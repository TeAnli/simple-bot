from dataclasses import dataclass
from datetime import datetime

from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.core.event import BaseMessageEvent

from ncatbot.utils import get_log

import random
import requests
import os
import time
from . import api
from .utils import *

_logger = get_log()


class SCPCPlugin(NcatBotPlugin):
    name = 'SCPC'
    version = '0.0.1'
    author = 'TeAnli'
    description = '专为西南科技大学 SCPC 竞赛平台 打造的 ncatbot 机器人插件'
    
    group_listeners = {}
    _codeforces_alerted_ids = set()
    # 评判函数：启用监听且有群组, 并且群组是否开启了监听任务
    def _judge(self) -> bool:
        return any(self.group_listeners.values())
    # 定时任务：特定小时数内 获取一次 CF 比赛 信息并提醒
    async def _listen_task(self):
        _logger.info('SCPC Plugin listen task running.')
        if not self._judge():
            _logger.info('Contest listener disabled or no groups; skipping.')
            return
        # 检查 CF 比赛并在距离开始 2 小时内提醒
        await self._check_cf_contests_and_notify(threshold_hours=2)
            
    async def _send(self, group_id, messages):
        try:
            await self.api.send_group_msg(group_id, messages)
        except Exception as e:
            _logger.warning(f'Send group message failed: {e}')

    async def _send_text(self, group_id, text: str):
        await self._send(group_id, [build_text_msg(text)])
        
    # 插件加载函数
    async def on_load(self):
        _logger.info('SCPC Plugin loaded.')
        try:
            self.add_scheduled_task(
                self._listen_task,
                "cf_contest_watch",
                "10s",
            )
            _logger.info('Scheduled hourly CF contest watcher.')
        except Exception as e:
            _logger.warning(f'Failed to add scheduled task: {e}')


    async def _check_cf_contests_and_notify(self, threshold_hours: int = 2):
        contests_url = api.codeforces_contests_url()
        try:
            response = requests.get(contests_url, headers=api.headers, timeout=10)
        except Exception as e:
            _logger.warning(f'Failed to fetch Codeforces contests: {e}')
            return

        if response.status_code != 200:
            _logger.warning(f'Bad status fetching Codeforces contests: {response.status_code} {response.text}')
            return

        body = response.json()
        if body.get('status') != 'OK':
            _logger.warning(f'Codeforces API not OK: {body}')
            return

        data = body.get('result', [])
        threshold_seconds = int(threshold_hours * 3600)
        upcoming_texts = []

        for contest in data:
            rel = int(contest.get('relativeTimeSeconds', 0))
            duration = int(contest.get('durationSeconds', 0))
            cid = contest.get('id')

            # 未来比赛 rel < 0
            if rel < 0:
                time_to_start = abs(rel)
                if time_to_start <= threshold_seconds:
                    # 去重：避免重复提醒
                    if cid in self._codeforces_alerted_ids:
                        continue
                    self._codeforces_alerted_ids.add(cid)

                    text = format_contest_text(
                        name=contest.get('name'),
                        contest_id=cid,
                        state='即将开始',
                        start_ts=int(contest.get('startTimeSeconds', 0)),
                        remaining_label='据开始还剩',
                        remaining_secs=time_to_start,
                        duration_secs=duration,
                    )
                    upcoming_texts.append((time_to_start, text))

        # 最近开始的排前
        upcoming_texts.sort(key=lambda x: x[0])
        if not upcoming_texts:
            _logger.info('No CF contests starting within threshold; no notifications sent.')
            return

        merged = "\n\n".join([t for _, t in upcoming_texts])
        # 发送到所有监听的群
        for gid, enabled in self.group_listeners.items():
            if enabled:
                await self._send_text(gid, merged)

    @command_registry.command('来个男神', description='随机发送一张男神照片')
    async def random_god_image(self, event: BaseMessageEvent):
        _logger.info(f'User {event.user_id} requested a random male god image.')
        random_id = random.randint(1, 5)
        await self.api.send_group_image(event.group_id, f'plugins/scpc/assets/image{random_id}.png')

    @command_registry.command('scpc信息', description='查询scpc网站的个人信息')
    async def get_user_info(self, event: BaseMessageEvent, username: str):
        user_info_url = api.user_info_url(username)
        response = requests.get(user_info_url, headers=api.headers)
        data = response.json()['data']
        _logger.info(f'Fetching SCPC user info: {data}')
        accept_ratio = "{:.2f}".format(calculate_accept_ratio(data['total'], len(data['solvedList'])) * 100)
        user_text = (
            f"SCPC 个人信息：\n"
            f"昵称: {data['nickname']}\n"
            f"签名: {data['signature']}\n"
            f"提交数: {data['total']}\n"
            f"AC数: {len(data['solvedList'])}\n"
            f"题目通过率: {accept_ratio}%"
        )
        await self._send_text(event.group_id, user_text)
    
    @command_registry.command('添加比赛监听器', description='为当前群开启比赛监听任务')
    async def add_contest_listener(self, event: BaseMessageEvent):
        _logger.info(f'User {event} added contest listener for contest')
        self.group_listeners[event.group_id] = True
        await self._send_text(event.group_id, "已为本群开启比赛监听任务（每小时检查一次）。")

    @command_registry.command('移除比赛监听器', description='为当前群关闭比赛监听任务')
    async def remove_contest_listener(self, event: BaseMessageEvent):
        _logger.info(f'User {event} removed contest listener for contest')
        self.group_listeners[event.group_id] = False
        await self._send_text(event.group_id, "已为本群关闭比赛监听任务。")

    async def _get_codeforces_contests(self, group_id: int):
        contests_url = api.codeforces_contests_url()
        response = requests.get(contests_url, headers=api.headers)
        if response.status_code == 200 and response.json()['status'] == 'OK':
            data = response.json()['result']
            _logger.info(f'Fetching Codeforces contests: {response.json()}')

            # 收集即将开始与进行中的比赛
            collected = []  # (time_remaining_seconds, formatted_text)
            for contest in data:
                rel = contest.get('relativeTimeSeconds', 0)
                duration = contest.get('durationSeconds', 0)

                if rel < 0:
                    state = '即将开始'
                    time_remaining = abs(rel)
                    remaining_label = '据开始还剩'
                elif 0 <= rel < duration:
                    state = '进行中'
                    time_remaining = max(duration - rel, 0)
                    remaining_label = '距离结束'
                else:
                    # 已结束的比赛不展示
                    continue

                text = format_contest_text(
                    name=contest['name'],
                    contest_id=contest['id'],
                    state=state,
                    start_ts=int(contest['startTimeSeconds']),
                    remaining_label=remaining_label,
                    remaining_secs=int(time_remaining),
                    duration_secs=int(duration),
                )
                collected.append((time_remaining, text))

            # 按剩余时间升序排序，最近的比赛排在最前
            collected.sort(key=lambda x: x[0])
            texts = [t for _, t in collected]

            if texts:
                await self._send_text(group_id, "\n\n".join(texts))
            else:
                await self._send_text(group_id, "近期暂无即将开始或进行中的 Codeforces 比赛")
        else:
            _logger.warning(f'Failed to fetch Codeforces contests: {response.text}')
            await self._send_text(group_id, "暂时无法获取 Codeforces 比赛信息, 请稍后重试")

    @command_registry.command("scpc比赛", description="获取SCPC比赛信息")
    async def get_scpc_contests(self, event: BaseMessageEvent):
        """从 SCPC 平台获取比赛列表，展示即将开始与进行中的比赛。"""
        contests_url = api.scpc_contests_url()
        try:
            response = requests.get(contests_url, headers=api.headers, timeout=10)
        except Exception as e:
            _logger.warning(f'Fetch SCPC contests failed: {e}')
            await self._send_text(event.group_id, "暂时无法获取 SCPC 比赛信息, 请稍后重试")
            return

        if response.status_code != 200:
            _logger.warning(f'SCPC contests bad status: {response.status_code} {response.text}')
            await self._send_text(event.group_id, "暂时无法获取 SCPC 比赛信息, 请稍后重试")
            return

        # 兼容多种返回结构：data.records 或 records
        body = {}
        try:
            body = response.json()
        except Exception:
            pass
        records = (
            body.get('data', {}).get('records')
            or body.get('records')
            or []
        )

        from .utils import parse_scpc_time

        collected = []  # (sort_key, text)
        now_ts = int(datetime.now().timestamp())
        for record in records:
            # 字段兼容：title/contestName，duration 秒，startTime/endTime 支持 ISO 或秒
            name = record.get('title') or record.get('contestName') or '未命名比赛'
            start_ts = parse_scpc_time(record.get('startTime'))
            end_ts = parse_scpc_time(record.get('endTime'))
            duration = int(record.get('duration') or max(end_ts - start_ts, 0))

            # 计算状态与剩余时间
            if start_ts and now_ts < start_ts:
                state = '即将开始'
                remaining_label = '据开始还剩'
                time_remaining = start_ts - now_ts
                sort_key = time_remaining
            elif start_ts and end_ts and start_ts <= now_ts < end_ts:
                state = '进行中'
                remaining_label = '距离结束'
                time_remaining = max(end_ts - now_ts, 0)
                sort_key = time_remaining
            else:
                # 已结束的比赛暂不展示
                continue

            text = format_contest_text(
                name=name,
                contest_id=None,
                state=state,
                start_ts=start_ts,
                remaining_label=remaining_label,
                remaining_secs=time_remaining,
                duration_secs=duration,
                include_id=False,
            )
            collected.append((sort_key, text))

        collected.sort(key=lambda x: x[0])
        texts = [t for _, t in collected]
        if texts:
            await self._send_text(event.group_id, "\n\n".join(texts))
        else:
            await self._send_text(event.group_id, "近期暂无即将开始或进行中的 SCPC 比赛")

    @command_registry.command("cf积分", description='获取codeforces比赛信息')
    async def get_codeforces_user_rating(self, event: BaseMessageEvent, username: str):
        user_rating_url = api.codeforces_user_rating_url(username)
        response = requests.get(user_rating_url, headers=api.headers)
        if response.status_code == 200 and response.json()['status'] == 'OK':
            data = response.json()['result']
            _logger.info(f'Fetching Codeforces user rating: {data}')

            if not data:
                await self._send_text(event.group_id, f"用户 {username} 没有比赛记录。")
                return
                
            last_contest = data[-1]
            ratings_text = (
                f"新积分: {last_contest['newRating']}\n"
            )

            await self._send_text(event.group_id, ratings_text.strip())
        else:
            _logger.warning(f'Failed to fetch Codeforces user rating: {response.text}')
            await self._send_text(event.group_id, "暂时无法获取 Codeforces 用户积分信息, 请稍后重试")

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
            await self._send_text(event.group_id, "Playwright 未安装或浏览器未就绪，请先安装依赖并执行 'playwright install'。")
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
            await self._send_text(event.group_id, f"无法截图该页面的榜单区块, 请联系管理人员维护")


