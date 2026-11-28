"""
Politemap XML Sitemap Builder & Multi-Service Ping Dispatcher.
Generates standard sitemaps.org XML and pings Ping-O-Matic, FeedBurner, and Bing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
import urllib.parse
import xml.etree.ElementTree as ET
import httpx


def create_sitemap(urls: List[str], output_path: str = "sitemap.xml") -> str:
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    now_iso = datetime.now(timezone.utc).isoformat()
    for url in urls:
        clean = (url or "").strip()
        if not clean:
            continue
        url_elem = ET.SubElement(urlset, "url")
        ET.SubElement(url_elem, "loc").text = clean
        ET.SubElement(url_elem, "lastmod").text = now_iso
        ET.SubElement(url_elem, "changefreq").text = "daily"
        ET.SubElement(url_elem, "priority").text = "1.0"
    tree = ET.ElementTree(urlset)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path


async def ping_all(url: str) -> List[Dict[str, Any]]:
    encoded = urllib.parse.quote(url, safe="")
    base = url.rstrip("/")
    services = [
        ("Ping-O-Matic", f"https://pingomatic.com/ping/?title=Update&blogurl={encoded}"),
        ("FeedBurner", f"https://feedburner.google.com/fb/a/pingSubmit?bloglink={encoded}"),
        ("Bing", f"https://www.bing.com/ping?sitemap={urllib.parse.quote(base + '/sitemap.xml', safe='')}"),
    ]
    results: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for name, svc in services:
            try:
                resp = await client.get(svc)
                results.append({"service": name, "url": svc, "status": resp.status_code})
            except Exception as exc:
                results.append({"service": name, "url": svc, "status": 0, "error": str(exc)})
    return results
