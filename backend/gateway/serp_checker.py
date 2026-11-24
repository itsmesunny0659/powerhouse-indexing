"""
Real-Time Live SERP Radar & Index Status Checker
Scrapes and verifies actual Google & Bing search engine result pages (SERPs)
to provide real-time proof of whether a submitted URL has been indexed.
"""

import asyncio
import urllib.parse
import re
import datetime
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

class SerpCheckerEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0"
        }

    async def check_google_serp(self, client: httpx.AsyncClient, target_url: str) -> Dict[str, Any]:
        """Checks if URL is physically indexed in Google Search using site: and exact slug match."""
        clean_url = target_url.strip()
        encoded = urllib.parse.quote(clean_url, safe='')
        search_query_url = f"https://www.google.com/search?q=site%3A{encoded}&hl=en"

        try:
            resp = await client.get(search_query_url, timeout=10.0)
            html = resp.text

            # 1. Detect anti-bot redirect or challenges (Google Cloud / Vercel IP shielding)
            bot_shields = [
                "please click here if you are not redirected",
                "unusual traffic",
                "recaptcha",
                "sorry/index",
                "consent.google.com"
            ]
            is_shielded = any(s in html.lower() for s in bot_shields)

            # 2. Extract meaningful slug from target URL to avoid false positives
            parsed = urllib.parse.urlparse(clean_url)
            slugs = [p for p in parsed.path.split('/') if p and p.lower() not in ('home', 'view', 'index', 'posts')]
            unique_slug = slugs[-1].lower() if slugs else parsed.netloc.lower()

            is_indexed = False
            if not is_shielded and resp.status_code == 200:
                # Require genuine organic result containers
                organic_containers = re.findall(r'<div[^>]+class=[\'"][^\'"]*(?:g|tF2Cxc|yuRUbf|MjjYud)[^\'"]*[\'"][^>]*>([\s\S]*?)</div>', html, re.IGNORECASE)
                for c in organic_containers:
                    if unique_slug in c.lower() and "/search?" not in c:
                        is_indexed = True
                        break

            return {
                "search_engine": "Google",
                "is_indexed": is_indexed,
                "status": "INDEXED_IN_SERP" if is_indexed else "PENDING_CRAWL_EVALUATION",
                "search_url": search_query_url,
                "status_code": resp.status_code,
                "is_bot_shielded": is_shielded
            }
        except Exception as e:
            return {
                "search_engine": "Google",
                "is_indexed": False,
                "status": "PENDING_CRAWL_EVALUATION",
                "error": str(e),
                "search_url": search_query_url
            }

    async def check_bing_serp(self, client: httpx.AsyncClient, target_url: str) -> Dict[str, Any]:
        """Checks if URL is indexed in Bing (IndexNow protocol validation)."""
        clean_url = target_url.strip()
        encoded = urllib.parse.quote(clean_url, safe='')
        search_query_url = f"https://www.bing.com/search?q=url%3A{encoded}&mkt=en-US"

        try:
            resp = await client.get(search_query_url, timeout=10.0)
            html = resp.text

            parsed = urllib.parse.urlparse(clean_url)
            slugs = [p for p in parsed.path.split('/') if p and p.lower() not in ('home', 'view', 'index')]
            unique_slug = slugs[-1].lower() if slugs else parsed.netloc.lower()

            is_indexed = False
            if resp.status_code == 200:
                # Organic results in Bing are strictly inside <li class="b_algo">
                algo_items = re.findall(r'<li[^>]+class=[\'"][^\'"]*b_algo[^\'"]*[\'"][^>]*>([\s\S]*?)</li>', html, re.IGNORECASE)
                for item in algo_items:
                    if unique_slug in item.lower():
                        is_indexed = True
                        break

            return {
                "search_engine": "Bing",
                "is_indexed": is_indexed,
                "status": "INDEXED_IN_SERP" if is_indexed else "PENDING_CRAWL_EVALUATION",
                "search_url": search_query_url,
                "status_code": resp.status_code
            }
        except Exception as e:
            return {
                "search_engine": "Bing",
                "is_indexed": False,
                "status": "PENDING_CRAWL_EVALUATION",
                "error": str(e),
                "search_url": search_query_url
            }

    async def verify_url_index_status(self, target_url: str) -> Dict[str, Any]:
        """Performs parallel live SERP verification across Google and Bing."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        async with httpx.AsyncClient(headers=self.headers, verify=False, follow_redirects=True) as client:
            g_task = self.check_google_serp(client, target_url)
            b_task = self.check_bing_serp(client, target_url)
            g_res, b_res = await asyncio.gather(g_task, b_task, return_exceptions=True)

        google_status = g_res if not isinstance(g_res, Exception) else {"is_indexed": False, "error": str(g_res)}
        bing_status = b_res if not isinstance(b_res, Exception) else {"is_indexed": False, "error": str(b_res)}

        is_any_indexed = google_status.get("is_indexed", False) or bing_status.get("is_indexed", False)

        return {
            "target_url": target_url,
            "checked_at": now_iso,
            "is_indexed_any": is_any_indexed,
            "google_status": google_status,
            "bing_status": bing_status,
            "verdict": "VERIFIED_LIVE_IN_SERP" if is_any_indexed else "NOT_INDEXED_YET"
        }

serp_checker = SerpCheckerEngine()
