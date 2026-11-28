"""
RSS 2.0 Feed Generator for instant syndication and WebSub discovery.
"""

from datetime import datetime, timezone
from xml.sax.saxutils import escape


def create_rss(title: str, link: str, desc: str, output_path: str = "feed.xml") -> str:
    clean_link = link.rstrip("/")
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{escape(title)}</title>\n"
        f"    <link>{escape(clean_link)}</link>\n"
        f"    <description>{escape(desc)}</description>\n"
        f"    <lastBuildDate>{pub_date}</lastBuildDate>\n"
        "    <item>\n"
        "      <title>Latest Update</title>\n"
        f"      <link>{escape(clean_link)}</link>\n"
        f"      <guid isPermaLink=\"true\">{escape(clean_link)}</guid>\n"
        f"      <pubDate>{pub_date}</pubDate>\n"
        "      <description>Page is now live.</description>\n"
        "    </item>\n"
        "  </channel>\n"
        "</rss>\n"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(feed)
    return output_path
