import asyncio
import time
import httpx
from typing import List, Dict, Any, Optional

# Active Global RPC & HTTP Ping Services
PING_SERVICES = [
    # 1. XML-RPC Weblog Ping Servers
    {
        "name": "Ping-O-Matic (RPC)",
        "url": "http://rpc.pingomatic.com/",
        "type": "xmlrpc"
    },
    {
        "name": "Twingly Global Ping",
        "url": "http://rpc.twingly.com",
        "type": "xmlrpc"
    },
    {
        "name": "FeedBurner / Google RPC",
        "url": "http://ping.feedburner.com/",
        "type": "xmlrpc"
    },
    {
        "name": "Blo.gs Ping",
        "url": "http://ping.blo.gs/",
        "type": "xmlrpc"
    },

    # 2. WebSub (PubSubHubbub) Real-Time Hubs (Google's Official Push Architecture)
    {
        "name": "Google WebSub (PubSubHubbub)",
        "url": "https://pubsubhubbub.appspot.com/publish",
        "type": "websub"
    },
    {
        "name": "Superfeedr WebSub Hub",
        "url": "https://pubsubhubbub.superfeedr.com/",
        "type": "websub"
    },

    # 3. HTTP Form & Aggregator Engines
    {
        "name": "Ping-O-Matic (HTTP)",
        "url": "https://pingomatic.com/ping/",
        "type": "pingomatic_http"
    },
    {
        "name": "FeedShark / Multi-Pinger Relay",
        "url": "https://pingomatic.com/ping/",
        "type": "feedshark"
    }
]

STANDARD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

class PingEngine:
    """
    High-velocity multi-service ping aggregator.
    Dispatches notifications across:
    1. XML-RPC Weblog Ping Endpoints (Ping-O-Matic, Twingly, FeedBurner, Blo.gs)
    2. WebSub (PubSubHubbub) Real-time Hubs (Google Appspot & Superfeedr)
    3. HTTP ping forms with automated redirect resolution
    4. Back-to-Back 10x Burst mode for guaranteed discovery
    """

    def __init__(self, site_name: str = "ApexSearch Live Feed", site_url: str = "http://localhost:8000"):
        self.site_name = site_name
        self.site_url = site_url
        self.services = PING_SERVICES

    def _build_xmlrpc_payload(self, title: str, page_url: str, rss_url: str = "") -> str:
        """Constructs standard, strictly formatted XML-RPC weblogUpdates.extendedPing body."""
        feed = rss_url or page_url
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<methodCall>
  <methodName>weblogUpdates.extendedPing</methodName>
  <params>
    <param><value><string>{title}</string></value></param>
    <param><value><string>{page_url}</string></value></param>
    <param><value><string>{feed}</string></value></param>
    <param><value><string>{feed}</string></value></param>
  </params>
</methodCall>"""

    def _build_simple_xmlrpc(self, title: str, page_url: str) -> str:
        """Fallback classic weblogUpdates.ping payload."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<methodCall>
  <methodName>weblogUpdates.ping</methodName>
  <params>
    <param><value><string>{title}</string></value></param>
    <param><value><string>{page_url}</string></value></param>
  </params>
