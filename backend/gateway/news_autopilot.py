"""
24/7 Automated News-to-Blogger Autopilot Engine
Monitors direct publisher RSS feeds (AajTak, NDTV, India Today, Indian Express, ABP, NBC):
1. Deduplicates against live Blogger Atom/JSON feed.
2. Extracts real article body + real featured image (RSS media/enclosure + og:image, filtering generic logos).
3. Rephrases headline, description, and lengthy 400+ word body (Gemini AI if enabled, else clean editorial rewriter).
4. Modifies featured image via Pillow (6% crop, color/contrast/sharpness shift, subtle border, EXIF strip).
5. Publishes to Blogger -> WebSub (204) -> Search Console Sitemap PUT (204) -> GCP Indexing API v3 (200 OK).
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Direct publisher RSS feeds (real article URLs & real images, avoiding Google News JS redirect icons)
RSS_FEEDS = [
    ("AajTak", "https://www.aajtak.in/rssfeeds/?id=home"),
    ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories"),
    ("India Today", "https://www.indiatoday.in/rss/home"),
    ("Indian Express", "https://indianexpress.com/section/india/feed/"),
    ("ABP News", "https://news.abplive.com/news/india/feed"),
    ("ABP Hindi", "https://www.abplive.com/home/feed"),
    ("NBC News", "https://feeds.nbcnews.com/nbcnews/public/news"),
    ("NBC World", "https://feeds.nbcnews.com/nbcnews/public/world"),
]

BLOG_JSON_FEED = "https://sunnyjaiswalblogs.blogspot.com/feeds/posts/default?alt=json&max-results=50"
BAD_IMG_PATTERNS = ("lh3.googleusercontent.com", "logo", "favicon", "default-image", "placeholder", "avatar", "sprite", "1x1")


def _normalize_title(text: str) -> str:
    cleaned = re.sub(r"\s*[-|—]\s*(Aaj\s*Tak|ABP\s*Live|ABP\s*News|NDTV|India\s*Today|Indian\s*Express|NBC\s*News|Latest\s*Report|Full\s*Update).*$", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^\w\s]", "", cleaned.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _load_gemini_key() -> Optional[str]:
    env_k = os.environ.get("GEMINI_API_KEY")
    if env_k:
        return env_k.strip()
    for fname in ("gemini_key.dat", "psi_key.dat"):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", fname)
        if os.path.isfile(p):
            try:
                import zlib
                with open(p, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                if raw:
                    return zlib.decompress(base64.b64decode(raw.encode("ascii"))).decode("utf-8").strip()
            except Exception:
                pass
    return None


class NewsAutopilotEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        }
        self.history_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "logs",
            "posted_news_urls.json",
        )

    def _load_posted_links(self) -> set:
        import tempfile
        for p in (self.history_file, os.path.join(tempfile.gettempdir(), "posted_news_urls.json")):
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        return set(data[-500:])
                except Exception:
                    pass
        return set()

    def _save_posted_links(self, links: set) -> None:
        import tempfile
        recent = list(links)[-500:]
        for p in (self.history_file, os.path.join(tempfile.gettempdir(), "posted_news_urls.json")):
            try:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(recent, f)
                return
            except Exception:
                continue

    async def _fetch_existing_titles(self, client: httpx.AsyncClient) -> List[str]:
        try:
            r = await client.get(BLOG_JSON_FEED, timeout=10.0)
            if r.status_code == 200:
                entries = r.json().get("feed", {}).get("entry", [])
                return [_normalize_title(e.get("title", {}).get("$t", "")) for e in entries]
        except Exception as e:
            logger.warning(f"[NewsAutopilot] Failed to read existing Blogger feed: {e}")
        return []

    def _extract_rss_image(self, item: ET.Element) -> Optional[str]:
        for child in item:
            tag = child.tag.lower()
            if "enclosure" in tag or "content" in tag or "thumbnail" in tag:
                url = child.attrib.get("url") or child.attrib.get("href")
                if url and url.startswith("http") and not any(b in url.lower() for b in BAD_IMG_PATTERNS):
                    return url
        desc_raw = item.findtext("description") or ""
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_raw, re.IGNORECASE)
        if m and m.group(1).startswith("http") and not any(b in m.group(1).lower() for b in BAD_IMG_PATTERNS):
            return m.group(1)
        return None

    async def _fetch_single_feed(self, client: httpx.AsyncClient, source_name: str, feed_url: str) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        try:
            r = await client.get(feed_url, timeout=8.0)
            if r.status_code != 200:
                return out
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:5]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = (item.findtext("description") or "").strip()
                rss_img = self._extract_rss_image(item)
                if title and link:
                    out.append({
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "rss_image": rss_img or "",
                        "description": BeautifulSoup(desc, "html.parser").get_text(" ", strip=True),
                    })
        except Exception as e:
            logger.warning(f"[NewsAutopilot] RSS error ({source_name}): {e}")
        return out

    async def _fetch_rss_items(self, client: httpx.AsyncClient) -> List[Dict[str, str]]:
        feed_lists = await asyncio.gather(
            *[self._fetch_single_feed(client, src, url) for src, url in RSS_FEEDS],
            return_exceptions=True,
        )
        clean_lists = [fl for fl in feed_lists if isinstance(fl, list)]
        interleaved: List[Dict[str, str]] = []
        max_len = max((len(fl) for fl in clean_lists), default=0)
        for i in range(max_len):
            for fl in clean_lists:
                if i < len(fl):
                    interleaved.append(fl[i])
        return interleaved

    async def _extract_article(self, client: httpx.AsyncClient, url: str, fallback_desc: str, rss_image: str) -> Tuple[str, Optional[str]]:
        body_paragraphs: List[str] = []
        image_url: Optional[str] = rss_image if rss_image else None
        try:
            r = await client.get(url, follow_redirects=True, timeout=12.0)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for meta in (
                    soup.find("meta", property="og:image"),
                    soup.find("meta", attrs={"name": "twitter:image"}),
                    soup.find("meta", attrs={"itemprop": "image"}),
                ):
                    if meta and meta.get("content"):
                        cand = meta["content"].strip()
                        if cand.startswith("http") and not any(b in cand.lower() for b in BAD_IMG_PATTERNS):
                            image_url = cand
                            break
                if not image_url:
                    for img in soup.find_all("img"):
                        cand = (img.get("src") or img.get("data-src") or "").strip()
                        if cand.startswith("http") and not any(b in cand.lower() for b in BAD_IMG_PATTERNS):
                            image_url = cand
                            break

                for p in soup.find_all("p"):
                    txt = p.get_text(" ", strip=True)
                    if len(txt) > 50 and not any(bad in txt.lower() for bad in ("cookie", "subscribe", "copyright", "read more", "whatsapp", "telegram", "all rights reserved", "follow us")):
                        body_paragraphs.append(txt)
                    if len(body_paragraphs) >= 10:
                        break
        except Exception as e:
            logger.warning(f"[NewsAutopilot] Article fetch error ({url[:60]}): {e}")

        raw_text = "\n\n".join(body_paragraphs) if body_paragraphs else fallback_desc
        return raw_text[:4500], image_url

    async def _modify_image_base64(self, client: httpx.AsyncClient, image_url: Optional[str]) -> Optional[str]:
        if not image_url or not image_url.startswith("http"):
            return None
        try:
            from PIL import Image, ImageEnhance, ImageOps
            r = await client.get(image_url, follow_redirects=True, timeout=10.0)
            if r.status_code != 200 or len(r.content) < 4000:
                return None
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            w, h = img.size
            if w < 250 or h < 150:
                return None
            # Crop 6% margins to strip edge watermarks & alter perceptual hash
            dx, dy = int(w * 0.06), int(h * 0.06)
            img = img.crop((dx, dy, w - dx, h - dy))
            if img.width > 760:
                new_h = int(img.height * (760 / img.width))
                img = img.resize((760, new_h), Image.Resampling.LANCZOS)
            img = ImageEnhance.Color(img).enhance(1.08)
            img = ImageEnhance.Brightness(img).enhance(1.03)
            img = ImageEnhance.Contrast(img).enhance(1.06)
            img = ImageEnhance.Sharpness(img).enhance(1.15)
            # Subtle 4px frame border
            img = ImageOps.expand(img, border=4, fill="#111827")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            logger.warning(f"[NewsAutopilot] Image modify skipped: {e}")
            return None

    async def _rephrase_news(self, client: httpx.AsyncClient, title: str, body: str, source: str) -> Tuple[str, str]:
        clean_title = re.sub(r"\s*[-|—]\s*(Aaj\s*Tak|ABP\s*Live|ABP\s*News|NDTV|India\s*Today|Indian\s*Express|NBC\s*News).*$", "", title, flags=re.IGNORECASE).strip()
        gemini_key = _load_gemini_key()
        if gemini_key:
            try:
                prompt = (
                    "You are a senior news editor. Rewrite this news headline and full article into a completely original, "
                    "lengthy (400-550 words), well-structured report in the SAME language (Hindi if Hindi, English if English). "
                    "Do NOT copy sentences verbatim; rephrase every headline, subheading, and paragraph naturally. "
                    "Return valid JSON only with keys: 'headline' (string), 'summary' (1-sentence meta description), "
                    "and 'sections' (array of 3-4 objects with 'heading' and 'body' paragraph). "
                    f"Original Headline: {clean_title}\nSource Details: {body[:3500]}"
                )
                gr = await client.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent",
                    headers={"x-goog-api-key": gemini_key, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=35.0,
                )
                if gr.status_code == 200:
                    raw = gr.json()["candidates"][0]["content"]["parts"][0]["text"]
                    m = re.search(r"\{.*\}", raw, re.DOTALL)
                    if m:
                        parsed = json.loads(m.group(0))
                        new_h = parsed.get("headline") or clean_title
                        summary = parsed.get("summary") or ""
                        sections = parsed.get("sections") or []
                        html_parts = [f"<p><em>{summary}</em></p>"] if summary else []
                        for sec in sections:
                            if sec.get("heading"):
                                html_parts.append(f"<h3>{sec['heading']}</h3>")
                            if sec.get("body"):
                                html_parts.append(f"<p>{sec['body']}</p>")
                        html_parts.append(f"<p><small>24hrsNewsOnline Editorial Desk &bull; {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}</small></p>")
                        return new_h, "\n".join(html_parts)
            except Exception as e:
                logger.warning(f"[NewsAutopilot] Gemini rephrase fallback: {e}")

        # Enhanced non-AI structural rephraser: rewrites headline framing & builds lengthy multi-section coverage
        is_hindi = bool(re.search(r"[\u0900-\u097F]", clean_title))
        paras = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 30]
        if not paras:
            paras = [clean_title]

        if is_hindi:
            rephrased_title = f"ताज़ा बड़ी खबर: {clean_title} — पूरी जानकारी और मुख्य बातें"
            html_parts = [
                f"<p><strong>मुख्य अपडेट:</strong> {paras[0]}</p>",
                "<h3>विस्तृत घटनाक्रम</h3>",
                *[f"<p>{p}</p>" for p in paras[1:4]],
                "<h3>प्रमुख बिंदु और विश्लेषण</h3>",
                f"<p>ताज़ा मीडिया रिपोर्ट्स और आधिकारिक अपडेट्स के अनुसार यह विषय इस समय चर्चा में है। पाठकों को सटीक और तेज़ जानकारी उपलब्ध कराने के लिए इस खबर के सभी महत्वपूर्ण पहलुओं को यहाँ संकलित किया गया है।</p>",
                *[f"<p>{p}</p>" for p in paras[4:7]],
                f"<p><small>24hrsNewsOnline Desk &bull; Public News Dispatch Summary &bull; {time.strftime('%d %b %Y, %H:%M UTC', time.gmtime())}</small></p>",
            ]
        else:
            rephrased_title = f"Developing Story: {clean_title} | Key Updates & Full Breakdown"
            html_parts = [
                f"<p><strong>Executive Brief:</strong> {paras[0]}</p>",
                "<h3>Key Developments &amp; Background</h3>",
                *[f"<p>{p}</p>" for p in paras[1:4]],
                "<h3>Broader Context &amp; Takeaways</h3>",
                "<p>Following recent public dispatches and ongoing coverage, observers and stakeholders are closely monitoring further official announcements on this development. Below are additional details gathered around this report.</p>",
                *[f"<p>{p}</p>" for p in paras[4:7]],
                f"<p><small>24hrsNewsOnline Editorial Desk &bull; Compiled Report &bull; {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}</small></p>",
            ]
        return rephrased_title, "\n".join(html_parts)

    async def _ping_gsc_sitemap(self, site_url: str) -> Optional[int]:
        try:
            import urllib.parse
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            from backend.gateway.gcp_service_account_rotator import gcp_rotator

            acc = next((a for a in gcp_rotator.account_pool if "myindexingtool004" in a.get("email", "")), None)
            if not acc:
                return None
            creds = service_account.Credentials.from_service_account_info(
                acc["key_data"], scopes=["https://www.googleapis.com/auth/webmasters"]
            )
            creds.refresh(Request())
            es = urllib.parse.quote(site_url, safe="")
            base = site_url.rstrip("/")
            last_code = None
            async with httpx.AsyncClient(timeout=8.0) as gc:
                for path in ("/sitemap.xml", "/rss.xml", "/atom.xml"):
                    esm = urllib.parse.quote(base + path, safe="")
                    resp = await gc.put(
                        f"https://www.googleapis.com/webmasters/v3/sites/{es}/sitemaps/{esm}",
                        headers={"Authorization": f"Bearer {creds.token}"}
                    )
                    last_code = resp.status_code
            return last_code
        except Exception:
            return None

    async def run_cycle(self, max_posts: int = 3) -> Dict[str, Any]:
        from backend.gateway.blogger_syndicator import blogger_syndicator

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
            existing_titles, rss_items = await asyncio.gather(
                self._fetch_existing_titles(client),
                self._fetch_rss_items(client),
            )
            posted_links = self._load_posted_links()

            published: List[Dict[str, Any]] = []
            for item in rss_items:
                if len(published) >= max_posts:
                    break
                if item["link"] in posted_links:
                    continue
                norm = _normalize_title(item["title"])
                if not norm or any(norm[:32] in ex or ex[:32] in norm for ex in existing_titles if ex):
                    continue

                raw_text, img_url = await self._extract_article(client, item["link"], item["description"], item.get("rss_image", ""))
                new_title, html_body = await self._rephrase_news(client, item["title"], raw_text, item["source"])
                modified_img = await self._modify_image_base64(client, img_url)

                img_tag = f'<p><img src="{modified_img}" alt="{new_title}" style="max-width:100%;border-radius:8px;"/></p>\n' if modified_img else ""
                full_html = (
                    f"{img_tag}"
                    f"<h2>{new_title}</h2>\n"
                    f"{html_body}"
                )

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
                    existing_titles.append(_normalize_title(item["title"]))
                    existing_titles.append(_normalize_title(new_title))
                    posted_links.add(item["link"])

            if published:
                self._save_posted_links(posted_links)

            gsc_sitemap_status = None
            if published:
                gsc_sitemap_status = await self._ping_gsc_sitemap("https://sunnyjaiswalblogs.blogspot.com/")

            return {
                "success": True,
                "rss_scanned": len(rss_items),
                "published_count": len(published),
                "gsc_sitemap_put": gsc_sitemap_status,
                "published": published,
            }


news_autopilot = NewsAutopilotEngine()
