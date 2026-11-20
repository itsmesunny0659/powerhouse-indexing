import json
from typing import Dict, Any, List
from backend.storage.db import SearchDB
from backend.indexer.tokenizer import Tokenizer

class Indexer:
    """Manages document tokenization and SQLite inverted index building."""
    def __init__(self, db: SearchDB):
        self.db = db

    def index_document(self, doc_id: int, title: str, text: str):
        """
        Parses document text & title, generates positional postings,
        and updates the inverted index and vocabulary tables.
        """
        # Combine title (given extra weighting through repetition or explicit terms) and body
        combined_text = f"{title} {title} {text}"
        tokens_with_pos = Tokenizer.tokenize_with_positions(combined_text, remove_stopwords=True)
        tf_map = Tokenizer.get_term_frequencies(tokens_with_pos)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # First, check if doc_id was previously indexed; decrement terms doc_freq
            cursor.execute("SELECT term FROM inverted_index WHERE doc_id = ?", (doc_id,))
            old_terms = [r["term"] for r in cursor.fetchall()]
            if old_terms:
                cursor.execute("DELETE FROM inverted_index WHERE doc_id = ?", (doc_id,))
                for ot in old_terms:
                    cursor.execute("UPDATE terms SET doc_freq = MAX(0, doc_freq - 1) WHERE term = ?", (ot,))

            # Batch insert new postings
            postings = []
            for term, data in tf_map.items():
                postings.append((
                    term,
                    doc_id,
                    data["tf"],
                    json.dumps(data["positions"][:50])  # store up to 50 sample positions
                ))

            cursor.executemany("""
                INSERT OR REPLACE INTO inverted_index (term, doc_id, term_frequency, positions)
                VALUES (?, ?, ?, ?)
            """, postings)

            # Update vocabulary terms doc_freq
            for term in tf_map.keys():
                cursor.execute("""
                    INSERT INTO terms (term, doc_freq)
                    VALUES (?, 1)
                    ON CONFLICT(term) DO UPDATE SET doc_freq = doc_freq + 1
                """, (term,))

            conn.commit()

    def get_postings_for_terms(self, terms: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves postings for a list of terms:
        { term: [ { "doc_id": 1, "tf": 3, "positions": [...] }, ... ] }
        """
        if not terms:
            return {}

        result = {t: [] for t in terms}
        placeholders = ",".join(["?"] * len(terms))

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = f"""
                SELECT term, doc_id, term_frequency, positions
                FROM inverted_index
                WHERE term IN ({placeholders})
            """
            cursor.execute(query, terms)
            for row in cursor.fetchall():
                t = row["term"]
                result[t].append({
                    "doc_id": row["doc_id"],
                    "tf": row["term_frequency"],
                    "positions": json.loads(row["positions"]) if row["positions"] else []
                })

        return result

