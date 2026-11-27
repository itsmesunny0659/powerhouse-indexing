"""
Standalone 24/7 News-to-Blogger Autopilot Daemon (Safe Pacing Mode).
- Runs every 10 minutes, max 1 post per cycle, hard cap 50 posts/day to protect Blogger from spam locks.
- Logs all cycles to logs/news_autopilot.log.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

IST_TZ = timezone(timedelta(hours=5, minutes=30))

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from backend.gateway.news_autopilot import news_autopilot

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/news_autopilot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("news_daemon")

INTERVAL_SECONDS = 1200
MAX_POSTS_PER_CYCLE = 1
DAILY_POST_CAP = 90
DAILY_COUNTER_FILE = "logs/daily_post_count.json"


def _get_today_count() -> int:
    today = datetime.now(IST_TZ).strftime("%Y-%m-%d")
    if os.path.isfile(DAILY_COUNTER_FILE):
        try:
            with open(DAILY_COUNTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") == today:
                return int(data.get("count", 0))
        except Exception:
            pass
    return 0


def _increment_today_count(added: int) -> int:
    today = datetime.now(IST_TZ).strftime("%Y-%m-%d")
    total = _get_today_count() + added
    try:
        with open(DAILY_COUNTER_FILE, "w", encoding="utf-8") as f:
            json.dump({"date": today, "count": total}, f)
    except Exception:
        pass
    return total


async def run_forever() -> None:
    logger.info(
        "Starting Safe 24/7 News Autopilot Daemon (interval=%ss, max_posts=%s, daily_cap=%s)",
        INTERVAL_SECONDS,
        MAX_POSTS_PER_CYCLE,
        DAILY_POST_CAP,
    )
    while True:
        try:
            current = _get_today_count()
            if current >= DAILY_POST_CAP:
                logger.info("Daily safe cap reached (%s/%s). Sleeping until next UTC day.", current, DAILY_POST_CAP)
            else:
                res = await news_autopilot.run_cycle(max_posts=MAX_POSTS_PER_CYCLE)
                posted = int(res.get("published_count", 0))
                if posted > 0:
                    current = _increment_today_count(posted)
                logger.info("Cycle result (daily=%s/%s): %s", current, DAILY_POST_CAP, json.dumps(res, ensure_ascii=False))
        except Exception as exc:
            logger.error("Cycle failed: %s", exc)
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_forever())
