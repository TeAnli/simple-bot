
from ncatbot.core import BotClient
from ncatbot.core.event import GroupMessageEvent
from ncatbot.utils import get_log
bot = BotClient()
logger = get_log()

about_infomation = """✨ 关于"安心Bot" ✨
👤 作者: 不知名人士
🔖 版本: 0.1.0
⚙️ 目前基于轻量的 ncatbot QQ 机器人框架开发(后续版本将转向 nonebot2)
🖼️ 暂未支持图片数据展示（后续版本会添加）
🚫 请勿利用 "安心Bot" 刷屏，发表违规言论
🤖 本程序不支持 AI 问答，也不会添加，为了防止重要消息被刷"""

menu_infomation = """💖 安心Bot 菜单 💖
📖 使用说明:
ℹ️ 关于安心 - 展示关于安心Bot界面
🧩 命令:
/来个男神 - 随机发送一张男神帅照 (仅群聊管理员)

/cf比赛 - 获取 Codeforces 比赛信息
/cf积分 <用户名> - 获取指定用户的rating

/添加比赛监听器 - 添加定时任务, 在比赛开始前自动发送即将开始的比赛信息 (仅群聊管理员)
/移除比赛监听器 - 移除定时任务 (仅群聊管理员)

/scpc信息 <用户名> - 获取指定用户名 SCPC 网站信息
/scpc榜单图 - 获取scpc一周内过题数前十名榜单"""


def is_at_me(event: GroupMessageEvent) -> bool:
    """检测是否有人 @ 机器人自身。"""
    try:
        # 遍历结构化消息片段，查找 at 段
        for seg in getattr(event, "message", []):
            d = seg.to_dict() if hasattr(seg, "to_dict") else seg
            if isinstance(d, dict) and d.get("type") == "at":
                qq = d.get("data", {}).get("qq")
                if qq and str(qq) == str(event.self_id):
                    return True
    except Exception:
        pass
    # 兼容原始文本中包含 CQ 码的情况
    raw = getattr(event, "raw_message", "") or ""
    if f"[CQ:at,qq={event.self_id}]" in raw:
        return True
    return False


async def respond_to_at(event: GroupMessageEvent) -> None:
    """根据 @ 的内容，发送 /菜单 或 /关于 已定义文本。"""
    raw = (getattr(event, "raw_message", "") or "").strip()
    # 优先匹配带斜杠的标准命令，其次是中文关键词
    if "/菜单" in raw or "菜单" in raw:
        await bot.api.post_group_msg(event.group_id, text=menu_infomation)
        return
    if "/关于" in raw or "关于" in raw:
        await bot.api.post_group_msg(event.group_id, text=about_infomation)
        return


@bot.on_group_message()
async def on_group_message(event: GroupMessageEvent):
    # 检测被 @ 时，根据内容回复菜单或关于
    if is_at_me(event):
        await respond_to_at(event)


if __name__ == '__main__':
    logger.info('Starting bot...')
    bot.run()
    logger.info('Bot stopped.')