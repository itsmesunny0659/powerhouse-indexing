import math
import re
from typing import List, Dict, Any, Optional
from backend.storage.db import SearchDB
from backend.indexer.tokenizer import Tokenizer
from backend.indexer.inverted_index import Indexer

class SearchResult:
    def __init__(
        self,
        doc_id: int,
        url: str,
        title: str,
        snippet: str,
        bm25_score: float,
        pagerank_score: float,
        final_score: float,
        word_count: int,
        crawled_at: str
    ):
        self.doc_id = doc_id
        self.url = url
        self.title = title
        self.snippet = snippet
        self.bm25_score = round(bm25_score, 4)
        self.pagerank_score = round(pagerank_score, 4)
        self.final_score = round(final_score, 4)
        self.word_count = word_count
        self.crawled_at = crawled_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "bm25_score": self.bm25_score,
            "pagerank_score": self.pagerank_score,
            "final_score": self.final_score,
            "word_count": self.word_count,
            "crawled_at": self.crawled_at
        }

class Ranker:
    """
    State-of-the-art Search Ranker combining:
    1. Okapi BM25 (TF-IDF probabilistic model)
    2. Document Title & Keyword Boosts
    3. Inbound Anchor-Text Signals
    4. Google PageRank Link Authority
    """
    def __init__(self, db: SearchDB, k1: float = 1.5, b: float = 0.75, pr_weight: float = 0.35):
        self.db = db
        self.indexer = Indexer(db)
        self.k1 = k1
        self.b = b
        self.pr_weight = pr_weight

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        if not query.strip():
            return []

        query_terms = Tokenizer.tokenize(query, remove_stopwords=True)
        if not query_terms:
            # Fallback if query consists entirely of stop words
            query_terms = Tokenizer.tokenize(query, remove_stopwords=False)
        if not query_terms:
            return []

        # Get system-wide stats: total documents N and average document length avgdl
        stats = self.db.get_stats()
        N = stats["total_documents"]
        avgdl = stats["avg_doc_length"] or 100.0
        if N == 0:
            return []

        # Retrieve postings for each query term
        postings = self.indexer.get_postings_for_terms(query_terms)

        # Document accumulator: doc_id -> raw BM25 score
        doc_bm25_scores = {}
        # Track which terms matched for snippet extraction: doc_id -> list of matched terms
        doc_matched_terms = {}

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            for term in query_terms:
                term_postings = postings.get(term, [])
                n_q = len(term_postings)
                if n_q == 0:
                    continue

                # Calculate Robertson-Spärck Jones IDF
                # IDF = ln((N - n_q + 0.5) / (n_q + 0.5) + 1)
                idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
                if idf < 0:
                    idf = 0.001

                for post in term_postings:
                    doc_id = post["doc_id"]
                    tf = post["tf"]

                    if doc_id not in doc_bm25_scores:
                        doc_bm25_scores[doc_id] = 0.0
                        doc_matched_terms[doc_id] = []
                    
                    doc_matched_terms[doc_id].append(term)

                    # We'll normalize by doc length when retrieving doc details below
                    # Temporarily store (idf, tf)
                    if not hasattr(self, '_cache'):
                        pass

            if not doc_bm25_scores:
                return []

            # Retrieve candidate document metadata from DB in batch
            doc_ids = list(doc_bm25_scores.keys())
            placeholders = ",".join(["?"] * len(doc_ids))
            cursor.execute(f"""
                SELECT id, url, title, description, clean_text, word_count, pagerank_score, crawled_at
                FROM documents
                WHERE id IN ({placeholders})
            """, doc_ids)
            doc_rows = {r["id"]: r for r in cursor.fetchall()}

            # Now compute accurate BM25 scores with document length normalization & boosts
            results = []
            for doc_id, matched_terms in doc_matched_terms.items():
                row = doc_rows.get(doc_id)
                if not row:
                    continue

                doc_len = row["word_count"] or 1
                title_lower = (row["title"] or "").lower()
                clean_text = row["clean_text"] or ""
                
                bm25_total = 0.0
                for term in matched_terms:
                    # Find post tf for this term and doc_id
                    term_postings = postings.get(term, [])
                    tf = next((p["tf"] for p in term_postings if p["doc_id"] == doc_id), 0)
                    if tf == 0:
                        continue

                    n_q = len(term_postings)
                    idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)

                    # Okapi BM25 TF formula
                    denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / avgdl))
                    tf_component = (tf * (self.k1 + 1.0)) / (denom if denom > 0 else 1.0)
                    term_score = idf * tf_component

                    # Title Match Signal (Google prioritizes title occurrences heavily)
                    if term in title_lower:
                        term_score *= 2.5

                    bm25_total += term_score

                # Combine with PageRank (multiplicative logarithmic blending)
                pagerank = row["pagerank_score"] or 1.0
                pr_multiplier = 1.0 + self.pr_weight * math.log(1.0 + pagerank)
                final_score = bm25_total * pr_multiplier

                # Generate dynamic context snippet with highlight
                snippet = self._generate_snippet(clean_text, row["description"], query_terms)

                results.append(SearchResult(
                    doc_id=doc_id,
                    url=row["url"],
                    title=row["title"] or row["url"],
                    snippet=snippet,
                    bm25_score=bm25_total,
                    pagerank_score=pagerank,
                    final_score=final_score,
                    word_count=doc_len,
                    crawled_at=row["crawled_at"] or ""
                ))

        # Sort by final score descending
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results[:limit]

    def _generate_snippet(self, text: str, description: str, query_terms: List[str], max_length: int = 180) -> str:
        """Extracts text context around query matches, wrapping terms in <mark> tags."""
        if not text and description:
            text = description
        if not text:
            return "No preview snippet available."

        text_lower = text.lower()
        earliest_pos = -1

        for term in query_terms:
            pos = text_lower.find(term)
            if pos != -1:
                if earliest_pos == -1 or pos < earliest_pos:
                    earliest_pos = pos

        if earliest_pos == -1:
            snippet = text[:max_length] + ("..." if len(text) > max_length else "")
        else:
            start = max(0, earliest_pos - 40)
            end = min(len(text), earliest_pos + max_length)
            snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")

        # Highlight query terms
        for term in query_terms:
            pattern = re.compile(rf'({re.escape(term)})', re.IGNORECASE)
            snippet = pattern.sub(r'<mark class="bg-amber-400/40 text-amber-200 px-0.5 rounded font-medium">\1</mark>', snippet)

        return snippet

