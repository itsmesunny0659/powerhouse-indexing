"""
JSON-LD Structured Data Builder (NewsArticle & JobPosting schemas).
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional


def build_schema_payloads(
    url: str,
    headline: str = "Breaking: Verified Page Update",
    image_url: Optional[str] = None,
    job_title: str = "SEO Specialist",
) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    news_schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "mainEntityOfPage": url,
        "headline": headline,
        "datePublished": now_iso,
        "dateModified": now_iso,
        "image": [image_url] if image_url else [],
        "author": {"@type": "Organization", "name": "Global News Network"},
        "publisher": {"@type": "Organization", "name": "Apex Global Breaking News"},
    }
    job_schema = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": job_title,
        "datePosted": now_iso,
        "hiringOrganization": {"@type": "Organization", "name": "Google Verified Inc."},
        "jobLocation": {"@type": "Place", "address": "Mountain View, CA"},
    }
    return {"news_article": news_schema, "job_posting": job_schema}


def inject_trust(url: str, headline: str = "Breaking: Verified Page Update") -> str:
    payloads = build_schema_payloads(url, headline=headline)
    news_tag = f'<script type="application/ld+json">\n{json.dumps(payloads["news_article"], indent=2)}\n</script>'
    job_tag = f'<script type="application/ld+json">\n{json.dumps(payloads["job_posting"], indent=2)}\n</script>'
    return f"{news_tag}\n{job_tag}"
