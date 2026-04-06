import os
import sys
import logging
import asyncio
import random
from io import BytesIO
from dotenv import load_dotenv # https://pypi.org/project/python-dotenv/
from typing import Optional
from fake_useragent import UserAgent # https://pypi.org/project/fake-useragent/

import requests
from telegram import Bot
from telegram.error import InvalidToken


#!TODO: make full async
#!TODO: add more annotations

# local variables
CAT_SUBREDDITS = ["cats", "blackcats", "OneOrangeBraincell", "danglers", "Catswithjobs", "airplaneears", "IllegallySmolCats", "catsareliquid", "Blep"]
GET_REQUEST_ATTEMPLS = 5
MIN_WAIT_TIME = 10 # seconds
MAX_WAIT_TIME = 15 # seconds

# global variables
current_subreddit_index = 0
# removed user agent from headers to avoid bans
custom_headers = {}
user_agent_manager = UserAgent()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


# exceptions, will be in asnother file
class TokenNotFoundException(Exception):
    def __str__(): return "No BOT_TOKEN found in env."

class ChatIdNotFoundException(Exception):
    def __str__(): return "No CHAT_ID found in env."

class InvalidTokenException(Exception):
    def __str__(): return "Invalid token."
        

# Returns the next element of the CAT_SUBREDDITS array.
# Loops back if the end is reached
def next_subreddit():
    global current_subreddit_index

    subreddit = CAT_SUBREDDITS[current_subreddit_index]

    current_subreddit_index = (current_subreddit_index + 1) % len(CAT_SUBREDDITS)
    return subreddit


# Returns the top posts of a subreddit
# time_filter: hour, day, week, month, year, all
def get_top_posts(subreddit: str, limit: int=10, time_filter:str="day") -> Optional[dict]:
    logger.info(f"Getting top posts from r/{subreddit}")
    url = f"https://www.reddit.com/r/{subreddit}/top.json"

    try:
        response = requests.get(
            url, 
            headers={
                "User-Agent": user_agent_manager.random, # generate user agent for every request randomly
                **custom_headers # custom user headers
            }, 
            params={ # dont need another var for this
                "limit": limit,
                "t": time_filter
            }
        )
        response.raise_for_status()
        
        posts = response.json()["data"]["children"]
        return posts

    except Exception as e:
        # added some context
        logger.error(f"Error getting top posts from \n    url: {url}\n    Exception: {e}")
        # do not return None here, useless


# Takes a reddit post's url and provides the attached image.
def get_image_data(post) -> Optional[bytes]:
    # returns None if no image is attached
    
    try:
        url = post["data"]["url"]
    except Exception:
        logger.error("Post does not contain url")
        return None

    if not url.startswith("https://i.redd.it"):
        logger.warning(f"Post contains non-image data: {url}")
        return None

    try:
        img = requests.get(url, headers={
                "User-Agent": user_agent_manager.random, # generate user agent for every request randomly
                **custom_headers # custom user headers
            })
        logger.info(f"Retrieved image data from: {url}.")
        return img.content
    except Exception as e:
        # do not use another log message for the same action
        logger.error(f"Could not retreive post: {url}, exception: {e}")


def get_next_image_data(attempts=5):
    for i in range(1, attempts+1):
        subreddit = next_subreddit()
        top_posts = get_top_posts(subreddit)

        if not top_posts:
            logger.warning(f"No top posts found in r/{subreddit}. Trying next subreddit. (attempt {i})")
            continue

        logger.info(f"Found top posts in r/{subreddit}")

        for post in top_posts:
            image_data = get_image_data(post)
            if image_data:
                logger.info(f"Retrieved image data from r/{subreddit}")
                return image_data

        logger.warning(f"No image data found in any post from r/{subreddit}. (attempt {i})")


async def send_picture(bot, image_data, chat_id):
    await bot.send_photo(
        chat_id=chat_id,
        photo=BytesIO(image_data),
    )
    logger.info(f"Sent picture to {chat_id}.")


async def main_loop(bot, chat_id):
    while True:
        sleep_time = random.randint(MIN_WAIT_TIME, MAX_WAIT_TIME) # removed magic values
        logger.info(f"Next picture will be sent in {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)

        image_data = get_next_image_data() # attemps variable has not been used

        if not image_data:
            logger.error("Could not get an image to send. Skipping message")
            continue

        await send_picture(bot, image_data, chat_id)


async def main():
    # loading .env file, file must be in the same dir
    # Example:
    #    .
    #    ├── .env
    #    └── main.py

    load_dotenv()
    
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    CHAT_ID = os.environ.get("CHAT_ID")

    if BOT_TOKEN is None:
        # just raise custom exception
        raise TokenNotFoundException()

    if CHAT_ID is None:
        raise ChatIdNotFoundException()

    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me() # Check token validity
        logger.info("Bot connected: @%s", me.username)
    except InvalidToken:
        raise InvalidTokenException()

    await main_loop(bot, CHAT_ID)



if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
    except Exception as ex:
        # do not skip any of critical exceptions
        logger.critical(ex)
