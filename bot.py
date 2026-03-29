import os
import sys
import logging
import asyncio
from io import BytesIO
import random

import requests
from telegram import Bot
from telegram.error import InvalidToken

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


headers = {"User-Agent": "chess-lord/1.0"}
CAT_SUBREDDITS = ["cats", "blackcats", "OneOrangeBraincell", "danglers", "Catswithjobs", "airplaneears", "IllegallySmolCats", "catsareliquid", "Blep"]

# Returns the top posts of a subreddit
# time_filter: hour, day, week, month, year, all
def get_top_posts(subreddit, limit=10, time_filter="day"):
    logger.info(f"Getting top posts from r/{subreddit}")

    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {
        "limit": limit,
        "t": time_filter
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        posts = data["data"]["children"]
        return posts

    except Exception as e:
        logger.error("Error getting top posts")
        return []



# Takes a reddit post's url and provides the attached image.
# returns None if no image is attached
def get_image_data(post):
    try:
        url = post["data"]["url"]
    except Exception:
        logger.error("Post does not contain url")
        return None

    logger.info(f"Retreiving image data from: {url}")

    try:
        if url.startswith("https://i.redd.it"):
            img = requests.get(url, headers=headers)

            logger.info("Returning image data from singular image")
            return img.content

        if post.get("is_gallery"):
            first = next(iter(post["media_metadata"].values()))
            img_url = first["s"]["u"].replace("&amp;", "&")
            img = requests.get(img_url, headers=headers)

            logger.info("Returning first image data from gallery")
            return img.content

        logger.warning(f"Bad post: {url}")
        return None
    except Exception as e:
        logger.error(e)
        logger.error(f"Could not retreive post: {url}")
        return None

async def send_picture(bot, image_data, chat_id):
    await bot.send_photo(
        chat_id=chat_id,
        photo=BytesIO(image_data),
    )
    logger.info("Sent picture.")

async def main_loop(bot, chat_id):
    while True:
        sleep_time = random.randint(16 * 3600, 24 * 3600)
        logger.info(f"Next picture will be sent in {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)

        top_posts = get_top_posts(random.choice(CAT_SUBREDDITS))
        if top_posts == []:
            logger.error("No top posts found. Skipping message.")
            continue

        sent_picture = False
        for post in top_posts:
            image_data = get_image_data(post)
            if image_data:
                await send_picture(bot, image_data, chat_id)
                sent_picture = True
                break

        if not sent_picture:
            logger.error("No image was sent")




async def main():
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    CHAT_ID = os.environ.get("CHAT_ID")

    if BOT_TOKEN is None:
        logger.critical("No BOT_TOKEN found in env. Exiting")
        sys.exit(1)

    if CHAT_ID is None:
        logger.critical("No CHAT_ID found in env. Exiting")
        sys.exit(1)

    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me() # Check token validity
        logger.info("Bot connected: @%s", me.username)
    except InvalidToken:
        logger.critical("Invalid Token. Exiting")
        sys.exit(1)

    await main_loop(bot, CHAT_ID)



if __name__ == "__main__":
    asyncio.run(main())
