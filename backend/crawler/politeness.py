import asyncio
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx

class RobotsManager:
    """
    Handles robots.txt fetching, parsing, caching, and politeness delays.
    Mimics Googlebot polite crawling behaviors.
    """
    def __init__(self, user_agent: str = "ApexSpider/1.0 (+http://google-sim.local/bot)", default_delay: float = 0.5):
        self.user_agent = user_agent
        self.default_delay = default_delay
        self._parsers = {}        # domain -> RobotFileParser
        self._last_access = {}     # domain -> float timestamp
        self._locks = {}           # domain -> asyncio.Lock
        self._sitemaps = {}        # domain -> list of sitemap urls

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def _get_lock(self, domain: str) -> asyncio.Lock:
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    async def fetch_robots_txt(self, domain: str, client: httpx.AsyncClient) -> RobotFileParser:
        """Fetches and parses robots.txt for a given domain."""
        if domain in self._parsers:
            return self._parsers[domain]

        parser = RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            resp = await client.get(robots_url, timeout=5.0)
            if resp.status_code == 200:
                parser.parse(resp.text.splitlines())
                # Discover sitemaps if any
                sitemaps = []
                for line in resp.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        sitemaps.append(line.split(":", 1)[1].strip())
                self._sitemaps[domain] = sitemaps
            else:
                # If robots.txt returns 404 or fails, RFC standard allows crawling everything
                parser.allow_all = True
        except Exception:
            # On network timeout or connection error, default to allow
            parser.allow_all = True

        self._parsers[domain] = parser
        return parser

    async def is_allowed(self, url: str, client: httpx.AsyncClient) -> bool:
        """Checks if crawling this URL is permitted by robots.txt."""
        domain = self._get_domain(url)
        if not domain:
            return False

        parser = await self.fetch_robots_txt(domain, client)
        try:
            allowed = parser.can_fetch(self.user_agent, url)
            if allowed is None:
                # Fallback to wildcard
                allowed = parser.can_fetch("*", url)
            return True if allowed is None else bool(allowed)
        except Exception:
            return True

    def get_crawl_delay(self, domain: str) -> float:
        """Gets crawl delay specified in robots.txt, or default politeness delay."""
        parser = self._parsers.get(domain)
        if parser:
            try:
                delay = parser.crawl_delay(self.user_agent)
                if delay is None:
                    delay = parser.crawl_delay("*")
                if delay and delay > 0:
                    return min(float(delay), 10.0)  # cap at 10s to prevent starvation
            except Exception:
                pass
        return self.default_delay

    async def wait_for_politeness(self, domain: str, custom_delay: float = None):
        """Ensures consecutive requests to the same domain wait the politeness duration."""
        lock = self._get_lock(domain)
        async with lock:
            delay = custom_delay if custom_delay is not None else self.get_crawl_delay(domain)
            now = time.time()
            last = self._last_access.get(domain, 0.0)
            elapsed = now - last
            
            if elapsed < delay:
                wait_time = delay - elapsed
                await asyncio.sleep(wait_time)
            
            self._last_access[domain] = time.time()

    def get_discovered_sitemaps(self, domain: str) -> list:
        return self._sitemaps.get(domain, [])

