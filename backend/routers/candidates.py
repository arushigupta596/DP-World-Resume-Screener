from __future__ import annotations

import json
import logging
import pathlib
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from db.supabase import get_client
from services.cv_parser import extract_candidate_name, parse_cv

logger = logging.getLogger("cv-screener.candidates")

router = APIRouter(tags=["candidates"])

MAX_FILES = 100
STORAGE_BUCKET = "cvs"

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
PRELOADED_PATH = BACKEND_DIR / "data" / "preloaded_resumes.json"


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

    # Content hash for dedup. Computed before insert so the row carries it.
    from services.embedder import compute_text_hash, copy_chunks, embed_and_store_candidate

    cv_text_hash = compute_text_hash(cv_text) if cv_text else None

    row = {
        "role_id": role_id,
        "name": name,
        "cv_text": cv_text or None,
        "cv_text_hash": cv_text_hash,
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

    # RAG-only: every successful upload ends with chunks available for
    # retrieval. Try the cache-hit path first (copy chunks from a prior
    # candidate with the same cv_text_hash); fall through to embedding only
    # on cache miss. No silent failures — exceptions propagate.
    if candidate_id and cv_text and cv_text_hash:
        cached = (
            sb.table("candidates")
            .select("id")
            .eq("cv_text_hash", cv_text_hash)
            .neq("id", candidate_id)
            .limit(5)
            .execute()
            .data
            or []
        )
        copied = False
        for c in cached:
            try:
                n = copy_chunks(c["id"], candidate_id)
                logger.info(
                    "cv_text cache hit; copied %d chunks from %s for %s",
                    n, c["id"][:8], candidate_id[:8],
                )
                copied = True
                break
            except RuntimeError:
                # That source happened to have no chunks; try the next match.
                continue
        if not copied:
            n = embed_and_store_candidate(candidate_id, cv_text)
            logger.info("cv_text cache miss; embedded %d chunks for %s", n, candidate_id[:8])

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

    from services.retriever import search_role
    hits = search_role(role_id, query, limit=payload.limit)
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


@router.get("/preloaded-resumes/info")
async def preloaded_info():
    """How many pre-cached resumes ship with this build."""
    if not PRELOADED_PATH.exists():
        return {"available": False, "count": 0}
    try:
        data = json.loads(PRELOADED_PATH.read_text())
    except Exception:
        return {"available": False, "count": 0}
    return {"available": True, "count": len(data)}


@router.post("/roles/{role_id}/load-preloaded")
async def load_preloaded(role_id: str):
    """Hydrate the active role with the pre-cached resume set shipped at
    backend/data/preloaded_resumes.json. Each entry brings its own chunk
    embeddings — zero OpenRouter calls. Dedups against existing
    candidates for this role using cv_text_hash (skips already-loaded
    ones)."""
    if not PRELOADED_PATH.exists():
        raise HTTPException(404, "No preloaded resume cache present")

    entries = json.loads(PRELOADED_PATH.read_text())
    if not entries:
        return {"loaded": 0, "skipped": 0}

    sb = get_client()

    # Find which hashes are already present in this role so we can skip.
    hashes = [e["cv_text_hash"] for e in entries if e.get("cv_text_hash")]
    existing = (
        sb.table("candidates")
        .select("cv_text_hash")
        .eq("role_id", role_id)
        .in_("cv_text_hash", hashes)
        .execute()
        .data
        or []
    )
    already = {r["cv_text_hash"] for r in existing if r.get("cv_text_hash")}

    def _strip_nul(s):
        return s.replace("\x00", "") if isinstance(s, str) else s

    loaded = 0
    skipped = 0
    for e in entries:
        h = e.get("cv_text_hash")
        if h in already:
            skipped += 1
            continue

        cand_row = {
            "role_id": role_id,
            "name": _strip_nul(e.get("parsed_name")),
            "cv_text": _strip_nul(e.get("cv_text")),
            "cv_text_hash": h,
            "cv_file_path": None,  # File not in Storage; cache is metadata-only.
            "file_name": e.get("file_name"),
            "status": "pending",
            "error_msg": None,
        }
        inserted = sb.table("candidates").insert(cand_row).execute()
        if not inserted.data:
            continue
        cand_id = inserted.data[0]["id"]

        chunks = e.get("chunks") or []
        if chunks:
            rows = [
                {
                    "candidate_id": cand_id,
                    "chunk_index": c.get("chunk_index", i),
                    "chunk_text": _strip_nul(c.get("chunk_text", "")),
                    "embedding": c.get("embedding"),
                }
                for i, c in enumerate(chunks)
            ]
            sb.table("resume_chunks").insert(rows).execute()

        loaded += 1

    logger.info("Preloaded resumes: loaded=%d skipped=%d", loaded, skipped)
    return {"loaded": loaded, "skipped": skipped, "total_in_cache": len(entries)}


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
