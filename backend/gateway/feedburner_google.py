import asyncio
import time
import httpx
from typing import Dict, Any, Optional

class FeedburnerGoogleClient:
    """
    Automates and manages feeds on official Google FeedBurner (https://feedburner.google.com/).
    Connects with Google's WebSub (PubSubHubbub) hub which powers real-time FeedBurner syndication.
    """
    BASE_URL = "https://feedburner.google.com"
    WEBSUB_HUB = "https://pubsubhubbub.appspot.com/publish"

    def __init__(self, account_email: str = "its.me.sunny.0659@gmail.com"):
        self.account_email = account_email
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    async def notify_feedburner_update(self, feed_url: str, custom_proxy_title: str = "") -> Dict[str, Any]:
        """
        Notifies Google's FeedBurner real-time ingestion hub about updates to the feed.
        This signals Google's FeedBurner crawler to immediately pull and index new URLs in the feed.
        """
        start = time.perf_counter()
        
        async with httpx.AsyncClient(headers=self.headers, timeout=10.0, follow_redirects=True, verify=False) as client:
            try:
                # 1. Dispatch real-time publish notification to Google WebSub Hub (FeedBurner backend)
                data = {
                    "hub.mode": "publish",
                    "hub.url": feed_url
                }
                resp = await client.post(
                    self.WEBSUB_HUB,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

                is_success = resp.status_code in (200, 204)
                return {
                    "platform": "Google FeedBurner (feedburner.google.com)",
                    "account": self.account_email,
                    "feed_url": feed_url,
                    "hub": self.WEBSUB_HUB,
                    "status_code": resp.status_code,
                    "success": is_success,
                    "message": "FeedBurner Google real-time ingestion notified successfully" if is_success else f"HTTP {resp.status_code}",
                    "elapsed_ms": elapsed_ms
                }
            except Exception as e:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                return {
                    "platform": "Google FeedBurner (feedburner.google.com)",
                    "account": self.account_email,
                    "feed_url": feed_url,
                    "status_code": 0,
                    "success": False,
                    "error": str(e),
                    "elapsed_ms": elapsed_ms
                }
