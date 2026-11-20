import re
from urllib.parse import urlparse, urlunparse, urljoin, parse_qsl, urlencode

TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'gclid', 'fbclid', 'msclkid', 'mc_cid', 'mc_eid', 'ref', 'source'
}

def normalize_url(raw_url: str, base_url: str = "") -> str:
    """
    Normalizes a URL to a canonical format:
    1. Resolves relative URLs against base_url
    2. Lowercases scheme and netloc
    3. Strips default ports (:80, :443)
    4. Removes fragment identifiers (#hash)
    5. Strips common analytics tracking query params (utm_*, fbclid, etc.)
    6. Sorts remaining query parameters
    7. Standardizes trailing slashes
    """
    if not raw_url:
        return ""
    
    raw_url = raw_url.strip()
    
    # Resolve relative URL if base_url is provided
    if base_url:
        try:
            raw_url = urljoin(base_url, raw_url)
        except Exception:
            return ""

    try:
        parsed = urlparse(raw_url)
    except Exception:
        return ""

    # Only process http and https schemes
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        return ""

    netloc = parsed.netloc.lower()
    if not netloc:
        return ""

    # Strip default ports
    if netloc.endswith(':80') and scheme == 'http':
        netloc = netloc[:-3]
    elif netloc.endswith(':443') and scheme == 'https':
        netloc = netloc[:-4]

    # Clean path: normalize double slashes, handle empty path
    path = parsed.path or "/"
    path = re.sub(r'/{2,}', '/', path)

    # Filter and sort query parameters
    query_params = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            k_lower = k.lower()
            if k_lower not in TRACKING_PARAMS:
                query_params.append((k, v))
        query_params.sort(key=lambda x: x[0])
    
    normalized_query = urlencode(query_params) if query_params else ""

    # Strip fragments completely (#target)
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        "",
        normalized_query,
        ""
    ))

    return normalized

def get_domain(url: str) -> str:
    """Extracts base domain (netloc) from normalized URL."""
    try:
        return urlparse(url).netloc
    except Exception:
        return ""

class URLSeenFilter:
    """In-memory deduplication filter with exact match and fast lookup."""
    def __init__(self):
        self._seen = set()

    def add(self, url: str) -> bool:
        """Returns True if URL is newly added, False if already seen."""
        norm = normalize_url(url)
        if not norm or norm in self._seen:
            return False
        self._seen.add(norm)
        return True

    def __contains__(self, url: str) -> bool:
        return normalize_url(url) in self._seen

    def __len__(self) -> int:
        return len(self._seen)

    def clear(self):
        self._seen.clear()

