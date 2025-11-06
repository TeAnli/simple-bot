
from ncatbot.core import BotClient
from ncatbot.utils import get_log
bot = BotClient()
logger = get_log()

# ========== 启动 BotClient ==========
if __name__ == '__main__':
    logger.info('Starting bot...')
    bot.run()
    logger.info('Bot stopped.')