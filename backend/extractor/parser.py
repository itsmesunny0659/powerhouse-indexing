import re
import hashlib
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from backend.crawler.dedup import normalize_url, get_domain

class ExtractedLink:
    def __init__(self, target_url: str, anchor_text: str, is_internal: bool, nofollow: bool):
        self.target_url = target_url
        self.anchor_text = anchor_text.strip()
        self.is_internal = is_internal
        self.nofollow = nofollow

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_url": self.target_url,
            "anchor_text": self.anchor_text,
            "is_internal": self.is_internal,
            "nofollow": self.nofollow
        }

class DocumentMetadata:
    def __init__(
        self,
        url: str,
        title: str = "",
        description: str = "",
        keywords: str = "",
        canonical_url: str = "",
        og_image: str = "",
        h1: List[str] = None,
        h2: List[str] = None,
        clean_text: str = "",
        word_count: int = 0,
        content_hash: str = "",
        noindex: bool = False,
        nofollow: bool = False,
        links: List[ExtractedLink] = None
    ):
        self.url = url
        self.title = title
        self.description = description
        self.keywords = keywords
        self.canonical_url = canonical_url or url
        self.og_image = og_image
        self.h1 = h1 or []
        self.h2 = h2 or []
        self.clean_text = clean_text
        self.word_count = word_count
        self.content_hash = content_hash
        self.noindex = noindex
        self.nofollow = nofollow
        self.links = links or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "keywords": self.keywords,
            "canonical_url": self.canonical_url,
            "og_image": self.og_image,
            "h1": self.h1,
            "h2": self.h2,
            "clean_text_preview": self.clean_text[:300] + ("..." if len(self.clean_text) > 300 else ""),
            "word_count": self.word_count,
            "content_hash": self.content_hash,
            "noindex": self.noindex,
            "nofollow": self.nofollow,
            "links_count": len(self.links)
        }

class HTMLParser:
    """Enterprise-grade HTML semantic parser and link extractor."""

    @staticmethod
    def parse(url: str, html: str) -> DocumentMetadata:
        if not html:
            return DocumentMetadata(url=url)

        soup = BeautifulSoup(html, "html.parser")

        # Robots meta directives (e.g. <meta name="robots" content="noindex, nofollow">)
        noindex = False
        nofollow = False
        robots_meta = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if robots_meta and robots_meta.get("content"):
            content = robots_meta["content"].lower()
            if "noindex" in content:
                noindex = True
            if "nofollow" in content:
                nofollow = True

        # Title extraction with fallbacks
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
        if not title:
            h1_first = soup.find("h1")
            if h1_first:
                title = h1_first.get_text().strip()

        # Meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()
        if not description:
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                description = og_desc["content"].strip()

        # Keywords
        keywords = ""
        meta_kw = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
        if meta_kw and meta_kw.get("content"):
            keywords = meta_kw["content"].strip()

        # Canonical Link
        canonical_url = ""
        canonical_tag = soup.find("link", rel=re.compile(r"^canonical$", re.I))
        if canonical_tag and canonical_tag.get("href"):
            canonical_url = normalize_url(canonical_tag["href"], base_url=url)

        # OG Image
        og_image = ""
        og_img_tag = soup.find("meta", property="og:image")
        if og_img_tag and og_img_tag.get("content"):
            og_image = og_img_tag["content"].strip()

        # Headings (H1, H2)
        h1_list = [h.get_text().strip() for h in soup.find_all("h1") if h.get_text().strip()]
        h2_list = [h.get_text().strip() for h in soup.find_all("h2") if h.get_text().strip()]

        # Outgoing link extraction
        base_domain = get_domain(url)
        extracted_links = []
        
        for a_tag in soup.find_all("a", href=True):
            raw_href = a_tag["href"]
            norm_href = normalize_url(raw_href, base_url=url)
            if not norm_href:
                continue

            target_domain = get_domain(norm_href)
            is_internal = (target_domain == base_domain)
            
            # Check link-level rel="nofollow"
            rel_attr = a_tag.get("rel", [])
            if isinstance(rel_attr, str):
                rel_attr = rel_attr.split()
            link_nofollow = nofollow or any("nofollow" in r.lower() for r in rel_attr)

            anchor_text = a_tag.get_text(strip=True)
            extracted_links.append(ExtractedLink(
                target_url=norm_href,
                anchor_text=anchor_text,
                is_internal=is_internal,
                nofollow=link_nofollow
            ))

        # Boilerplate Removal & Clean Text Extraction
        # Strip script, style, noscript, svg, nav, footer, header, form
        for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "iframe", "button"]):
            element.extract()

        raw_text = soup.get_text(separator=" ")
        # Clean multiple spaces and newlines
        clean_text = re.sub(r'\s+', ' ', raw_text).strip()
        words = clean_text.split()
        word_count = len(words)

        # Content hash for duplicate document detection (SimHash / SHA-256)
        content_hash = hashlib.sha256(clean_text.encode('utf-8')).hexdigest()

        return DocumentMetadata(
            url=url,
            title=title or url,
            description=description,
            keywords=keywords,
            canonical_url=canonical_url or url,
            og_image=og_image,
            h1=h1_list,
            h2=h2_list,
            clean_text=clean_text,
            word_count=word_count,
            content_hash=content_hash,
            noindex=noindex,
            nofollow=nofollow,
            links=extracted_links
        )

