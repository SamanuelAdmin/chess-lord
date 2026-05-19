import logging
import random
import asyncio
import json_utils
import csv
from datetime import datetime, date, time, timedelta
from telegram import LinkPreviewOptions
from telegram import ReactionTypeEmoji

logger = logging.getLogger("mainlogger")

DAILY_PROBLEM_TIME = time(6, 30) # 6:30

json_filename = "leetcode.json"
leetcode_dataset_filename = "leetcode_easier.csv"

LEETCODE_FIELDS = []
LEETCODE_ROWS = []
LEN_LEETCODE_ROWS = 0

def load_state() -> dict:
    state = json_utils.load_json(json_filename)
    if not state:
        state = {
            "day" : 0,
            "ping_users" : [],
            "completed_problems" : []
        }
    json_utils.save_json(json_filename, state)
    return state


def load_csv():
    global LEETCODE_FIELDS, LEETCODE_ROWS, LEN_LEETCODE_ROWS
    with open(leetcode_dataset_filename, 'r') as csvfile:
        csvreader = csv.reader(csvfile)

        LEETCODE_FIELDS = next(csvreader)
        for row in csvreader:
            LEETCODE_ROWS.append(row)

    LEN_LEETCODE_ROWS = len(LEETCODE_ROWS)

def get_sleep_time():
    now = datetime.now()
    target = datetime.combine(date.today(), DAILY_PROBLEM_TIME)

    if target <= now:
        target += timedelta(days=1)

    return (target - now).total_seconds()

def construct_message(day_number, problem_name, url, difficulty, ping_users=[]) -> str:
    msg = "‼️ЗАДАЧА ДНЯ " + str(day_number) + "‼️\n"
    msg += problem_name + "\n"
    msg += "Сложность: "
    if difficulty == 'Easy':
        msg += "🟢"
    elif difficulty == 'Medium':
        msg += "🟡🟡"
    elif difficulty == 'Hard':
        msg += "🔴🔴🔴"
    else:
        logger.error(f"Unknown difficulty: {difficulty}")
        msg += "???"
    msg += "\n" + url
    if ping_users == []:
        return msg
    
    msg += "\n"
    msg += ", ".join(ping_users)

    return msg

# Picks a random int from 0 to n-1, avoiding the array 'excluding'
# O(n)
def pick_random_excluding(n: int, exclude: list[int]) -> int:
    exclude_set = set(exclude)
    choices = [i for i in range(n) if i not in exclude_set]
    if not choices:
        raise ValueError("No valid numbers available after exclusions")
    return random.choice(choices)


def get_next_message():
    state = load_state()

    if len(state["completed_problems"]) >= LEN_LEETCODE_ROWS:
        state["completed_problems"] = []

    line_number = pick_random_excluding(LEN_LEETCODE_ROWS, state["completed_problems"])
    state["day"] += 1
    state["completed_problems"].append(line_number)
    json_utils.save_json(json_filename, state)
    next_line = LEETCODE_ROWS[line_number]
    
    # ID,Title,Difficulty,Link,Topics,Acceptance Rate (%),Premium Only,Category,Likes,Dislikes,Example Test Cases,Similar Questions
    return construct_message(state["day"], next_line[1], next_line[3], next_line[2], state["ping_users"])
    

async def pingme(update, context):
    if update.effective_user.username is None:
        await update.message.set_reaction(ReactionTypeEmoji("👎"))
        return

    state = load_state()
    username = "@" + update.effective_user.username   
    if not username in state["ping_users"]:
        state["ping_users"].append(username)

    json_utils.save_json(json_filename, state)
    await update.message.set_reaction(ReactionTypeEmoji("❤️"))

async def dontpingme(update, context):
    if update.effective_user.username is None:
        await update.message.set_reaction(ReactionTypeEmoji("👎"))
        return

    state = load_state()
    username = "@" + update.effective_user.username   
    if username in state["ping_users"]:
        state["ping_users"].remove(username)

    json_utils.save_json(json_filename, state)
    await update.message.set_reaction(ReactionTypeEmoji("💔"))

async def main_loop(bot, chat_id):
    logger.info(__name__ + " loaded")
    load_csv()
    while True:
        sleep_time = get_sleep_time()
        await asyncio.sleep(sleep_time)

        text_message = get_next_message()
        await bot.send_message(
            chat_id=chat_id,
            text=text_message,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        logger.info(f"Sent leetcode problem:\n{text_message}")


