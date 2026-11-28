"""
Google Indexing API v3 Direct Submission Wrapper.
Supports explicit Bearer OAuth token or automatic service-account rotation via gcp_rotator.
"""

from typing import Any, Dict, Optional
import httpx


async def force_index(url: str, key: Optional[str] = None) -> Dict[str, Any]:
    if key:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        data = {"url": url, "type": "URL_UPDATED"}
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                "https://indexing.googleapis.com/v3/urlNotifications:publish",
                json=data,
                headers=headers,
            )
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            return {"status": resp.status_code, "url": url, "response": body}

    from backend.gateway.gcp_service_account_rotator import gcp_rotator

    return await gcp_rotator.submit_url(url, "URL_UPDATED")
