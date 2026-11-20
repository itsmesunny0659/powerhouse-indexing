import re
from typing import List, Tuple, Dict, Set, Any

# Standard English stop words curated for search engine precision
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", 
    "by", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", 
    "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", 
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", 
    "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", 
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", 
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", 
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", 
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", 
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

TOKEN_PATTERN = re.compile(r'\b[a-zA-Z0-9_\-\']{2,}\b')

class Tokenizer:
    @staticmethod
    def tokenize(text: str, remove_stopwords: bool = True) -> List[str]:
        """Simple tokenization returning list of tokens."""
        if not text:
            return []
        tokens = TOKEN_PATTERN.findall(text.lower())
        if remove_stopwords:
            return [t for t in tokens if t not in STOP_WORDS]
        return tokens

    @staticmethod
    def tokenize_with_positions(text: str, remove_stopwords: bool = True) -> List[Tuple[str, int]]:
        """
        Tokenizes text while tracking positional offsets in the document.
        Returns list of (term, position_index).
        """
        if not text:
            return []
        tokens_with_pos = []
        for match in TOKEN_PATTERN.finditer(text.lower()):
            token = match.group()
            pos = match.start()
            if remove_stopwords and token in STOP_WORDS:
                continue
            tokens_with_pos.append((token, pos))
        return tokens_with_pos

    @staticmethod
    def get_term_frequencies(tokens_with_pos: List[Tuple[str, int]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregates positional tokens into:
        term -> { "tf": frequency_count, "positions": [pos1, pos2, ...] }
        """
        result = {}
        for term, pos in tokens_with_pos:
            if term not in result:
                result[term] = {"tf": 0, "positions": []}
            result[term]["tf"] += 1
            result[term]["positions"].append(pos)
        return result
