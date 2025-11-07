from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.core.event import BaseMessageEvent
from ncatbot.utils import get_log

import random
_logger = get_log()

message_list = [
    "赞过了哦",
    "赞了赞了",
    "赞过了",
    "点赞成功",
    "已点赞",
]

class AutoLikePlugin(NcatBotPlugin):
    name = "AutoLikePlugin"
    version = "0.0.1"
    author = "TeAnli"
    description = "自动点赞插件, 支持命令点赞和定时点赞"

    @command_registry.command("点赞", description="对你的名片进行点赞")
    async def like_command(self, event: BaseMessageEvent):
        status = await self.api.get_status()
        _logger.info(f"User {event.user_id} requested like. Status: {status}")
        count = 0
        try:
            for _ in range(5):
                await self.api.send_like(event.user_id, times=10)
                count += 10
                _logger.info(f"Sent 10 likes in batch, total count: {count}")
        except Exception as e:
            _logger.warning(f"Like action encountered an error after {count} likes: {e}")

        await self.api.send_group_msg(event.group_id, [
            {
                "type": "text",
                "data": {
                    "text": f"{random.choice(message_list)}"
                }
            }
        ])
