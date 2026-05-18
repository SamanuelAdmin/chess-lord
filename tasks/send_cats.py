import logging
import random
import asyncio
import requests
import json_utils
from io import BytesIO

logger = logging.getLogger("mainlogger")

headers = {"User-Agent": "chess-lord/1.0"}

json_filename = "cats.json"
CAT_SUBREDDITS = ["cats", "blackcats", "OneOrangeBraincell", "danglers", "Catswithjobs", "airplaneears", "IllegallySmolCats", "catsareliquid", "Blep"]
MIN_WAIT_TIME = 5 # hours
MAX_WAIT_TIME = 8 # hours

def load_state() -> dict:
    state = json_utils.load_json(json_filename)
    if not state:
        state = {
            "last_index" : 0,
        }
    json_utils.save_json(json_filename, state)
    return state

# Returns the next element of the CAT_SUBREDDITS array.
# Loops back if the end is reached
def next_subreddit():
    state = load_state()
    current_subreddit_index = state["last_index"]
    subreddit = CAT_SUBREDDITS[current_subreddit_index]

    current_subreddit_index = (current_subreddit_index + 1) % len(CAT_SUBREDDITS)
    state["last_index"] = current_subreddit_index
    json_utils.save_json(json_filename, state)
    return subreddit


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
        return None

# Takes a reddit post's url and provides the attached image.
# returns None if no image is attached
def get_image_data(post):
    try:
        url = post["data"]["url"]
    except Exception:
        logger.error("Post does not contain url")
        return None

    logger.info(f"Retreiving image data from: {url}")

    if not url.startswith("https://i.redd.it"):
        logger.warning(f"Post contains non-image data: {url}")
        return None

    try:
        img = requests.get(url, headers=headers)

        logger.info("Retrieved image data.")
        return img.content

    except Exception as e:
        logger.error(e)
        logger.error(f"Could not retreive post: {url}")
        return None


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

    return None


async def send_picture(bot, image_data, chat_id):
    await bot.send_photo(
        chat_id=chat_id,
        photo=BytesIO(image_data),
    )
    logger.info("Sent picture.")

async def main_loop(bot, chat_id):
    logger.info(__name__ + " loaded")
    while True:
        sleep_time = random.randint(MIN_WAIT_TIME * 3600, MAX_WAIT_TIME * 3600)
        logger.info(f"Next picture will be sent in {sleep_time} seconds.")
        await asyncio.sleep(sleep_time)

        image_data = get_next_image_data()

        if not image_data:
            logger.error("Could not get an image to send. Skipping message")
            continue

        await send_picture(bot, image_data, chat_id)


