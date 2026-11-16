"""Small dependency-free TF-IDF retriever for page-aware text chunks."""

import math
import re
from collections import Counter

from .ingest import TextChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "what", "when", "where", "which", "who", "will", "with",
}


def _tokens(text: str) -> list[str]:
    return [word for word in _TOKEN_RE.findall(text.lower()) if word not in _STOP_WORDS]


def retrieve_chunks(question: str, chunks: list[TextChunk], top_k: int = 3) -> list[tuple[TextChunk, float]]:
    """Rank chunks by cosine similarity over TF-IDF vectors."""
    if not chunks or top_k < 1:
        return []
    documents = [_tokens(chunk.text) for chunk in chunks]
    query_terms = _tokens(question)
    if not query_terms:
        return []

    document_frequency = Counter(term for terms in documents for term in set(terms))
    total_documents = len(documents)
    idf = {
        term: math.log((total_documents + 1) / (document_frequency.get(term, 0) + 1)) + 1
        for term in set(query_terms).union(document_frequency)
    }
    query_counts = Counter(query_terms)
    query_vector = {term: count * idf[term] for term, count in query_counts.items()}
    query_norm = math.sqrt(sum(weight * weight for weight in query_vector.values()))
    ranked: list[tuple[TextChunk, float]] = []

    for chunk, terms in zip(chunks, documents):
        counts = Counter(terms)
        vector = {term: count * idf[term] for term, count in counts.items()}
        norm = math.sqrt(sum(weight * weight for weight in vector.values()))
        if not norm:
            continue
        dot_product = sum(query_weight * vector.get(term, 0.0) for term, query_weight in query_vector.items())
        score = dot_product / (query_norm * norm)
        if score > 0:
            ranked.append((chunk, score))
    return sorted(ranked, key=lambda item: item[1], reverse=True)[:top_k]