</methodCall>"""

    async def ping_single(self, client: httpx.AsyncClient, service: Dict[str, str], title: str, page_url: str, rss_url: str) -> Dict[str, Any]:
        """Pings a single ping service with error resilience and redirect following."""
        start = time.perf_counter()
        name = service["name"]
        url = service["url"]
        stype = service["type"]

        try:
            if stype == "xmlrpc":
                payload = self._build_xmlrpc_payload(title, page_url, rss_url)
                resp = await client.post(
                    url,
                    content=payload.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "User-Agent": STANDARD_USER_AGENT
                    },
                    timeout=7.0
                )

                # If extended ping is not accepted, retry with simple ping
                if resp.status_code == 400:
                    simple_payload = self._build_simple_xmlrpc(title, page_url)
                    resp = await client.post(
                        url,
                        content=simple_payload.encode("utf-8"),
                        headers={
                            "Content-Type": "text/xml; charset=utf-8",
                            "User-Agent": STANDARD_USER_AGENT
                        },
                        timeout=5.0
                    )

                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                is_success = resp.status_code in (200, 201) or ("flerror" in resp.text.lower() and "<boolean>0</boolean>" in resp.text.lower())
                return {
                    "service": name,
                    "url": url,
                    "type": "XML-RPC",
                    "status_code": resp.status_code,
                    "success": is_success,
                    "elapsed_ms": elapsed_ms
                }

            elif stype == "websub":
                data = {"hub.mode": "publish", "hub.url": rss_url or page_url}
                resp = await client.post(
                    url,
                    data=data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": STANDARD_USER_AGENT
                    },
                    timeout=7.0
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                return {
                    "service": name,
                    "url": url,
                    "type": "WebSub",
                    "status_code": resp.status_code,
                    "success": resp.status_code in (200, 202, 204),
                    "elapsed_ms": elapsed_ms
                }

            elif stype in ("pingomatic_http", "feedshark"):
                params = {
                    "title": title,
                    "blogurl": page_url,
                    "rssurl": rss_url or page_url,
                    "chk_blogs": "on",
                    "chk_feedburner": "on",
                    "chk_twingly": "on",
                    "chk_newsisfree": "on"
                }
                resp = await client.get(
                    url,
                    params=params,
                    headers={"User-Agent": STANDARD_USER_AGENT},
                    timeout=7.0
                )
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                return {
                    "service": name,
                    "url": url,
                    "type": "HTTP-FORM",
                    "status_code": resp.status_code,
                    "success": resp.status_code in (200, 301, 302),
                    "elapsed_ms": elapsed_ms
                }

        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            return {
                "service": name,
                "url": url,
                "type": stype.upper(),
                "status_code": 0,
                "success": False,
                "error": str(e),
                "elapsed_ms": elapsed_ms
            }

    async def broadcast_ping(self, title: str, page_url: str, rss_url: str = "") -> Dict[str, Any]:
        """Concurrent fan-out broadcast to all ping services."""
        start_all = time.perf_counter()
        
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, limits=limits, verify=False) as client:
            tasks = [
                self.ping_single(client, s, title, page_url, rss_url)
                for s in PING_SERVICES
            ]
            results = await asyncio.gather(*tasks)

        total_elapsed = round((time.perf_counter() - start_all) * 1000, 1)
        successful_count = sum(1 for r in results if r.get("success"))

        return {
            "title": title,
            "target_url": page_url,
            "total_services": len(PING_SERVICES),
            "successful_pings": successful_count,
            "total_latency_ms": total_elapsed,
            "dispatches": results
        }

    async def burst_10x_pings(
        self,
        urls: List[str],
        title: str = "ApexSearch Live Feed",
        custom_rss_url: str = "",
        repeat_count: int = 10,
        delay_between_rounds: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executes back-to-back 10x ping iterations for each submitted URL
        across all ping services with automated redirect following.
        """
        start_time = time.perf_counter()
        overall_results = []
        total_pings_sent = 0

        limits = httpx.Limits(max_keepalive_connections=30, max_connections=60)
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, limits=limits, verify=False) as client:
            for url_idx, target_url in enumerate(urls):
                url_pings = []
                for round_num in range(1, repeat_count + 1):
                    tasks = [
                        self.ping_single(client, s, f"{title} (Round {round_num})", target_url, custom_rss_url)
                        for s in PING_SERVICES
                    ]
                    round_results = await asyncio.gather(*tasks)
                    total_pings_sent += len(round_results)
                    url_pings.append({
                        "round": round_num,
                        "successful": sum(1 for r in round_results if r.get("success")),
                        "total_services": len(round_results)
                    })

                    if delay_between_rounds > 0 and round_num < repeat_count:
                        await asyncio.sleep(delay_between_rounds)

                overall_results.append({
                    "url": target_url,
                    "rounds_completed": repeat_count,
                    "summary": url_pings
                })

        total_elapsed = round((time.perf_counter() - start_time) * 1000, 1)
        return {
            "status": "completed",
            "total_urls": len(urls),
            "repeat_per_url": repeat_count,
            "total_pings_sent": total_pings_sent,
            "total_elapsed_ms": total_elapsed,
            "details": overall_results
        }
