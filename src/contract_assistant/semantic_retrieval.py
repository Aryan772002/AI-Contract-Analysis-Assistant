"""Dense embedding retrieval backed by FAISS when its optional packages exist."""

from __future__ import annotations

from .ingest import TextChunk
from .retrieval import retrieve_chunks

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def retrieve_semantic_chunks(
    question: str, chunks: list[TextChunk], top_k: int = 3
) -> tuple[list[tuple[TextChunk, float]], str]:
    """Embed the question and chunks, then rank with a cosine FAISS index.

    The compact baseline remains available when optional native dependencies
    are not installed (including unsupported Python/platform combinations).
    """
    if not chunks or top_k < 1:
        return [], "faiss"

    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return retrieve_chunks(question, chunks, top_k), "tfidf-fallback"

    model = SentenceTransformer(EMBEDDING_MODEL, device="cpu")
    texts = [chunk.text for chunk in chunks]
    vectors = model.encode(
        texts + [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype("float32")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(np.ascontiguousarray(vectors[:-1]))
    scores, indices = index.search(np.ascontiguousarray(vectors[-1:]), min(top_k, len(chunks)))
    matches = [
        (chunks[int(position)], float(score))
        for score, position in zip(scores[0], indices[0])
        if position >= 0
    ]
    return matches, "faiss"
