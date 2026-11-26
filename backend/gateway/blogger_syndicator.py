"""
Blogger (*.blogspot.com) Auto-Syndication & Native Google WebSub Engine.
Publishes clean static HTML directory posts via Blogger API v3 and immediately
pings Google's PubSubHubbub hub on the blog's Atom feed for fast Googlebot discovery.
"""

import base64
import json
import logging
import os
import time
import zlib
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

BLOGGER_API_BASE = "https://www.googleapis.com/blogger/v3"
WEBSUB_HUB = "https://pubsubhubbub.appspot.com/publish"


class BloggerSyndicator:
    def __init__(self, config_path: str = "data/blogger_config.json"):
        self.config_path = config_path

    def _load_config(
        self,
        blog_id: Optional[str] = None,
        oauth_token: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        cfg: Dict[str, Optional[str]] = {
            "blog_id": blog_id or os.environ.get("BLOGGER_BLOG_ID"),
            "oauth_token": oauth_token or os.environ.get("BLOGGER_OAUTH_TOKEN"),
            "client_id": os.environ.get("BLOGGER_CLIENT_ID"),
            "client_secret": os.environ.get("BLOGGER_CLIENT_SECRET"),
            "refresh_token": os.environ.get("BLOGGER_REFRESH_TOKEN"),
            "blog_url": os.environ.get("BLOGGER_BLOG_URL"),
        }
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    file_cfg = json.load(f)
                if isinstance(file_cfg, dict):
                    for k, v in file_cfg.items():
                        if not cfg.get(k) and v:
                            cfg[k] = v
            except Exception as e:
                logger.error(f"[Blogger] Failed to read {self.config_path}: {e}")

        vault_candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "blogger_vault.dat"),
            "data/blogger_vault.dat",
        ]
        for vp in vault_candidates:
            if os.path.isfile(vp):
                try:
                    with open(vp, "r", encoding="utf-8") as vf:
                        raw = vf.read().strip()
                    if raw:
                        v_cfg = json.loads(zlib.decompress(base64.b64decode(raw.encode("ascii"))))
                        if isinstance(v_cfg, dict):
                            for k, v in v_cfg.items():
                                if not cfg.get(k) and v:
                                    cfg[k] = v
                        break
                except Exception as e:
                    logger.error(f"[Blogger] Failed to load {vp}: {e}")
        return cfg

    async def _refresh_access_token(self, client: httpx.AsyncClient, cfg: Dict[str, Optional[str]]) -> Optional[str]:
        if cfg.get("oauth_token"):
            return cfg["oauth_token"]
        if cfg.get("refresh_token") and cfg.get("client_id") and cfg.get("client_secret"):
            try:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": cfg["client_id"],
                        "client_secret": cfg["client_secret"],
                        "refresh_token": cfg["refresh_token"],
                        "grant_type": "refresh_token",
                    },
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    return resp.json().get("access_token")
            except Exception as e:
                logger.error(f"[Blogger] Token refresh failed: {e}")
        return None

    def _build_post_html(self, urls: List[str], keyword: Optional[str] = None) -> str:
        items_html = "\n".join(
            f'<li><a href="{u}" rel="dofollow">{u}</a></li>' for u in urls
        )
        topic = keyword or "Verified Resource Directory"
        return (
            f"<p>Updated index directory for <strong>{topic}</strong>.</p>\n"
            f"<ul>\n{items_html}\n</ul>\n"
            f"<p><small>Published {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</small></p>"
        )

    async def syndicate_urls(
        self,
        urls: List[str],
        keyword: Optional[str] = None,
        blog_id: Optional[str] = None,
        oauth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not urls:
            return {"success": False, "status": "no_urls"}

        cfg = self._load_config(blog_id=blog_id, oauth_token=oauth_token)
        resolved_blog_id = cfg.get("blog_id")
        if not resolved_blog_id:
            return {
                "success": False,
                "status": "needs_credentials",
                "message": "Set BLOGGER_BLOG_ID and BLOGGER_OAUTH_TOKEN (or data/blogger_config.json) to publish directly to *.blogspot.com.",
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            token = await self._refresh_access_token(client, cfg)
            if not token:
                return {
                    "success": False,
                    "status": "needs_oauth_token",
                    "blog_id": resolved_blog_id,
                    "message": "Missing BLOGGER_OAUTH_TOKEN or OAuth refresh credentials for Blogger API v3.",
                }

            title = f"{keyword or 'Resource Directory'} — {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}"
            post_body = {
                "kind": "blogger#post",
                "blog": {"id": resolved_blog_id},
                "title": title,
                "content": self._build_post_html(urls, keyword=keyword),
            }
            resp = await client.post(
                f"{BLOGGER_API_BASE}/blogs/{resolved_blog_id}/posts/",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=post_body,
            )
            if resp.status_code not in (200, 201):
                return {
                    "success": False,
                    "status": "blogger_api_error",
                    "http_status": resp.status_code,
                    "error": resp.text[:400],
                }

            post_data = resp.json()
            post_url = post_data.get("url", "")
            blog_base = cfg.get("blog_url") or (
                post_url.split("/20")[0] if "/20" in post_url else ""
            )

            websub_status = None
            if blog_base:
                feed_url = blog_base.rstrip("/") + "/feeds/posts/default"
                try:
                    ws = await client.post(
                        WEBSUB_HUB,
                        data={"hub.mode": "publish", "hub.url": feed_url},
                        timeout=8.0,
                    )
                    websub_status = ws.status_code
                except Exception:
                    pass

            gcp_status = None
            if post_url:
                try:
                    from backend.gateway.gcp_service_account_rotator import gcp_rotator
                    gcp_res = await gcp_rotator.submit_url(post_url, "URL_UPDATED")
                    gcp_status = gcp_res.get("status")
                except Exception:
                    pass

            return {
                "success": True,
                "status": "PUBLISHED_TO_BLOGGER",
                "post_id": post_data.get("id"),
                "post_url": post_url,
                "websub_ping_status": websub_status,
                "gcp_indexing_api_status": gcp_status,
                "urls_linked": len(urls),
            }


blogger_syndicator = BloggerSyndicator()
