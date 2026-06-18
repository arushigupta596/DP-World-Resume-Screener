from __future__ import annotations

import hashlib
import json
import logging
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
SIDECAR_PATH = BACKEND_DIR / "data" / "active_role.json"


async def bootstrap_active_role() -> str:
    """Ensure a fixed active role exists; return its id.

    Idempotency: a sidecar file caches (role_id, jd_hash). If JD.docx is
    unchanged and the cached role still exists, reuse it. If no sidecar
    exists but Supabase already has roles, adopt the most recently created
    one to preserve any in-progress work. Otherwise extract JD via the
    LLM and insert a fresh role.
    """
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
            logger.warning("Sidecar role %s missing in DB; will re-seed", role_id)
        else:
            logger.info("JD hash changed or sidecar incomplete; re-seeding role")

    # No valid sidecar. Look for an existing role to adopt (preserves prior runs).
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
        SIDECAR_PATH.write_text(json.dumps({"role_id": role_id, "jd_hash": jd_hash}, indent=2))
        logger.info("Adopted existing role %s as active role (sidecar written)", role_id)
        return role_id

    # Fresh seed via LLM.
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
    SIDECAR_PATH.write_text(json.dumps({"role_id": role_id, "jd_hash": jd_hash}, indent=2))
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


app = FastAPI(title="DP World CV Screener", version="0.2.0", lifespan=lifespan)

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
