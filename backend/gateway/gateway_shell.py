"""
High-DA Reverse Proxy & Gateway Shell Engine
Generates authoritative gateway wrapper pages (/i/{url_id}) injecting
Schema.org JobPosting JSON-LD + Canonical pointing to target URL.
This trick allows any arbitrary URL to leverage the Google Indexing API
with instant crawl prioritization.
"""

import base64
import json
import logging
import re
import urllib.parse
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class GatewayShellEngine:
    def __init__(self):
        self.gateway_cache: Dict[str, str] = {}

    def encode_url_id(self, url: str) -> str:
        """Encodes URL to base64 safe ID."""
        encoded = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        return f"u_{encoded}"

    def decode_url_id(self, url_id: str) -> Optional[str]:
        """Decodes URL ID back to target URL."""
        if not url_id.startswith("u_"):
            return None
        raw_b64 = url_id[2:]
        # Fix padding
        padding = 4 - (len(raw_b64) % 4)
        if padding and padding != 4:
            raw_b64 += "=" * padding
        try:
            return base64.urlsafe_b64decode(raw_b64.encode()).decode()
        except Exception:
            return None

    def extract_keywords(self, url: str) -> str:
        """Extracts readable keyword from target URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.strip("/")
            if path:
                slugs = [s for s in path.split("/") if s]
                last_slug = slugs[-1]
                cleaned = re.sub(r"^\d+[\-_]?", "", last_slug)
                cleaned = re.sub(r"\.(html|php|aspx|jsp)$", "", cleaned)
                words = re.sub(r"[\-_+]+", " ", cleaned).strip()
                if len(words) >= 3:
                    return words
            domain = parsed.netloc.split(":")[0]
            domain_parts = domain.split(".")
            if len(domain_parts) >= 2:
                name = domain_parts[-2] if domain_parts[-1] in ("com", "net", "org", "app", "io") else domain_parts[0]
                return name.replace("-", " ")
        except Exception:
            pass
        return "Official Resource"

    def generate_html_shell(self, target_url: str, title: Optional[str] = None, description: Optional[str] = None) -> str:
        """
        Creates competitor-grade high-CTR Schema.org JobPosting exploit wrapper with canonical link.
        """
        keyword = self.extract_keywords(target_url)
        page_title = title or f"GUIA Official ⛵ 🐳 {keyword} 🔋 🧲 !"
        page_desc = description or f"20 seconds ago — Portal oficial e acesso verificado de {keyword} é ☎️ | ◢▼ Acesso Oficial Online ◢▼. Acesso prioritário com suporte imediato e downloads diretos."

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
    <link rel="canonical" href="{target_url}">
    <meta http-equiv="refresh" content="2;url={target_url}">
    <meta name="description" content="{page_desc}">

    <!-- SCHEMA.ORG JOBPOSTING / PRIORITY CRAWL INJECTION -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "JobPosting",
      "title": "{page_title}",
      "description": "{page_desc}",
      "datePosted": "2026-11-23T00:00:00Z",
      "validThrough": "2027-11-23T00:00:00Z",
      "employmentType": "FULL_TIME",
      "hiringOrganization": {{
        "@type": "Organization",
        "name": "Apex Fast Indexing Authority Network",
        "sameAs": "https://www.google.com"
      }},
      "jobLocation": {{
        "@type": "Place",
        "address": {{
          "@type": "PostalAddress",
          "addressLocality": "Global",
          "addressCountry": "US"
        }}
      }}
    }}
    </script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 40px; display: flex; justify-content: center; align-items: center; min-height: 80vh; }}
        .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 32px; max-width: 600px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ font-size: 20px; color: #60a5fa; margin-top: 0; }}
        p {{ color: #9ca3af; font-size: 14px; line-height: 1.6; }}
        .snippet-box {{ background: #1f2937; border-left: 4px solid #38bdf8; padding: 12px 16px; margin: 16px 0; border-radius: 4px; font-size: 13px; color: #e5e7eb; }}
        .btn {{ display: inline-block; background: #2563eb; color: #fff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 16px; }}
        .meta {{ font-size: 12px; color: #6b7280; margin-top: 24px; border-top: 1px solid #1f2937; padding-top: 12px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>{page_title}</h1>
        <div class="snippet-box">
            {page_desc}
        </div>
        <p>This high-authority gateway node has registered an official priority crawl request with Googlebot for the verified destination below.</p>
        <p><strong>Canonical Target:</strong><br><a href="{target_url}" style="color: #38bdf8; word-break: break-all;">{target_url}</a></p>
        <a href="{target_url}" class="btn">Proceed to Destination &rarr;</a>
        <div class="meta">
            ApexSearch Engine &bull; Schema.org Verified Canonical &bull; Google Indexing API Enabled
        </div>
    </div>
</body>
</html>"""
        return html

gateway_shell = GatewayShellEngine()
