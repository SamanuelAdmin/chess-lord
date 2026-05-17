import logging
import random
import asyncio
import json_utils
import csv
from datetime import datetime, date, time, timedelta
from telegram import LinkPreviewOptions

logger = logging.getLogger("mainlogger")

DAILY_PROBLEM_TIME = time(6, 30) # 6:30

json_filename = "leetcode.json"
leetcode_dataset_filename = "leetcode.csv"

LEETCODE_FIELDS = []
LEETCODE_ROWS = []
LEN_LEETCODE_ROWS = 0

PING_USERS = []

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


# Returns the next available random line from leetcode.csv
def get_next_line():
    state = json_utils.load_json(json_filename)
    if not state:
        state = {
            "day" : 0,
            "completed_problems" : []
        }

    if state["day"] >= LEN_LEETCODE_ROWS:
        state["completed_problems"] = []

    line_number = pick_random_excluding(LEN_LEETCODE_ROWS, state["completed_problems"])
    state["day"] += 1
    state["completed_problems"].append(line_number)
    json_utils.save_json(json_filename, state)
    return LEETCODE_ROWS[line_number], state["day"]
    
    

# def construct_message(day_number, problem_name, url, difficulty, ping_users=[]) -> str:
# ID,Title,Difficulty,Link,Topics,Acceptance Rate (%),Premium Only,Category,Likes,Dislikes,Example Test Cases,Similar Questions
def get_next_message():
    next_line, day = get_next_line()

    return construct_message(day, next_line[1], next_line[3], next_line[2], PING_USERS)



async def main_loop(bot, chat_id):
    logger.info(__name__ + " loaded")
    load_csv()
    while True:
        sleep_time = get_sleep_time()
        await asyncio.sleep(sleep_time)

        message = get_next_message()
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        logger.info(f"Sent leetcode problem:\n{message}")


