from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Callable, Literal

from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.plugin_system import admin_filter
from ncatbot.core.event import BaseMessageEvent

from ncatbot.utils import get_log

import random
import os
import time
from . import api
from .utils import (
    calculate_accept_ratio,
    format_contest_text,
    parse_scpc_time,
    require_sender_admin,
    send_group_text,
    broadcast_text,
)

_logger = get_log()

# 过滤器装饰器已移至 utils.py

class SCPCPlugin(NcatBotPlugin):
    name = 'SCPC'
    version = '0.0.1'
    author = 'TeAnli'
    description = '专为西南科技大学 SCPC 竞赛平台 打造的 ncatbot 机器人插件'
    
    # 监听的群聊
    group_listeners = {}
    # 存储 CF 已提醒过的比赛ID（去重用）
    _cf_alerted_ids = set()
    # 插件加载函数
    async def on_load(self):
        _logger.info('SCPC Plugin loaded.')
        # 添加任务, 每隔30分钟检测一次
        try:
            self.add_scheduled_task(
                self._listen_task,
                "cf_contest_watch",
                "30m",
            )
            _logger.info('Scheduled hourly CF contest watcher.')
        except Exception as e:
            _logger.warning(f'Failed to add scheduled task: {e}')

    # 判断启用监听且有群组, 并且群组是否开启了监听任务
    def _judge(self) -> bool:
        return any(self.group_listeners.values())
    
    # 特定小时数内 获取一次 CF 比赛 信息并提醒
    async def _listen_task(self):
        _logger.info('SCPC Plugin listen task running.')
        if not self._judge():
            _logger.info('Contest listener disabled or no groups, skipping.')
            return
        # 检查 CF 比赛并在距离开始 1 小时内提醒
        await self._check_cf_contests_and_notify(threshold_hours=2)
        
    # 发送消息相关工具函数已提取至 utils.py

    # HTTP 获取逻辑已下沉到 api.py

    # 统一群发文本：只向开启监听的群发送
    # 广播文本工具函数已提取至 utils.py

    # 提取 CF 比赛时间信息：状态、剩余时间标签与秒数、时长、开始时间
    def _extract_cf_timing(self, contest: dict):
        """根据 Codeforces 比赛对象计算展示所需的时间信息。
        返回 (state, remaining_label, remaining_secs, duration_secs, start_ts)
        - 结束比赛返回 None
        """
        rel = int(contest.get('relativeTimeSeconds', 0))
        duration = int(contest.get('durationSeconds', 0))
        start_ts = int(contest.get('startTimeSeconds', 0))
        if rel < 0:
            return '即将开始', '据开始还剩', abs(rel), duration, start_ts
        if 0 <= rel < duration:
            return '进行中', '距离结束', max(duration - rel, 0), duration, start_ts
        return None

    # 提取 SCPC 比赛时间信息：状态、剩余时间标签与秒数、时长、开始时间、排序键
    def _extract_scpc_timing(self, record: dict, now_ts: int):
        """根据 SCPC 比赛记录计算展示所需的时间信息。
        返回 (state, remaining_label, remaining_secs, duration_secs, start_ts, sort_key)
        - 结束比赛返回 None
        """
        name = record.get('title') or record.get('contestName') or '未命名比赛'
        start_ts = parse_scpc_time(record.get('startTime'))
        end_ts = parse_scpc_time(record.get('endTime'))
        duration = int(record.get('duration') or (max(end_ts - start_ts, 0) if start_ts and end_ts else 0))

        if start_ts and now_ts < start_ts:
            state = '即将开始'
            remaining_label = '据开始还剩'
            remaining_secs = start_ts - now_ts
            sort_key = remaining_secs
        elif start_ts and end_ts and start_ts <= now_ts < end_ts:
            state = '进行中'
            remaining_label = '距离结束'
            remaining_secs = max(end_ts - now_ts, 0)
            sort_key = remaining_secs
        else:
            return None

        return name, state, remaining_label, remaining_secs, duration, start_ts, sort_key
    # 检测 codeforces 比赛 threshold_hours 用于 接收小时数
    async def _check_cf_contests_and_notify(self, threshold_hours: int = 2):
        contests = api.get_codeforces_contests()
        if not contests:
            _logger.warning('Failed to fetch Codeforces contests: no data or bad status')
            return
        threshold_seconds = int(threshold_hours * 3600)
        upcoming_texts = []

        for contest in contests:
            cid = contest.get('id')
            timing = self._extract_cf_timing(contest)
            # 仅提醒即将开始且在阈值内的比赛
            if timing:
                state, remaining_label, remaining_secs, duration, start_ts = timing
                if state == '即将开始' and remaining_secs <= threshold_seconds:
                    # 去重：避免重复提醒
                    if cid in self._cf_alerted_ids:
                        continue
                    self._cf_alerted_ids.add(cid)

                    text = format_contest_text(
                        name=contest.get('name'),
                        contest_id=cid,
                        state=state,
                        start_ts=start_ts,
                        remaining_label=remaining_label,
                        remaining_secs=remaining_secs,
                        duration_secs=duration,
                    )
                    upcoming_texts.append((remaining_secs, text))

        # 最近开始的排前
        upcoming_texts.sort(key=lambda x: x[0])
        if not upcoming_texts:
            _logger.info('No CF contests starting within threshold; no notifications sent.')
            return

        merged = "\n\n".join([t for _, t in upcoming_texts])
        # 统一群发
        await broadcast_text(self.api, self.group_listeners, merged)

    @command_registry.command('来个男神', description='随机发送一张男神照片')
    @require_sender_admin()
    async def random_god_image(self, event: BaseMessageEvent):
        _logger.info(f'User {event.user_id} requested a random male god image.')
        random_id = random.randint(1, 5)
        await self.api.send_group_image(event.group_id, f'plugins/scpc/assets/image{random_id}.png')
    @command_registry.command('scpc信息', description='查询scpc网站的个人信息')
    async def get_user_info(self, event: BaseMessageEvent, username: str):
        # 使用 api.py 封装的获取函数
        data = api.get_scpc_user_info(username)
        if not data:
            _logger.warning(f'Failed to fetch SCPC user info for {username}')
            await self._send_text(event.group_id, "暂时无法获取 SCPC 用户信息, 请稍后重试")
            return

        _logger.info(f'Fetching SCPC user info: {data}')
        total = int(data.get('total', 0))
        solved_list = data.get('solvedList') or []
        accept_ratio = "{:.2f}".format(calculate_accept_ratio(total, len(solved_list)) * 100)
        nickname = data.get('nickname') or username
        signature = data.get('signature') or ''

        # 统一文本输出
        user_text = (
            f"SCPC 个人信息：\n"
            f"昵称: {nickname}\n"
            f"签名: {signature}\n"
            f"提交数: {total}\n"
            f"AC数: {len(solved_list)}\n"
            f"题目通过率: {accept_ratio}%"
        )
        await send_group_text(self.api, event.group_id, user_text)
    @command_registry.command('添加比赛监听器', description='为当前群开启比赛监听任务')
    @require_sender_admin()
    async def add_contest_listener(self, event: BaseMessageEvent):
        _logger.info(f'User {event} added contest listener for contest')
        self.group_listeners[event.group_id] = True
        await send_group_text(self.api, event.group_id, "已为本群开启比赛监听任务（每小时检查一次）。")
    @command_registry.command('移除比赛监听器', description='为当前群关闭比赛监听任务')
    @require_sender_admin()
    async def remove_contest_listener(self, event: BaseMessageEvent):
        _logger.info(f'User {event} removed contest listener for contest')
        self.group_listeners[event.group_id] = False
        await send_group_text(self.api, event.group_id, "已为本群关闭比赛监听任务。")

    async def _get_codeforces_contests(self, group_id: int):
        contests = api.get_codeforces_contests()
        if contests is not None:
            _logger.info(f'Fetching Codeforces contests: received {len(contests)} contests')

            # 收集即将开始与进行中的比赛
            collected = []  # (time_remaining_seconds, formatted_text)
            for contest in contests:
                timing = self._extract_cf_timing(contest)
                if not timing:
                    continue
                state, remaining_label, time_remaining, duration, start_ts = timing

                text = format_contest_text(
                    name=contest['name'],
                    contest_id=contest['id'],
                    state=state,
                    start_ts=start_ts,
                    remaining_label=remaining_label,
                    remaining_secs=int(time_remaining),
                    duration_secs=int(duration),
                )
                collected.append((time_remaining, text))

            # 按剩余时间升序排序，最近的比赛排在最前
            collected.sort(key=lambda x: x[0])
            texts = [t for _, t in collected]

            if texts:
                await send_group_text(self.api, group_id, "\n\n".join(texts))
            else:
                await send_group_text(self.api, group_id, "近期暂无即将开始或进行中的 Codeforces 比赛")
        else:
            _logger.warning('Failed to fetch Codeforces contests: request failed or bad status')
            await send_group_text(self.api, group_id, "暂时无法获取 Codeforces 比赛信息, 请稍后重试")

    @command_registry.command("scpc比赛", description="获取SCPC比赛信息")
    async def get_scpc_contests(self, event: BaseMessageEvent):
        """从 SCPC 平台获取比赛列表，展示即将开始与进行中的比赛。"""
        records = api.get_scpc_contests()
        if records is None:
            _logger.warning('Fetch SCPC contests failed: no data')
            await send_group_text(self.api, event.group_id, "暂时无法获取 SCPC 比赛信息, 请稍后重试")
            return
        collected = []  # (sort_key, text)
        now_ts = int(datetime.now().timestamp())
        for record in records:
            timing = self._extract_scpc_timing(record, now_ts)
            if not timing:
                continue
            name, state, remaining_label, remaining_secs, duration, start_ts, sort_key = timing

            text = format_contest_text(
                name=name,
                contest_id=None,
                state=state,
                start_ts=start_ts,
                remaining_label=remaining_label,
                remaining_secs=remaining_secs,
                duration_secs=duration,
                include_id=False,
            )
            collected.append((sort_key, text))

        collected.sort(key=lambda x: x[0])
        texts = [t for _, t in collected]
        if texts:
            await send_group_text(self.api, event.group_id, "\n\n".join(texts))
        else:
            await send_group_text(self.api, event.group_id, "近期暂无即将开始或进行中的 SCPC 比赛")
    
    @command_registry.command("cf积分", description='获取codeforces比赛信息')
    async def get_codeforces_user_rating(self, event: BaseMessageEvent, username: str):
        ratings = api.get_codeforces_user_rating(username)
        if ratings is not None:
            _logger.info(f'Fetching Codeforces user rating: {len(ratings)} records')

            if not ratings:
                await send_group_text(self.api, event.group_id, f"用户 {username} 没有比赛记录。")
                return
                
            last_contest = ratings[-1]
            ratings_text = (
                f"新积分: {last_contest['newRating']}\n"
            )

            await send_group_text(self.api, event.group_id, ratings_text.strip())
        else:
            _logger.warning('Failed to fetch Codeforces user rating: request failed or bad status')
            await send_group_text(self.api, event.group_id, "暂时无法获取 Codeforces 用户积分信息, 请稍后重试")

    @command_registry.command("cf比赛", description='获取codeforces比赛信息')
    async def get_codeforces_contests(self, event: BaseMessageEvent):
        await self._get_codeforces_contests(event.group_id)

    @command_registry.command("scpc榜单图", description="截图 SCPC 过题榜单并发送图片内容")
    async def screenshot_scpc_rank(self, event: BaseMessageEvent):
        # 目录准备
        out_dir = os.path.join('plugins', 'scpc', 'cache')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"scpc_rank_{int(time.time())}.png")

        # 延迟导入，避免未安装时影响其他命令
        try:
            from playwright.async_api import async_playwright
        except Exception as e:
            _logger.warning(f"Playwright not available: {e}")
            await send_group_text(self.api, event.group_id, "Playwright 未安装或浏览器未就绪，请先安装依赖并执行 'playwright install'。")
            return

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    device_scale_factor=2,
                )
                page = await context.new_page()

                await page.goto("http://scpc.fun/home", wait_until='networkidle')
                # 优先搜索精确选择器（同时匹配属性与类）
                precise_selector = 'div.el-card.ac-rank-card.is-always-shadow.card-top[data-v-5bb0f4c1]'
                simple_selector = 'div[data-v-5bb0f4c1]'

                locator = None
                used_selector = None
                try:
                    await page.wait_for_selector(precise_selector, state='visible', timeout=8000)
                    locator = page.locator(precise_selector)
                    used_selector = precise_selector
                except Exception:
                    # 回退到更宽松的选择器
                    await page.wait_for_selector(simple_selector, state='visible', timeout=8000)
                    # 选择第一个匹配，避免页面中存在多个相同 data-v 的区块
                    locator = page.locator(simple_selector).first
                    used_selector = simple_selector

                # 确保元素在视区内
                await locator.scroll_into_view_if_needed()

                # 强制触发图片懒加载并等待所有图片加载完成
                try:
                    await page.evaluate(
                        """
                        (sel) => {
                            const el = document.querySelector(sel);
                            if (!el) return;
                            const imgs = el.querySelectorAll('img');
                            imgs.forEach(img => {
                                try {
                                    // 移除懒加载属性并改为 eager
                                    img.removeAttribute('loading');
                                    img.loading = 'eager';
                                    // 常见懒加载属性迁移到 src
                                    const candidates = ['data-src','data-original','data-lazy-src','data-url'];
                                    for (const key of candidates) {
                                        const val = img.getAttribute(key);
                                        if (val && (!img.src || img.src === '')) { img.src = val; break; }
                                    }
                                } catch {}
                            });
                        }
                        """,
                        used_selector
                    )

                    await page.wait_for_function(
                        """
                        (sel) => {
                            const el = document.querySelector(sel);
                            if (!el) return false;
                            const imgs = el.querySelectorAll('img');
                            for (const img of imgs) {
                                if (!img.complete || img.naturalWidth === 0) return false;
                            }
                            return true;
                        }
                        """,
                        used_selector,
                        timeout=20000
                    )
                except:
                    await page.wait_for_timeout(800)
                
                # 截图该区块
                await locator.screenshot(path=out_path)

                await browser.close()

            await self.api.send_group_image(event.group_id, out_path)
        except Exception as e:
            _logger.warning(f"Screenshot failed: {e}")
            await send_group_text(self.api, event.group_id, f"无法截图该页面的榜单区块, 请联系管理人员维护")

