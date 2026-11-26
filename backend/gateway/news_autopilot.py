"""
24/7 Automated News-to-Blogger Autopilot Engine
Monitors Google News, AajTak, and ABP News RSS feeds:
1. Deduplicates against live Blogger Atom/JSON feed (stateless & cloud-persistent).
2. Extracts full article body + og:image.
3. Rephrases headline & article content (Gemini API if configured, else clean structural rewriter).
4. Modifies featured image via Pillow (crop, color/contrast shift, EXIF strip, compact JPEG).
5. Publishes to Blogger -> WebSub (204) -> GCP Indexing API v3 (200 OK via myindexingtool004).
"""

import base64
import io
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    ("AajTak", "https://www.aajtak.in/rssfeeds/?id=home"),
    ("ABP News", "https://news.abplive.com/news/india/feed"),
    ("ABP Hindi", "https://www.abplive.com/home/feed"),
    ("Google News India", "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News Hindi", "https://news.google.com/rss?hl=hi&gl=IN&ceid=IN:hi"),
]

BLOG_JSON_FEED = "https://sunnyjaiswalblogs.blogspot.com/feeds/posts/default?alt=json&max-results=40"


def _normalize_title(text: str) -> str:
    cleaned = re.sub(r"\s*[-|]\s*(Aaj\s*Tak|ABP\s*Live|ABP\s*News|Google\s*News).*$", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s]", "", cleaned.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


class NewsAutopilotEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        }

    async def _fetch_existing_titles(self, client: httpx.AsyncClient) -> List[str]:
        try:
            r = await client.get(BLOG_JSON_FEED, timeout=10.0)
            if r.status_code == 200:
                entries = r.json().get("feed", {}).get("entry", [])
                return [_normalize_title(e.get("title", {}).get("$t", "")) for e in entries]
        except Exception as e:
            logger.warning(f"[NewsAutopilot] Failed to read existing Blogger feed: {e}")
        return []

    async def _fetch_rss_items(self, client: httpx.AsyncClient) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        for source_name, feed_url in RSS_FEEDS:
            try:
                r = await client.get(feed_url, timeout=10.0)
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:5]:
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    desc = (item.findtext("description") or "").strip()
                    pub_date = (item.findtext("pubDate") or "").strip()
                    if title and link:
                        items.append({
                            "source": source_name,
                            "title": title,
                            "link": link,
                            "description": BeautifulSoup(desc, "html.parser").get_text(" ", strip=True),
                            "pubDate": pub_date,
                        })
            except Exception as e:
                logger.warning(f"[NewsAutopilot] RSS error ({source_name}): {e}")
        return items

    async def _extract_article(self, client: httpx.AsyncClient, url: str, fallback_desc: str) -> Tuple[str, Optional[str]]:
        body_paragraphs: List[str] = []
        image_url: Optional[str] = None
        try:
            r = await client.get(url, follow_redirects=True, timeout=12.0)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                if og_img and og_img.get("content"):
                    image_url = og_img["content"].strip()
                for p in soup.find_all("p"):
                    txt = p.get_text(" ", strip=True)
                    if len(txt) > 55 and not any(bad in txt.lower() for bad in ("cookie", "subscribe", "copyright", "read more", "whatsapp", "telegram")):
                        body_paragraphs.append(txt)
                    if len(body_paragraphs) >= 6:
                        break
        except Exception as e:
            logger.warning(f"[NewsAutopilot] Article fetch error ({url[:60]}): {e}")

        raw_text = "\n\n".join(body_paragraphs) if body_paragraphs else fallback_desc
        return raw_text[:2800], image_url

    async def _modify_image_base64(self, client: httpx.AsyncClient, image_url: Optional[str]) -> Optional[str]:
        if not image_url or not image_url.startswith("http"):
            return None
        try:
            from PIL import Image, ImageEnhance
            r = await client.get(image_url, follow_redirects=True, timeout=10.0)
            if r.status_code != 200 or len(r.content) < 2000:
                return None
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if w < 120 or h < 120:
                return None
            # Crop 4% margins to alter visual hash & remove border watermarks
            dx, dy = int(w * 0.04), int(h * 0.04)
            img = img.crop((dx, dy, w - dx, h - dy))
            if img.width > 720:
                new_h = int(img.height * (720 / img.width))
                img = img.resize((720, new_h), Image.Resampling.LANCZOS)
            img = ImageEnhance.Brightness(img).enhance(1.04)
            img = ImageEnhance.Contrast(img).enhance(1.06)
            img = ImageEnhance.Sharpness(img).enhance(1.12)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=78, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            logger.warning(f"[NewsAutopilot] Image modify skipped: {e}")
            return None

    async def _rephrase_news(self, client: httpx.AsyncClient, title: str, body: str, source: str) -> Tuple[str, str]:
        clean_title = re.sub(r"\s*[-|]\s*(Aaj\s*Tak|ABP\s*Live|ABP\s*News|Google\s*News).*$", "", title, flags=re.IGNORECASE).strip()
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                prompt = (
                    "Rewrite this news headline and article in fresh, original journalistic wording "
                    "(same language as input — Hindi if input is Hindi, English if English). "
                    "Return JSON with keys 'headline' and 'paragraphs' (array of 3-4 short paragraphs). "
                    f"Original Headline: {clean_title}\nSource Text: {body[:1800]}"
                )
                gr = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=15.0,
                )
                if gr.status_code == 200:
                    raw = gr.json()["candidates"][0]["content"]["parts"][0]["text"]
                    m = re.search(r"\{.*\}", raw, re.DOTALL)
                    if m:
                        import json
                        parsed = json.loads(m.group(0))
                        new_h = parsed.get("headline") or clean_title
                        paras = parsed.get("paragraphs") or [body]
                        html_body = "".join(f"<p>{p}</p>\n" for p in paras)
                        return new_h, html_body
            except Exception as e:
                logger.warning(f"[NewsAutopilot] Gemini rephrase fallback: {e}")

        # Clean structural fallback rephraser (always works without external AI key)
        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        if not paras:
            paras = [clean_title]
        lead = paras[0]
        rest = paras[1:4]
        html_parts = [
            f"<p><strong>Latest Update:</strong> {lead}</p>",
            *[f"<p>{p}</p>" for p in rest],
            f"<p><small>News Desk Summary &bull; Coverage Reference: {source} &bull; {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}</small></p>",
        ]
        return f"{clean_title} — Latest Report", "\n".join(html_parts)

    async def run_cycle(self, max_posts: int = 1) -> Dict[str, Any]:
        """Fetches latest RSS news, skips already-posted items, rephrases, modifies image, and publishes to Blogger."""
        from backend.gateway.blogger_syndicator import blogger_syndicator

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
            existing_titles, rss_items = await asyncio.gather(
                self._fetch_existing_titles(client),
                self._fetch_rss_items(client),
            )

            published: List[Dict[str, Any]] = []
            for item in rss_items:
                if len(published) >= max_posts:
                    break
                norm = _normalize_title(item["title"])
                if not norm or any(norm[:40] in ex or ex[:40] in norm for ex in existing_titles if ex):
                    continue

                raw_text, img_url = await self._extract_article(client, item["link"], item["description"])
                new_title, html_body = await self._rephrase_news(client, item["title"], raw_text, item["source"])
                modified_img = await self._modify_image_base64(client, img_url)

                img_tag = f'<p><img src="{modified_img}" alt="{new_title}" style="max-width:100%;border-radius:8px;"/></p>\n' if modified_img else ""
                full_html = (
                    f"{img_tag}"
                    f"<h2>{new_title}</h2>\n"
                    f"{html_body}\n"
                    f'<p>Source Link: <a href="{item["link"]}" rel="nofollow noopener">{item["source"]}</a></p>'
                )

                # Publish directly via blogger_syndicator config & auto-refresh
                cfg = blogger_syndicator._load_config()
                bid = cfg.get("blog_id")
                tok = await blogger_syndicator._refresh_access_token(client, cfg)
                if not bid or not tok:
                    return {"success": False, "status": "missing_blogger_auth"}

                pr = await client.post(
                    f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts/",
                    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                    json={"kind": "blogger#post", "blog": {"id": bid}, "title": new_title, "content": full_html},
                )
                if pr.status_code in (200, 201):
                    pdata = pr.json()
                    post_url = pdata.get("url", "")
                    # Ping WebSub + GCP Indexing API
                    blog_base = cfg.get("blog_url") or "https://sunnyjaiswalblogs.blogspot.com/"
                    try:
                        await client.post("https://pubsubhubbub.appspot.com/publish", data={"hub.mode": "publish", "hub.url": blog_base.rstrip("/") + "/feeds/posts/default"}, timeout=8.0)
                    except Exception:
                        pass
                    gcp_status = None
                    if post_url:
                        try:
                            from backend.gateway.gcp_service_account_rotator import gcp_rotator
                            gres = await gcp_rotator.submit_url(post_url, "URL_UPDATED")
                            gcp_status = gres.get("status")
                        except Exception:
                            pass
                    published.append({
                        "source": item["source"],
                        "title": new_title,
                        "post_url": post_url,
                        "image_modified": bool(modified_img),
                        "gcp_indexing_api": gcp_status,
                    })
                    existing_titles.append(_normalize_title(new_title))

            return {
                "success": True,
                "rss_scanned": len(rss_items),
                "published_count": len(published),
                "published": published,
            }


import asyncio
news_autopilot = NewsAutopilotEngine()
