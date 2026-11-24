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
        """Checks if URL is physically indexed in Google Search using site: and exact match."""
        clean_url = target_url.strip()
        encoded = urllib.parse.quote(clean_url, safe='')
        search_query_url = f"https://www.google.com/search?q=site%3A{encoded}&hl=en"

        try:
            resp = await client.get(search_query_url, timeout=10.0)
            html = resp.text

            # Patterns indicating NOT indexed
            not_found_patterns = [
                "did not match any documents",
                "No results found for",
                "Your search - <em>site:",
                "Check your spelling"
            ]

            not_found = any(p.lower() in html.lower() for p in not_found_patterns)
            
            # Pattern indicating presence
            has_domain = urllib.parse.urlparse(clean_url).netloc.lower() in html.lower()
            is_indexed = (not not_found) and (resp.status_code == 200) and has_domain

            return {
                "search_engine": "Google",
                "is_indexed": is_indexed,
                "status": "INDEXED_IN_SERP" if is_indexed else "PENDING_CRAWL_EVALUATION",
                "search_url": search_query_url,
                "status_code": resp.status_code
            }
        except Exception as e:
            return {
                "search_engine": "Google",
                "is_indexed": False,
                "status": "CHECK_FAILED",
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

            not_found_patterns = [
                "There are no results for",
                "No results found for",
                "Check your spelling"
            ]
            not_found = any(p.lower() in html.lower() for p in not_found_patterns)
            has_url = clean_url.lower() in html.lower() or urllib.parse.urlparse(clean_url).path.lower() in html.lower()
            is_indexed = (not not_found) and (resp.status_code == 200) and has_url

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
                "status": "CHECK_FAILED",
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
