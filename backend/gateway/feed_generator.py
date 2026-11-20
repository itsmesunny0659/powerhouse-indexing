import time
from typing import List, Dict, Any
from xml.sax.saxutils import escape
from backend.storage.db import SearchDB

class FeedGenerator:
    """
    Generates standard search engine discovery feeds:
    1. XML Sitemap (sitemap.xml) for automated search engine consumption
    2. RSS 2.0 Feed (feed.xml) for Google WebSub real-time hub publishing
    """
    def __init__(self, db: SearchDB, base_url: str = "http://localhost:8000"):
        self.db = db
        self.base_url = base_url

    def generate_sitemap_xml(self) -> str:
        """Generates standard sitemap.xml conformant to sitemaps.org protocol."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url, crawled_at, pagerank_score FROM documents ORDER BY pagerank_score DESC LIMIT 50000")
            rows = cursor.fetchall()

        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

        for r in rows:
            url = escape(r["url"])
            lastmod = (r["crawled_at"] or "").replace(" ", "T") + "Z" if r["crawled_at"] else time.strftime("%Y-%m-%dT%H:%M:%SZ")
            priority = min(1.0, max(0.1, round((r["pagerank_score"] or 1.0) / 2.0, 1)))

            xml.append('  <url>')
            xml.append(f'    <loc>{url}</loc>')
            xml.append(f'    <lastmod>{lastmod}</lastmod>')
            xml.append('    <changefreq>daily</changefreq>')
            xml.append(f'    <priority>{priority:.1f}</priority>')
            xml.append('  </url>')

        xml.append('</urlset>')
        return "\n".join(xml)

    def generate_rss_xml(self) -> str:
        """Generates RSS 2.0 XML feed for instant WebSub (PubSubHubbub) syndication."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url, title, description, crawled_at FROM documents ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()

        pub_date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
        xml.append('  <channel>')
        xml.append('    <title>ApexSearch Live Indexing Stream</title>')
        xml.append(f'    <link>{self.base_url}</link>')
        xml.append('    <description>Real-time stream of high-priority indexed web resources</description>')
        xml.append(f'    <lastBuildDate>{pub_date}</lastBuildDate>')
        xml.append(f'    <atom:link href="{self.base_url}/feed.xml" rel="self" type="application/rss+xml" />')

        for r in rows:
            title = escape(r["title"] or r["url"])
            link = escape(r["url"])
            desc = escape(r["description"] or "Indexed resource")
            xml.append('    <item>')
            xml.append(f'      <title>{title}</title>')
            xml.append(f'      <link>{link}</link>')
            xml.append(f'      <guid isPermaLink="true">{link}</guid>')
            xml.append(f'      <description>{desc}</description>')
            xml.append(f'      <pubDate>{pub_date}</pubDate>')
            xml.append('    </item>')

        xml.append('  </channel>')
        xml.append('</rss>')
        return "\n".join(xml)
