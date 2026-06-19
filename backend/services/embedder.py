"""Resume chunking + embedding service. Stores chunks + 1536-dim vectors in
the `resume_chunks` table (pgvector).

Embedding provider: OpenAI text-embedding-3-small. If OPENAI_API_KEY is not
set, embedding calls raise so the caller can fall back gracefully.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

from openai import OpenAI

from db.supabase import get_client

logger = logging.getLogger("cv-screener.embedder")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536

# Character-window chunking. ~1500 chars ≈ ~500 tokens; 200-char overlap
# preserves context across boundaries.
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

_client: OpenAI | None = None


def _get_openai() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set; cannot embed")
        _client = OpenAI(api_key=api_key)
    return _client


def chunk_cv_text(text: str) -> list[str]:
    """Sliding window chunks. Handles short CVs (returns single chunk).

    Splits on character count rather than token count for simplicity — the
    overlap window catches sentence boundaries near the seams.
    """
    if not text:
        return []
    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Single batched call to the embeddings API."""
    if not texts:
        return []
    client = _get_openai()
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    # API guarantees ordering matches input order.
    return [d.embedding for d in resp.data]


def embed_and_store_candidate(candidate_id: str, cv_text: str) -> int:
    """Chunk a candidate's CV, embed all chunks in one API call, bulk-insert
    rows into resume_chunks. Returns the number of chunks stored.

    No-op (returns 0) when cv_text is empty.
    """
    chunks = chunk_cv_text(cv_text or "")
    if not chunks:
        return 0

    vectors = embed_texts(chunks)
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding count mismatch")

    sb = get_client()
    # Delete any prior chunks for this candidate so re-uploads are clean.
    sb.table("resume_chunks").delete().eq("candidate_id", candidate_id).execute()

    rows = [
        {
            "candidate_id": candidate_id,
            "chunk_index": idx,
            "chunk_text": text,
            "embedding": vec,
        }
        for idx, (text, vec) in enumerate(zip(chunks, vectors))
    ]
    sb.table("resume_chunks").insert(rows).execute()
    logger.info("Embedded %d chunks for candidate %s", len(rows), candidate_id)
    return len(rows)


def has_embeddings(candidate_id: str) -> bool:
    sb = get_client()
    resp = (
        sb.table("resume_chunks")
        .select("id", count="exact")
        .eq("candidate_id", candidate_id)
        .limit(1)
        .execute()
    )
    count = resp.count or len(resp.data or [])
    return count > 0
