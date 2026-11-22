import re
import httpx
from typing import Dict, Any

class IndexabilityChecker:
    """
    Pre-flight audit engine:
    Verifies that a target URL is NOT blocked by:
    1. HTTP Response 'X-Robots-Tag: noindex'
    2. HTML '<meta name="robots" content="noindex">'
    3. HTTP status errors (404, 403, 500)
    Prevents wasting indexing quota on unindexable pages.
    """

    @staticmethod
    async def check(url: str, timeout: float = 5.0) -> Dict[str, Any]:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
                res = await client.get(url, headers=headers)

                # Check HTTP Status Code
                if res.status_code >= 400:
                    return {
                        "is_indexable": False,
                        "status_code": res.status_code,
                        "reason": f"HTTP status error: {res.status_code}"
                    }

                # Check X-Robots-Tag header
                x_robots = res.headers.get("x-robots-tag", "").lower()
                if "noindex" in x_robots:
                    return {
                        "is_indexable": False,
                        "status_code": res.status_code,
                        "reason": f"Blocked by HTTP header 'X-Robots-Tag: {x_robots}'"
                    }

                # Check HTML meta robots
                html = res.text[:20000]  # scan head section
                if re.search(r'<meta[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex[^"\']*["\']', html, re.I):
                    return {
                        "is_indexable": False,
                        "status_code": res.status_code,
                        "reason": "Blocked by HTML '<meta name=\"robots\" content=\"noindex\">'"
                    }

                return {
                    "is_indexable": True,
                    "status_code": res.status_code,
                    "reason": "URL is clean and indexable"
                }

        except Exception as e:
            # If network error or timeout, allow it (don't block submission)
            return {
                "is_indexable": True,
                "status_code": 0,
                "reason": f"Pre-check bypassed (Network/Timeout: {str(e)})"
            }
