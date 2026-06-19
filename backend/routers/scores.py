from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from db.supabase import get_client
from services.exporter import generate_excel
from services.scorer import score_candidate

router = APIRouter(tags=["scores"])


@router.post("/roles/{role_id}/score")
async def list_pending_candidates(role_id: str):
    """Return the ids of candidates that still need scoring.

    Frontend drives the scoring loop on Vercel (one fetch per candidate to
    keep each request inside the function timeout).
    """
    sb = get_client()
    role_resp = sb.table("roles").select("id").eq("id", role_id).single().execute()
    if not role_resp.data:
        raise HTTPException(404, "Role not found")

    cands = (
        sb.table("candidates")
        .select("id, status")
        .eq("role_id", role_id)
        .in_("status", ["pending", "error"])
        .execute()
        .data
        or []
    )
    return {"pending": [c["id"] for c in cands if c.get("id")]}


@router.post("/candidates/{candidate_id}/score")
async def score_one(candidate_id: str):
    """Score a single candidate synchronously. Each call is one LLM round-trip
    (~6-15s typical) plus the Supabase write. Fits well inside Vercel's 60s
    Hobby-tier function timeout.
    """
    sb = get_client()
    cand = sb.table("candidates").select("role_id").eq("id", candidate_id).single().execute()
    if not cand.data:
        raise HTTPException(404, "Candidate not found")
    role_resp = sb.table("roles").select("*").eq("id", cand.data["role_id"]).single().execute()
    if not role_resp.data:
        raise HTTPException(500, "Candidate's role missing")

    await score_candidate(candidate_id, role_resp.data)

    score_resp = (
        sb.table("scores")
        .select("*")
        .eq("candidate_id", candidate_id)
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )
    cand_resp = sb.table("candidates").select("status, error_msg, name").eq("id", candidate_id).single().execute()
    return {"candidate": cand_resp.data, "score": score_resp.data[0] if score_resp.data else None}


@router.get("/roles/{role_id}/score/status")
async def scoring_status(role_id: str):
    sb = get_client()
    rows = (
        sb.table("candidates").select("status").eq("role_id", role_id).execute().data or []
    )
    counts = {"total": len(rows), "pending": 0, "scoring": 0, "scored": 0, "error": 0}
    for r in rows:
        s = r.get("status") or "pending"
        if s in counts:
            counts[s] += 1
    return counts


@router.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str):
    sb = get_client()
    cand = sb.table("candidates").select("*").eq("id", candidate_id).single().execute()
    if not cand.data:
        raise HTTPException(404, "Candidate not found")
    score_resp = (
        sb.table("scores")
        .select("*")
        .eq("candidate_id", candidate_id)
        .order("scored_at", desc=True)
        .limit(1)
        .execute()
    )
    score = score_resp.data[0] if score_resp.data else None
    role_resp = sb.table("roles").select("*").eq("id", cand.data["role_id"]).single().execute()
    return {"candidate": cand.data, "score": score, "role": role_resp.data}


@router.get("/roles/{role_id}/export")
async def export_excel(role_id: str):
    sb = get_client()
    role_resp = sb.table("roles").select("*").eq("id", role_id).single().execute()
    if not role_resp.data:
        raise HTTPException(404, "Role not found")
    role = role_resp.data

    cands = sb.table("candidates").select("*").eq("role_id", role_id).execute().data or []
    cand_ids = [c["id"] for c in cands]
    scores_by_cand: dict[str, dict] = {}
    if cand_ids:
        scores = sb.table("scores").select("*").in_("candidate_id", cand_ids).execute().data or []
        for s in scores:
            scores_by_cand.setdefault(s["candidate_id"], s)

    enriched = [{**c, "score": scores_by_cand.get(c["id"])} for c in cands]
    blob = generate_excel(role, enriched)
    headers = {"Content-Disposition": f'attachment; filename="scores_{role_id}.xlsx"'}
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
