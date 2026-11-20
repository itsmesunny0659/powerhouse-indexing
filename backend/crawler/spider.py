import asyncio
import time
from typing import List, Set, Dict, Any, Optional, Callable
from urllib.parse import urlparse
from backend.crawler.dedup import normalize_url, get_domain, URLSeenFilter
from backend.crawler.politeness import RobotsManager
from backend.crawler.fetcher import AsyncFetcher, FetchResult
from backend.extractor.parser import HTMLParser, DocumentMetadata
from backend.storage.db import SearchDB
from backend.indexer.inverted_index import Indexer
from backend.indexer.pagerank import PageRankCalculator

class SpiderConfig:
    def __init__(
        self,
        seed_urls: List[str],
        max_pages: int = 50,
        max_depth: int = 2,
        concurrency: int = 3,
        politeness_delay: float = 0.5,
        same_domain_only: bool = True,
        respect_robots: bool = True
    ):
        self.seed_urls = seed_urls
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.politeness_delay = politeness_delay
        self.same_domain_only = same_domain_only
        self.respect_robots = respect_robots

class SpiderStatus:
    def __init__(self):
        self.is_running = False
        self.pages_crawled = 0
        self.pages_indexed = 0
        self.pages_failed = 0
        self.queue_size = 0
        self.current_url = ""
        self.start_time: float = 0.0
        self.elapsed_sec: float = 0.0
        self.recent_logs: List[Dict[str, Any]] = []

    def log(self, level: str, message: str, meta: Dict[str, Any] = None):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message,
            "meta": meta or {}
        }
        self.recent_logs.append(entry)
        if len(self.recent_logs) > 200:
            self.recent_logs.pop(0)

