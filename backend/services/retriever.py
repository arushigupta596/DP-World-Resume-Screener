"""Hybrid retrieval against resume_chunks (pgvector + Postgres FTS,
fused with Reciprocal Rank Fusion in the SQL function)."""
from __future__ import annotations

import logging

from db.supabase import get_client
from services.embedder import embed_texts

logger = logging.getLogger("cv-screener.retriever")


def embed_query(query: str) -> list[float]:
    vectors = embed_texts([query])
    return vectors[0] if vectors else []


def retrieve_chunks_for_candidate(
    candidate_id: str, query: str, k: int = 3
) -> list[dict]:
    """Top-k chunks from this candidate that match the query.
    Returns [{chunk_text, rrf_score}, ...] ordered desc by rrf."""
    if not query:
        return []
    sb = get_client()
    embedding = embed_query(query)
    try:
        resp = sb.rpc(
            "hybrid_search_chunks",
            {
                "p_candidate_id": candidate_id,
                "p_query_text": query,
                "p_query_embedding": embedding,
                "p_k": k,
            },
        ).execute()
    except Exception as e:
        logger.warning("hybrid_search_chunks RPC failed: %s", e)
        return []
    return [
        {"chunk_text": r.get("chunk_text", ""), "rrf_score": r.get("rrf_score", 0)}
        for r in (resp.data or [])
        if r.get("chunk_text")
    ]


def search_role(role_id: str, query: str, limit: int = 20) -> list[dict]:
    """Cross-candidate hybrid search across all CVs in a role.
    Returns [{candidate_id, best_chunk, rrf_score}, ...]."""
    if not query:
        return []
    sb = get_client()
    embedding = embed_query(query)
    try:
        resp = sb.rpc(
            "hybrid_search_role",
            {
                "p_role_id": role_id,
                "p_query_text": query,
                "p_query_embedding": embedding,
                "p_limit": limit,
            },
        ).execute()
    except Exception as e:
        logger.warning("hybrid_search_role RPC failed: %s", e)
        return []
    return [
        {
            "candidate_id": r.get("candidate_id"),
            "best_chunk": r.get("best_chunk", ""),
            "rrf_score": r.get("rrf_score", 0),
        }
        for r in (resp.data or [])
        if r.get("candidate_id")
    ]
