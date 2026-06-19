from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from db.supabase import get_client
from routers import roles, candidates, scores
from services.cv_parser import parse_jd
from services.jd_extractor import extract_jd

logger = logging.getLogger("cv-screener.bootstrap")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

BACKEND_DIR = pathlib.Path(__file__).resolve().parent
JD_PATH = BACKEND_DIR / "data" / "JD.docx"
SEED_PATH = BACKEND_DIR / "data" / "role_seed.json"
SIDECAR_PATH = BACKEND_DIR / "data" / "active_role.json"


async def bootstrap_active_role() -> str:
    """Return the active role id.

    On Vercel (and any read-only filesystem), this just reads role_seed.json
    (committed to the repo). For local dev, the sidecar approach + LLM
    fallback is preserved.
    """
    # Production path: pre-baked seed, no LLM call, no filesystem writes.
    if SEED_PATH.exists():
        try:
            seed = json.loads(SEED_PATH.read_text())
        except json.JSONDecodeError:
            seed = {}
        role_id = seed.get("role_id")
        if role_id:
            logger.info("Active role from role_seed.json: %s", role_id)
            return role_id
        logger.warning("role_seed.json present but missing role_id; falling back")

    # Local-dev fallback: existing sidecar + LLM bootstrap logic.
    if not JD_PATH.exists():
        raise RuntimeError(f"JD file missing at {JD_PATH}")

    jd_bytes = JD_PATH.read_bytes()
    jd_hash = hashlib.sha256(jd_bytes).hexdigest()
    sb = get_client()

    if SIDECAR_PATH.exists():
        try:
            cached = json.loads(SIDECAR_PATH.read_text())
        except json.JSONDecodeError:
            cached = {}
        if cached.get("jd_hash") == jd_hash and cached.get("role_id"):
            role_id = cached["role_id"]
            check = sb.table("roles").select("id").eq("id", role_id).execute()
            if check.data:
                logger.info("Reusing cached active role %s (JD hash matches)", role_id)
                return role_id

    existing = (
        sb.table("roles")
        .select("id, created_at")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        role_id = existing[0]["id"]
        try:
            SIDECAR_PATH.write_text(json.dumps({"role_id": role_id, "jd_hash": jd_hash}))
        except OSError:
            pass  # read-only fs (Vercel) — caller falls through to seed-based bootstrap next deploy
        logger.info("Adopted existing role %s as active role", role_id)
        return role_id

    jd_text = parse_jd(jd_bytes, JD_PATH.name)
    logger.info("Extracting JD via LLM (jd length=%d chars)", len(jd_text))
    parsed = await extract_jd(jd_text)
    insert_payload = {
        "title": parsed.get("title") or "Market Research Analyst",
        "company": parsed.get("company"),
        "location": parsed.get("location"),
        "reports_to": parsed.get("reports_to"),
        "min_experience_years": parsed.get("min_experience_years") or 0,
        "min_qualification": parsed.get("min_qualification"),
        "jd_text": parsed.get("jd_text") or jd_text,
        "scoring_criteria": parsed.get("scoring_criteria") or [],
    }
    inserted = sb.table("roles").insert(insert_payload).execute()
    if not inserted.data:
        raise RuntimeError("Failed to insert seeded role")
    role_id = inserted.data[0]["id"]
    try:
        SIDECAR_PATH.write_text(json.dumps({"role_id": role_id, "jd_hash": jd_hash}))
    except OSError:
        pass
    logger.info("Active role seeded: %s (JD hash: %s…)", role_id, jd_hash[:8])
    return role_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        role_id = await bootstrap_active_role()
        app.state.active_role_id = role_id
    except Exception as e:
        logger.exception("Failed to bootstrap active role: %s", e)
        app.state.active_role_id = None
        yield
        return

    # Prime the criterion-query embedding cache so scoring calls don't
    # pay the per-candidate retrieval-embedding cost. Non-fatal: if this
    # fails (e.g., OpenRouter hiccup at boot), the scorer will populate
    # the cache lazily on the first scoring call.
    if role_id:
        try:
            sb = get_client()
            role_resp = sb.table("roles").select("*").eq("id", role_id).single().execute()
            if role_resp.data:
                from services.scorer import prime_criterion_embeddings
                prime_criterion_embeddings(role_resp.data)
        except Exception as e:
            logger.warning("Failed to prime criterion embeddings at startup: %s", e)
    yield


app = FastAPI(
    title="DP World CV Screener",
    version="0.3.0",
    lifespan=lifespan,
    # On Vercel's experimentalServices model the backend is mounted at
    # /_/backend; set ROOT_PATH=/_/backend in that env so FastAPI generates
    # correct URLs (docs, redirects, etc.). Empty in local dev.
    root_path=os.getenv("ROOT_PATH", ""),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roles.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(scores.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "active_role_id": getattr(app.state, "active_role_id", None)}