class WebSpider:
    """Enterprise-scale asynchronous web crawler and indexing coordinator."""
    def __init__(self, db: SearchDB, event_broadcaster: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.db = db
        self.indexer = Indexer(db)
        self.pagerank_calc = PageRankCalculator(db)
        self.broadcaster = event_broadcaster
        self.status = SpiderStatus()
        self._stop_event = asyncio.Event()
        self.seen_filter = URLSeenFilter()
        self.robots_mgr = RobotsManager()

    def _broadcast(self, event_type: str, data: Dict[str, Any]):
        if self.broadcaster:
            try:
                self.broadcaster({"type": event_type, "data": data, "timestamp": time.time()})
            except Exception:
                pass

    async def stop(self):
        """Signals the crawler to stop."""
        self._stop_event.set()
        self.status.is_running = False
        self.status.log("WARNING", "Crawler stop requested by user.")
        self._broadcast("crawl_stopped", {"message": "Crawler stopped."})

    async def crawl(self, config: SpiderConfig):
        """Executes full crawl pipeline using async producer-consumer worker queue."""
        if self.status.is_running:
            return

        self._stop_event.clear()
        self.status.is_running = True
        self.status.pages_crawled = 0
        self.status.pages_indexed = 0
        self.status.pages_failed = 0
        self.status.start_time = time.time()
        self.seen_filter.clear()

        # Seed normalization
        queue: asyncio.Queue = asyncio.Queue()
        allowed_domains: Set[str] = set()

        for raw_url in config.seed_urls:
            norm_url = normalize_url(raw_url)
            if norm_url:
                self.seen_filter.add(norm_url)
                await queue.put((norm_url, 0))  # (url, depth)
                allowed_domains.add(get_domain(norm_url))
                self.status.log("INFO", f"Seeded URL: {norm_url}")

        self.status.queue_size = queue.qsize()
        self._broadcast("crawl_started", {"seeds": config.seed_urls, "max_pages": config.max_pages})

        async with AsyncFetcher() as fetcher:
            # Worker task definition
            async def worker(worker_id: int):
                while not self._stop_event.is_set():
                    if self.status.pages_crawled >= config.max_pages:
                        break

                    try:
                        url, depth = await asyncio.wait_for(queue.get(), timeout=2.0)
                    except asyncio.TimeoutError:
                        if queue.empty():
                            break
                        continue

                    domain = get_domain(url)
                    self.status.current_url = url
                    self.status.queue_size = queue.qsize()

                    # Domain scope check
                    if config.same_domain_only and domain not in allowed_domains:
                        queue.task_done()
                        continue

                    # Robots.txt check
                    if config.respect_robots:
                        is_allowed = await self.robots_mgr.is_allowed(url, fetcher.client)
                        if not is_allowed:
                            self.status.log("WARNING", f"[Worker {worker_id}] Blocked by robots.txt: {url}")
                            queue.task_done()
                            continue

                        # Respect politeness delay per domain
                        await self.robots_mgr.wait_for_politeness(domain, config.politeness_delay)

                    # Fetch page
                    self.status.log("INFO", f"[Worker {worker_id}] Fetching (depth {depth}): {url}")
                    fetch_res = await fetcher.fetch(url)

                    if not fetch_res.is_success:
                        self.status.pages_failed += 1
                        self.status.log("ERROR", f"[Worker {worker_id}] Fetch failed ({fetch_res.status_code}): {url} - {fetch_res.error}")
                        queue.task_done()
                        continue

                    self.status.pages_crawled += 1

                    # Parse HTML semantic metadata
                    doc = HTMLParser.parse(fetch_res.final_url, fetch_res.html)

                    # Deduplication via Content Hash
                    duplicate_url = self.db.check_duplicate_content(doc.content_hash, exclude_url=doc.url)
                    if duplicate_url:
                        self.status.log("WARNING", f"Duplicate content detected for {doc.url} (matches {duplicate_url})")

                    if doc.noindex:
                        self.status.log("WARNING", f"Skipping indexing due to noindex directive: {doc.url}")
                    else:
                        # Save to database
                        doc_id = self.db.insert_or_update_document({
                            "url": doc.url,
                            "canonical_url": doc.canonical_url,
                            "title": doc.title,
                            "description": doc.description,
                            "keywords": doc.keywords,
                            "clean_text": doc.clean_text,
                            "word_count": doc.word_count,
                            "content_hash": doc.content_hash,
                            "status_code": fetch_res.status_code
                        })

                        # Save links
                        links_dict = [l.to_dict() for l in doc.links]
                        self.db.save_links(doc.url, links_dict)

                        # Build Inverted Index
                        self.indexer.index_document(doc_id, doc.title, doc.clean_text)
                        self.status.pages_indexed += 1
                        self.status.log("SUCCESS", f"Indexed: '{doc.title[:45]}' ({doc.word_count} words)")

                        self._broadcast("page_indexed", {
                            "doc_id": doc_id,
                            "url": doc.url,
                            "title": doc.title,
                            "word_count": doc.word_count,
                            "elapsed_ms": fetch_res.elapsed_ms
                        })

                    # Queue newly discovered links if within depth limit
                    if depth < config.max_depth and not doc.nofollow:
                        for link in doc.links:
                            target = link.target_url
                            if not target or target in self.seen_filter:
                                continue

                            target_domain = get_domain(target)
                            if config.same_domain_only and target_domain not in allowed_domains:
                                continue

                            self.seen_filter.add(target)
                            await queue.put((target, depth + 1))

                    queue.task_done()

            # Run workers concurrently
            workers = [asyncio.create_task(worker(i + 1)) for i in range(config.concurrency)]
            await asyncio.gather(*workers)

        # Post-crawl: Compute PageRank algorithm
        self.status.log("INFO", "Calculating Google PageRank algorithm for crawled link graph...")
        pr_scores = self.pagerank_calc.calculate_and_save()
        self.status.log("SUCCESS", f"PageRank computed for {len(pr_scores)} documents.")

        self.status.is_running = False
        self.status.elapsed_sec = round(time.time() - self.status.start_time, 2)
        self.status.log("SUCCESS", f"Crawl completed. {self.status.pages_indexed} pages indexed in {self.status.elapsed_sec}s.")

        self._broadcast("crawl_finished", {
            "pages_crawled": self.status.pages_crawled,
            "pages_indexed": self.status.pages_indexed,
            "pages_failed": self.status.pages_failed,
            "elapsed_sec": self.status.elapsed_sec
        })

