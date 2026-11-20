import time
import httpx
from typing import Optional, Dict, Any

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (compatible; ApexSpider/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1"
}

class FetchResult:
    def __init__(
        self,
        url: str,
        status_code: int = 0,
        html: str = "",
        headers: Optional[Dict[str, str]] = None,
        elapsed_ms: float = 0.0,
        error: Optional[str] = None,
        final_url: Optional[str] = None
    ):
        self.url = url
        self.status_code = status_code
        self.html = html
        self.headers = headers or {}
        self.elapsed_ms = elapsed_ms
        self.error = error
        self.final_url = final_url or url

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300 and bool(self.html)

class AsyncFetcher:
    """High-performance asynchronous HTTP fetcher with connection pooling and resiliency."""
    def __init__(self, timeout: float = 10.0, max_redirects: int = 5):
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
        self.client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            follow_redirects=True,
            max_redirects=self.max_redirects,
            verify=False,  # Resilient to invalid/self-signed certs during web crawl
            limits=limits
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def fetch(self, url: str) -> FetchResult:
        """Fetches a URL and returns structured FetchResult."""
        if not self.client:
            raise RuntimeError("AsyncFetcher must be used as an async context manager.")

        start_time = time.perf_counter()
        try:
            resp = await self.client.get(url)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            content_type = resp.headers.get("content-type", "").lower()
            # Fast check: skip binary files (pdf, zip, exe, images, videos)
            if content_type and not any(ct in content_type for ct in ("text/html", "application/xhtml+xml", "text/plain")):
                return FetchResult(
                    url=url,
                    status_code=resp.status_code,
                    elapsed_ms=elapsed_ms,
                    error=f"Unsupported Content-Type: {content_type}",
                    final_url=str(resp.url)
                )

            return FetchResult(
                url=url,
                status_code=resp.status_code,
                html=resp.text,
                headers=dict(resp.headers),
                elapsed_ms=elapsed_ms,
                final_url=str(resp.url)
            )

        except httpx.TimeoutException:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return FetchResult(url=url, error="Request Timeout", elapsed_ms=elapsed_ms)
        except httpx.ConnectError:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return FetchResult(url=url, error="Connection Failed", elapsed_ms=elapsed_ms)
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return FetchResult(url=url, error=str(e), elapsed_ms=elapsed_ms)

