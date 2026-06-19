"""Hybrid retrieval against resume_chunks (pgvector + Postgres FTS,
fused with Reciprocal Rank Fusion in the SQL function).

Demo policy: no fallbacks. Errors propagate.
"""
from __future__ import annotations

from db.supabase import get_client
from services.embedder import embed_texts


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]


def retrieve_chunks_for_candidate(
    candidate_id: str,
    query: str,
    k: int = 3,
    query_embedding: list[float] | None = None,
) -> list[dict]:
    """Top-k chunks from one candidate matching the query.
    Pass a pre-computed query_embedding to skip the OpenRouter round-trip
    (useful when the same query is reused across many candidates)."""
    if not query:
        return []
    embedding = query_embedding if query_embedding is not None else embed_query(query)
    sb = get_client()
    resp = sb.rpc(
        "hybrid_search_chunks",
        {
            "p_candidate_id": candidate_id,
            "p_query_text": query,
            "p_query_embedding": embedding,
            "p_k": k,
        },
    ).execute()
    return [
        {"chunk_text": r.get("chunk_text", ""), "rrf_score": r.get("rrf_score", 0)}
        for r in (resp.data or [])
        if r.get("chunk_text")
    ]


def search_role(role_id: str, query: str, limit: int = 20) -> list[dict]:
    """Cross-candidate hybrid search across all CVs in a role."""
    if not query:
        return []
    embedding = embed_query(query)
    sb = get_client()
    resp = sb.rpc(
        "hybrid_search_role",
        {
            "p_role_id": role_id,
            "p_query_text": query,
            "p_query_embedding": embedding,
            "p_limit": limit,
        },
    ).execute()
    return [
        {
            "candidate_id": r.get("candidate_id"),
            "best_chunk": r.get("best_chunk", ""),
            "rrf_score": r.get("rrf_score", 0),
        }
        for r in (resp.data or [])
        if r.get("candidate_id")
    ]
