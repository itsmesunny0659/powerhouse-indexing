# /modules/botnet.py
import asyncio
import random
from playwright.async_api import async_playwright
import httpx

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

PROXIES = [
    "http://user:pass@us.iproyal.com:12321",
    "http://user:pass@uk.iproyal.com:12321",
    "http://user:pass@de.iproyal.com:12321"
]

ACTIONS = ["scroll", "click", "dwell", "type", "share"]

async def human_delay(min_sec=1, max_sec=3):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def move_mouse_smooth(page, x, y):
    await page.mouse.move(0, 0)
    await page.mouse.move(x // 2, y // 2)
    await human_delay(0.5, 1.5)
    await page.mouse.move(x, y)

async def fake_human_visit(url: str):
    proxy = random.choice(PROXIES)
    ua = random.choice(USER_AGENTS)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(proxy={"server": proxy}, headless=True)
            context = await browser.new_context(user_agent=ua)
            page = await context.new_page()

            await page.goto(url, timeout=30000)

            # Random scroll
            scroll_y = random.randint(300, 2000)
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await human_delay(2, 5)

            # Simulate mouse movement
            await move_mouse_smooth(page, 400, 600)

            # Click random link
            links = await page.query_selector_all("a")
            if links:
                await random.choice(links).click(timeout=5000)
                await human_delay(3, 8)

            # Dwell time
            await human_delay(45, 120)

            await browser.close()
        except Exception as e:
            pass  # Silent fail — bots die, we don’t care

async def launch_traffic(url: str, bots: int = 10000):
    tasks = []
    for _ in range(bots):
        tasks.append(fake_human_visit(url))
        if len(tasks) >= 50:  # Limit concurrent
            await asyncio.gather(*tasks, return_exceptions=True)
            tasks = []
            await asyncio.sleep(1)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)