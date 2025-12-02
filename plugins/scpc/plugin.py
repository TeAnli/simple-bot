from datetime import datetime

from ncatbot.core import GroupMessageEvent
from ncatbot.plugin_system import NcatBotPlugin, group_admin_filter, group_filter
from ncatbot.plugin_system import command_registry
from ncatbot.utils import get_log

from plugins.scpc.platforms.codeforces import CodeforcesPlatform
from plugins.scpc.platforms.luogu import LuoguPlatform
from plugins.scpc.platforms.nowcoder import NowcoderPlatform
from plugins.scpc.platforms.platform import Contest
from plugins.scpc.platforms.scpc import SCPCPlatform, render_scpc_user_info_image, render_scpc_week_rank_image, \
    generate_excel_contest_rank
from plugins.scpc.utils.text import format_contest_text, calculate_accept_ratio, format_timestamp
import random

LOG = get_log()


class SCPCPlugin(NcatBotPlugin):
    name = "SCPC"
    version = "0.0.3"
    author = "TeAnli"
    description = "专为西南科技大学 SCPC 团队 打造的 ncatbot 机器人插件"

    group_listeners = dict[str, bool]()
    cf_alerted_ids = set[int]()

    codeforces_platform = CodeforcesPlatform()
    scpc_platform = SCPCPlatform("player281", "123456")
    nowcoder_platform = NowcoderPlatform()
    luogu_platform = LuoguPlatform()

    # ----------------------------
    # region 插件生命周期方法
    # ----------------------------
    async def on_load(self):
        """
        注册比赛监听的定时任务 (每 30 分钟执行一次)
        """
        LOG.info("SCPC 插件启动中")


    def _format_single_contest(
        self,
        c: Contest,
        now_ts: int,
        include_id: bool,
        source_label: str | None = None,
        skip_verify_name: bool = False,
    ) -> tuple[int, str] | None:
        if skip_verify_name and ("验题" in c.name):
            return None
        timing = self.extract_contest_timing(c, now_ts)
        if not timing:
            return None
        state, remaining_label, remaining_secs, duration_secs, start_ts, sort_key = (
            timing
        )
        text = format_contest_text(
            name=c.name,
            contest_id=c.id,
            state=state,
            start_ts=start_ts,
            remaining_label=remaining_label,
            remaining_secs=remaining_secs,
            duration_secs=duration_secs,
            include_id=include_id,
            contest_url=c.url,
        )
        if source_label:
            text = f"{text}\n来源: {source_label}"
        return sort_key, text

    def _build_contest_texts(
        self,
        contests: list[Contest],
        include_id: bool,
        source: str | None = None,
        skip_verify_name: bool = False,
    ) -> list[tuple[int, str]]:
        now_ts = int(datetime.now().timestamp())
        source_map = {
            "cf": "Codeforces",
            "scpc": "SCPC",
            "nowcoder": "牛客",
            "luogu": "洛谷",
        }
        label = source_map.get(source, source) if source else None
        items: list[tuple[int, str]] = []
        for c in contests:
            formatted = self._format_single_contest(
                c, now_ts, include_id, label, skip_verify_name
            )
            if formatted:
                items.append(formatted)
        items.sort(key=lambda x: x[0])
        return items

    # ----------------------------
    # region 命令注册
    # ----------------------------
    @command_registry.command("来个男神", description="随机发送一张男神照片")
    @group_admin_filter
    @group_filter
    async def random_god_image(self, event: GroupMessageEvent):
        LOG.info(f"用户 {event.user_id} 请求随机图片")
        random_id = random.randint(1, 5)
        image_path = f"plugins/scpc/assets/image{random_id}.png"
        await self.api.send_group_image(event.group_id, image_path)

    @command_registry.command("添加比赛监听器", description="为当前群开启比赛监听任务")
    @group_admin_filter
    @group_filter
    async def add_contest_listener(self, event: GroupMessageEvent):
        LOG.info(f"用户 {event.user_id} 添加了比赛订阅 至 {event.group_id}")
        self.group_listeners[event.group_id] = True
        await self.api.send_group_text(event.group_id, "已为本群开启比赛监听任务")

    @command_registry.command("移除比赛监听器", description="为当前群关闭比赛监听任务")
    @group_admin_filter
    @group_filter
    async def remove_contest_listener(self, event: GroupMessageEvent):
        LOG.info(f"User {event} removed contest listener for contest")
        self.group_listeners[event.group_id] = False
        await self.api.send_group_text(event.group_id, "已为本群关闭比赛监听任务")

    @command_registry.command("scpc信息", description="查询scpc网站的个人信息")
    @group_filter
    async def get_user_info(self, event: GroupMessageEvent, username: str):
        data = await self.scpc_platform.get_user_info(username)
        if not data:
            LOG.warning(f"获取 SCPC 用户信息失败：{username}")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 用户信息, 请稍后重试"
            )
            return

        LOG.info(f"获取 SCPC 用户信息: {data}")
        total = int(getattr(data, "total", 0))
        solved_list = getattr(data, "solved_list", []) or []
        accept_ratio = "{:.2f}".format(
            calculate_accept_ratio(total, len(solved_list)) * 100
        )
        nickname = getattr(data, "nickname", username) or username
        signature = getattr(data, "signature", "") or ""
        avatar = getattr(data, "avatar", "") or ""
        image_path = await render_scpc_user_info_image(
            nickname=nickname,
            signature=signature,
            total=total,
            ac=len(solved_list),
            accept_ratio=accept_ratio,
            username=username,
            avatar=avatar,
        )
        if image_path:
            await self.api.send_group_image(event.group_id, image_path)
            return
        user_text = (
            f"SCPC 个人信息：\n"
            f"昵称: {nickname}\n"
            f"签名: {signature}\n"
            f"提交数: {total}\n"
            f"AC数: {len(solved_list)}\n"
            f"题目通过率: {accept_ratio}%"
        )
        await self.api.send_group_text(event.group_id, user_text)

    @command_registry.command("scpc排行", description="获取SCPC最近一周过题排行")
    @group_filter
    async def get_scpc_week_rank_command(self, event: GroupMessageEvent):
        records = await self.scpc_platform.get_week_rank()
        if records is None:
            LOG.warning("获取 SCPC 排行失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 排行信息, 请稍后重试"
            )
            return
        image_path = await render_scpc_week_rank_image(records)
        if image_path:
            await self.api.send_group_image(event.group_id, image_path)
            return
        lines = []
        for i, record in enumerate(records, start=1):
            lines.append(f"#{i} {record.username} | AC:{record.ac}")
        await self.api.send_group_text(event.group_id, "\n".join(lines))

    # @command_registry.command("cf积分", description="获取codeforces比赛信息")
    # @group_filter
    # async def get_codeforces_user_rating(self, event: GroupMessageEvent, username: str):
    #     ratings = get_codeforces_user_rating(username)
    #     if ratings is not None:
    #         LOG.info(f"获取 CF 用户积分记录：{len(ratings)} 条")
    #
    #         if not ratings:
    #             await self.api.send_group_text(
    #                 event.group_id, f"用户 {username} 没有比赛记录"
    #             )
    #             return
    #
    #         last_contest = ratings[-1]
    #         ratings_text = f"新积分: {last_contest.new_rating}\n"
    #
    #         await self.api.send_group_text(event.group_id, ratings_text.strip())
    #     else:
    #         LOG.warning("获取 CF 用户积分失败：请求异常或状态不正确")
    #         await self.api.send_group_text(
    #             event.group_id, "暂时无法获取 Codeforces 用户积分信息, 请稍后重试"
    #         )

    @command_registry.command("cf比赛", description="获取codeforces比赛信息")
    @group_filter
    async def get_codeforces_contests(self, event: GroupMessageEvent):
        contests = await self.codeforces_platform.get_contests()
        if contests is None:
            LOG.warning("获取 CF 比赛失败：请求异常或状态不正确")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 Codeforces 比赛信息, 请稍后重试"
            )
            return
        LOG.info(f"获取 CF 比赛列表：共 {len(contests)} 场")
        texts = self._build_contest_texts(contests, include_id=True, source="cf")
        if texts:
            await self.api.send_group_text(
                event.group_id, "\n\n".join([t for _, t in texts])
            )
        else:
            await self.api.send_group_text(
                event.group_id, "近期暂无即将开始或进行中的 Codeforces 比赛"
            )

    @command_registry.command("scpc近期比赛", description="获取近期SCPC比赛信息")
    @group_filter
    async def get_recent_scpc_contests(self, event: GroupMessageEvent):
        records = await self.scpc_platform.get_recent_contests()
        if records is None:
            LOG.warning("获取 SCPC 近期比赛失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 近期比赛信息, 请稍后重试"
            )
            return
        texts = self._build_contest_texts(records, include_id=False, source="scpc")
        if texts:
            await self.api.send_group_text(
                event.group_id, "\n\n".join([t for _, t in texts])
            )
        else:
            await self.api.send_group_text(
                event.group_id, "近期暂无即将开始或进行中的 SCPC 比赛"
            )

    @command_registry.command("牛客比赛", description="获取牛客近期比赛信息")
    @group_filter
    async def get_nowcoder_recent_contests_command(self, event: GroupMessageEvent):
        contests = await self.nowcoder_platform.get_contests()
        if not contests:
            await self.api.send_group_text(
                event.group_id, "暂时无法获取牛客近期比赛信息, 请稍后重试"
            )
            return
        texts = self._build_contest_texts(contests, include_id=True, source="nowcoder")
        await self.api.send_group_text(
            event.group_id, "\n\n".join([t for _, t in texts])
        )

    @command_registry.command("洛谷比赛", description="获取洛谷比赛信息")
    @group_filter
    async def get_luogu_contests(self, event: GroupMessageEvent):
        contests = await self.luogu_platform.get_contests()
        if contests is None:
            LOG.warning("获取 洛谷 比赛失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 洛谷 比赛信息, 请稍后重试"
            )
            return
        texts = self._build_contest_texts(contests, include_id=True, source="luogu")
        if texts:
            await self.api.send_group_text(
                event.group_id, "\n\n".join([t for _, t in texts])
            )
        else:
            await self.api.send_group_text(
                event.group_id, "近期暂无即将开始或进行中的 洛谷 比赛"
            )

    @command_registry.command("scpc近期更新题目", description="获取近期SCPC更新题目")
    @group_filter
    async def get_recent_scpc_updated_problems(self, event: GroupMessageEvent):
        items = await self.scpc_platform.get_recent_updated_problems()
        LOG.info(f"获取 SCPC 近期更新题目：{items} 条")
        if not items:
            LOG.warning("获取 SCPC 近期更新题目失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 近期更新题目, 请稍后重试"
            )
            return
        lines = []
        for p in items:
            time_str = (
                format_timestamp(p.gmt_modified)
                if isinstance(p.gmt_modified, int) and p.gmt_modified > 0
                else str(p.gmt_modified)
            )
            lines.append(
                f"题目: {p.title}\nID: {p.problem_id}\n更新时间: {time_str}\n地址: {p.url}"
            )
        await self.api.send_group_text(event.group_id, "\n".join(lines))

    @command_registry.command("scpc比赛排行", description="生成比赛的排行榜Excel表格")
    @group_filter
    async def get_scpc_contest_rank(self, event: GroupMessageEvent, contest_id: int):
        await self.scpc_platform.login()
        ranks = await self.scpc_platform.get_contest_rank(contest_id=contest_id)
        if not ranks:
            await self.api.send_group_text(
                event.group_id, "未获取到比赛排行或比赛ID无效"
            )
        else:
            excel_path = generate_excel_contest_rank(
                rank_users=ranks, contest_id=contest_id
            )
            try:
                await self.api.send_group_file(event.group_id, file=excel_path)
            except Exception as e:
                await self.api.send_group_text(event.group_id, f"发送文件失败: {e}")
            pass
