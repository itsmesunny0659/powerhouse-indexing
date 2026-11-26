"""
Standalone 24/7 News-to-Blogger Autopilot Daemon.
Runs continuously every 5 minutes without needing chat prompts.
Logs all cycles to logs/news_autopilot.log.
"""

import asyncio
import json
import logging
import os
import sys
import time

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

INTERVAL_SECONDS = 300
MAX_POSTS_PER_CYCLE = 3


async def run_forever() -> None:
    logger.info("Starting 24/7 News-to-Blogger Autopilot Daemon (interval=%ss, max_posts=%s)", INTERVAL_SECONDS, MAX_POSTS_PER_CYCLE)
    while True:
        try:
            res = await news_autopilot.run_cycle(max_posts=MAX_POSTS_PER_CYCLE)
            logger.info("Cycle result: %s", json.dumps(res, ensure_ascii=False))
        except Exception as exc:
            logger.error("Cycle failed: %s", exc)
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_forever())
