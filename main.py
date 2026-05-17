import os
import sys
import logging
import asyncio
from telegram.ext import Application, CommandHandler
from telegram.error import InvalidToken
from dotenv import load_dotenv
from tasks import send_cats
from tasks import send_leetcode

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("mainlogger")


async def main():
    load_dotenv()
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    CHAT_ID = os.environ.get("CHAT_ID")

    if BOT_TOKEN is None:
        logger.critical("No BOT_TOKEN found in env. Exiting")
        sys.exit(1)

    if CHAT_ID is None:
        logger.critical("No CHAT_ID found in env. Exiting")
        sys.exit(1)

    try:
        app = Application.builder().token(BOT_TOKEN).build()
        bot = app.bot

        me = await bot.get_me() # Check token validity
        logger.info("Bot connected: @%s", me.username)
    except InvalidToken:
        logger.critical("Invalid Token. Exiting")
        sys.exit(1)

    app.add_handler(CommandHandler("pingme", send_leetcode.pingme))
    app.add_handler(CommandHandler("dontpingme", send_leetcode.dontpingme))

    async with app:
        await app.start()
        await app.updater.start_polling()

        await asyncio.gather(
            send_cats.main_loop(bot, CHAT_ID),
            send_leetcode.main_loop(bot, CHAT_ID) 
        )



if __name__ == "__main__":
    asyncio.run(main())
