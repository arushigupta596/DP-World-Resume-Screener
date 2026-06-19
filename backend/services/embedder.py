"""Resume chunking + embedding via OpenRouter. Stores chunks + 1536-dim
vectors in the `resume_chunks` table (pgvector).

Single API key path: reuses OPENROUTER_API_KEY + OPENROUTER_BASE_URL. The
chosen embedding model must be one that OpenRouter routes (e.g.,
`openai/text-embedding-3-small`).

Demo policy: NO fallbacks. If anything goes wrong (missing key, model
mismatch, API error), exceptions propagate so the recruiter sees an
honest error instead of silent skips.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re

import httpx

from db.supabase import get_client

logger = logging.getLogger("cv-screener.embedder")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIM = 1536

# Character-window chunking. ~1500 chars ≈ ~500 tokens; 200-char overlap
# preserves context across boundaries.
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


_WS_RE = re.compile(r"\s+")


def compute_text_hash(text: str) -> str:
    """Stable SHA-256 of a CV's parsed text. Whitespace-normalized and
    case-folded so two visually-identical CVs that differ only in trailing
    whitespace or capitalization still match."""
    if not text:
        return ""
    normalized = _WS_RE.sub(" ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def copy_chunks(source_candidate_id: str, target_candidate_id: str) -> int:
    """Copy resume_chunks rows from one candidate to another, keeping the
    chunk_text + embedding intact. Returns the number of rows copied.
    Raises if source has 0 chunks (caller should fall through to embedding)."""
    sb = get_client()
    src = (
        sb.table("resume_chunks")
        .select("chunk_index, chunk_text, embedding")
        .eq("candidate_id", source_candidate_id)
        .order("chunk_index")
        .execute()
        .data
        or []
    )
    if not src:
        raise RuntimeError(f"Source candidate {source_candidate_id} has no chunks")

    rows = [
        {
            "candidate_id": target_candidate_id,
            "chunk_index": r["chunk_index"],
            "chunk_text": r["chunk_text"],
            "embedding": r["embedding"],
        }
        for r in src
    ]
    # Wipe any existing chunks for target (e.g., from a partial earlier upload).
    sb.table("resume_chunks").delete().eq("candidate_id", target_candidate_id).execute()
    sb.table("resume_chunks").insert(rows).execute()
    return len(rows)


def chunk_cv_text(text: str) -> list[str]:
    """Sliding-window chunks. Single-chunk passthrough for short CVs."""
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
    """Batched embedding call via OpenRouter's OpenAI-compatible endpoint."""
    if not texts:
        return []

    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set; cannot embed")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": EMBEDDING_MODEL, "input": texts}

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(f"{base_url}/embeddings", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    entries = data.get("data") or []
    if len(entries) != len(texts):
        raise RuntimeError(
            f"Embedding count mismatch: got {len(entries)} for {len(texts)} inputs"
        )
    return [e["embedding"] for e in entries]


def has_embeddings(candidate_id: str) -> bool:
    """Idempotency helper for the backfill script. Not used at scoring time."""
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


def embed_and_store_candidate(candidate_id: str, cv_text: str) -> int:
    """Chunk → embed → bulk-insert. Returns chunk count.
    Raises on any failure (no silent fallback)."""
    chunks = chunk_cv_text(cv_text or "")
    if not chunks:
        raise RuntimeError("No CV text to embed")

    vectors = embed_texts(chunks)

    sb = get_client()
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
