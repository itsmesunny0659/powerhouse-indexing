# ApexSearch: High-Tech Web Crawler & Google-Grade Indexing Engine

ApexSearch is an enterprise-grade search engine pipeline built with modern asynchronous Python, SQLite WAL storage, Okapi BM25 scoring, and the mathematical PageRank algorithm.

---

## 🏗️ Architecture & Pipeline Overview

```
[ Frontend: Apex UI ]
       │ (WebSocket & REST API)
       ▼
[ FastAPI Server ] ◄────────────────────────────────────────┐
       │                                                    │
       ▼                                                    │
[ Spider Lab (Coordinator) ]                                │
  ├── Robots.txt & Politeness Engine                        │
  ├── URL Normalizer & Bloom Filter (Deduplication)         │
  └── Async Worker Pool (httpx connection pooling)          │
       │                                                    │
       ▼                                                    │
[ HTML Semantic Parser & Extractor ]                        │
  ├── Metadata (Title, Description, Canonical, OG tags)     │
  ├── Link Graph Extractor (Internal/External, Anchor text) │
  └── Content Hashing (SHA256 duplicate detection)          │
       │                                                    │
       ▼                                                    │
[ Indexing Core ]                                           │
  ├── Positional Tokenizer & Stopword Engine                │
  ├── Inverted Index (Term Frequency & Posting lists)       │
  └── Google PageRank Calculator (Power Iteration on Graph) │
       │                                                    │
       ▼                                                    │
[ Search & Ranking Engine ] ────────────────────────────────┘
  ├── Okapi BM25 (Probabilistic Relevance)
  ├── PageRank Multiplier & Title Boost
  └── Context Snippet Highlighter
```

---

## ⚡ Core Components

1. **Crawler & Robots Engine (`backend/crawler/`):**
   - **`politeness.py`**: Automated `robots.txt` discovery, parsing, and caching with configurable crawl-delay enforcement per domain.
   - **`dedup.py`**: URL normalization (stripping tracking parameters, canonicalizing scheme/port/path) and fast in-memory hash set.
   - **`fetcher.py`**: Asynchronous HTTP client using `httpx` with connection pooling, SSL resilience, and content-type filtering.
   - **`spider.py`**: Concurrent worker pool using `asyncio.Queue` supporting depth-limited BFS crawling.

2. **Semantic Extraction (`backend/extractor/`):**
   - **`parser.py`**: Strips scripts, styles, and navigation boilerplate. Extracts clean body text, H1/H2 headings, canonical URLs, and outbound hyperlinks with their associated anchor text.

3. **Google-Grade Indexing & Ranking (`backend/indexer/`):**
   - **`inverted_index.py`**: High-performance SQLite inverted index with term frequency (TF) and positional offsets.
   - **`pagerank.py`**: Power-iteration algorithm solving the Google PageRank equation with damping factor $\alpha = 0.85$ and dangling-node handling.
   - **`ranking.py`**: Multi-signal ranker blending Okapi BM25, title match signals, anchor text, and PageRank authority.

4. **Interactive Dashboard (`frontend/`):**
   - Google-style search engine with dynamic latency telemetry and `<mark>` highlighted snippets.
   - Live Spider Lab with active workers, real-time log terminal, and dials.
   - Interactive HTML5 Canvas directed link graph visualizer.
   - Full document inspection modal.

---

## 🚀 Getting Started

### 1. Run the Server
```powershell
python run.py
```

### 2. Access the Application
- **Interactive UI Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

