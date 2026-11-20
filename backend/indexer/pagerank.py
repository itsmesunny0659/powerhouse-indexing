from typing import Dict, List, Tuple, Any
from collections import defaultdict
from backend.storage.db import SearchDB

class PageRankCalculator:
    """
    Computes classic Google PageRank using power-iteration on the crawled web graph.
    Properly handles dangling nodes (sinks) and convergence epsilon.
    """
    def __init__(self, db: SearchDB, damping: float = 0.85, max_iter: int = 100, tol: float = 1e-6):
        self.db = db
        self.damping = damping
        self.max_iter = max_iter
        self.tol = tol

    def calculate_and_save(self) -> Dict[str, float]:
        """Calculates PageRank for all indexed documents and updates DB."""
        doc_urls = self.db.get_all_document_urls()
        if not doc_urls:
            return {}

        N = len(doc_urls)
        doc_set = set(doc_urls)
        
        # Build adjacency and in-link lists
        # Only count links between known indexed documents (closed graph)
        # Exclude rel="nofollow" links
        out_links = defaultdict(set)
        in_links = defaultdict(set)

        raw_links = self.db.get_all_links_for_graph()
        for src, dst, nofollow in raw_links:
            if nofollow:
                continue
            if src in doc_set and dst in doc_set and src != dst:
                out_links[src].add(dst)
                in_links[dst].add(src)

        # Initial uniform distribution: PR_0 = 1 / N
        scores = {url: 1.0 / N for url in doc_urls}

        # Power Iteration
        for iteration in range(self.max_iter):
            new_scores = {}
            # Sum of ranks from dangling nodes (nodes with 0 outbound links)
            dangling_sum = sum(scores[url] for url in doc_urls if len(out_links[url]) == 0)

            diff = 0.0
            for url in doc_urls:
                # Standard random teleportation + dangling redistribution
                rank = (1.0 - self.damping) / N + (self.damping * dangling_sum / N)
                
                # Inbound link contributions
                for inbound in in_links[url]:
                    out_degree = len(out_links[inbound])
                    if out_degree > 0:
                        rank += self.damping * (scores[inbound] / out_degree)

                diff += abs(rank - scores[url])
                new_scores[url] = rank

            scores = new_scores
            if diff < self.tol:
                break

        # Normalize so average score is 1.0 (for easy human interpretability)
        avg_score = sum(scores.values()) / N if N > 0 else 1.0
        normalized_scores = {url: round(score / avg_score, 4) for url, score in scores.items()}

        # Save to database
        self.db.update_pagerank_scores(normalized_scores)
        return normalized_scores

    def get_graph_data(self) -> Dict[str, Any]:
        """Exports nodes and edges formatted for visualization charts."""
        doc_urls = self.db.get_all_document_urls()
        doc_set = set(doc_urls)
        raw_links = self.db.get_all_links_for_graph()

        nodes = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url, title, pagerank_score FROM documents")
            for r in cursor.fetchall():
                nodes.append({
                    "id": r["url"],
                    "label": r["title"] or r["url"],
                    "pagerank": r["pagerank_score"]
                })

        edges = []
        for src, dst, nofollow in raw_links:
            if src in doc_set and dst in doc_set:
                edges.append({
                    "source": src,
                    "target": dst,
                    "nofollow": bool(nofollow)
                })

        return {"nodes": nodes, "edges": edges}
