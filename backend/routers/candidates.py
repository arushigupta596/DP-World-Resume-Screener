from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from db.supabase import get_client
from services.cv_parser import extract_candidate_name, parse_cv

logger = logging.getLogger("cv-screener.candidates")

router = APIRouter(tags=["candidates"])

MAX_FILES = 100
STORAGE_BUCKET = "cvs"


def _content_type_for(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if lower.endswith(".txt"):
        return "text/plain"
    return "application/octet-stream"


def _process_one(role_id: str, file_name: str, contents: bytes) -> dict:
    sb = get_client()
    result = {"file_name": file_name, "status": "pending", "name": None, "candidate_id": None}
    try:
        cv_text = parse_cv(contents, file_name)
    except ValueError as e:
        result["status"] = "error"
        result["error_msg"] = str(e)
        cv_text = ""
        scanned = False
    else:
        scanned = cv_text == "" and file_name.lower().endswith(".pdf")

    name = extract_candidate_name(cv_text) if cv_text else None

    storage_path = f"{role_id}/{uuid.uuid4()}_{file_name}"
    try:
        sb.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=contents,
            file_options={"content-type": _content_type_for(file_name), "upsert": "false"},
        )
    except Exception as e:
        # Non-fatal: continue without storage path so demo is resilient.
        storage_path = None
        result["error_msg"] = f"Storage upload failed: {e}"

    row = {
        "role_id": role_id,
        "name": name,
        "cv_text": cv_text or None,
        "cv_file_path": storage_path,
        "file_name": file_name,
        "status": "error" if (scanned or result["status"] == "error") else "pending",
        "error_msg": (
            "Scanned PDF — text extraction failed"
            if scanned
            else result.get("error_msg")
        ),
    }
    inserted = sb.table("candidates").insert(row).execute()
    candidate_id = inserted.data[0]["id"] if inserted.data else None

    # Best-effort embedding for RAG. If OPENAI_API_KEY is missing or the
    # embeddings API is unreachable, log and continue — scoring will fall
    # back to the full-CV prompt path.
    if candidate_id and cv_text:
        try:
            from services.embedder import embed_and_store_candidate
            embed_and_store_candidate(candidate_id, cv_text)
        except Exception as e:
            logger.warning("Embedding failed for %s: %s", candidate_id, e)

    result["candidate_id"] = candidate_id
    result["name"] = name
    result["status"] = row["status"]
    if row["error_msg"]:
        result["error_msg"] = row["error_msg"]
    return result


class SearchRequest(BaseModel):
    query: str
    limit: int = 20


@router.post("/roles/{role_id}/search")
async def search_candidates(role_id: str, payload: SearchRequest):
    """Hybrid (vector + FTS) search across all CVs in a role."""
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(400, "query is required")

    try:
        from services.retriever import search_role
    except ImportError as e:
        raise HTTPException(503, f"Search unavailable: {e}")

    try:
        hits = search_role(role_id, query, limit=payload.limit)
    except Exception as e:
        raise HTTPException(503, f"Search failed: {e}")

    if not hits:
        return {"results": []}

    sb = get_client()
    cand_ids = [h["candidate_id"] for h in hits]
    cands = (
        sb.table("candidates").select("*").in_("id", cand_ids).execute().data or []
    )
    by_id = {c["id"]: c for c in cands}

    scores = (
        sb.table("scores").select("*").in_("candidate_id", cand_ids).execute().data or []
    )
    score_by_cand: dict = {}
    for s in scores:
        score_by_cand.setdefault(s["candidate_id"], s)

    results = []
    for h in hits:
        cid = h["candidate_id"]
        cand = by_id.get(cid)
        if not cand:
            continue
        results.append({
            "candidate_id": cid,
            "name": cand.get("name"),
            "file_name": cand.get("file_name"),
            "status": cand.get("status"),
            "matched_chunk": h.get("best_chunk", ""),
            "rrf_score": h.get("rrf_score", 0),
            "score": score_by_cand.get(cid),
        })
    return {"results": results}


@router.post("/roles/{role_id}/candidates")
async def upload_candidates(role_id: str, files: list[UploadFile] = File(...)):
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Max {MAX_FILES} files per upload")

    results = []
    for f in files:
        contents = await f.read()
        results.append(_process_one(role_id, f.filename or "unnamed", contents))
    return {"results": results}


@router.post("/roles/{role_id}/candidates/single")
async def upload_one(role_id: str, file: UploadFile = File(...)):
    """One file per request. Frontend loops over the user's selection and
    calls this once per file so each request stays well inside Vercel's
    serverless function timeout."""
    contents = await file.read()
    return _process_one(role_id, file.filename or "unnamed", contents)


@router.delete("/roles/{role_id}/candidates")
async def clear_candidates(role_id: str):
    """Wipe all candidates for a role. Scores cascade-delete via FK."""
    sb = get_client()
    existing = (
        sb.table("candidates").select("id").eq("role_id", role_id).execute().data or []
    )
    if not existing:
        return {"deleted": 0}
    deleted = (
        sb.table("candidates").delete().eq("role_id", role_id).execute().data or []
    )
    return {"deleted": len(deleted)}


@router.get("/roles/{role_id}/candidates")
async def list_candidates(role_id: str):
    sb = get_client()
    cands = sb.table("candidates").select("*").eq("role_id", role_id).execute().data or []
    cand_ids = [c["id"] for c in cands]
    scores_by_cand: dict[str, dict] = {}
    if cand_ids:
        scores = (
            sb.table("scores")
            .select("*")
            .in_("candidate_id", cand_ids)
            .order("scored_at", desc=True)
            .execute()
            .data
            or []
        )
        for s in scores:
            scores_by_cand.setdefault(s["candidate_id"], s)

    enriched = []
    for c in cands:
        c["score"] = scores_by_cand.get(c["id"])
        enriched.append(c)

    # NULLS LAST: split into scored / unscored, sort scored desc, then concat.
    scored = [c for c in enriched if c.get("score") and c["score"].get("total_score") is not None]
    unscored = [c for c in enriched if not (c.get("score") and c["score"].get("total_score") is not None)]
    scored.sort(key=lambda c: c["score"]["total_score"], reverse=True)
    return {"candidates": scored + unscored}
