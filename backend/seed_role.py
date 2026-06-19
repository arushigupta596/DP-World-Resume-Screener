"""One-time seeding script: extract JD via LLM, insert role into Supabase,
write role_seed.json. Commit role_seed.json to the repo so production cold
starts don't need to re-run the LLM.

Run once locally before deploying:
    cd backend && source .venv/bin/activate && python seed_role.py

Re-run anytime JD.docx changes — it overwrites role_seed.json with the
new role's id + new JD hash.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import pathlib
import sys

from dotenv import load_dotenv

load_dotenv()

from db.supabase import get_client
from services.cv_parser import parse_jd
from services.jd_extractor import extract_jd

BACKEND_DIR = pathlib.Path(__file__).resolve().parent
JD_PATH = BACKEND_DIR / "data" / "JD.docx"
SEED_PATH = BACKEND_DIR / "data" / "role_seed.json"


async def main() -> None:
    if not JD_PATH.exists():
        print(f"JD file missing at {JD_PATH}", file=sys.stderr)
        sys.exit(1)

    jd_bytes = JD_PATH.read_bytes()
    jd_hash = hashlib.sha256(jd_bytes).hexdigest()
    jd_text = parse_jd(jd_bytes, JD_PATH.name)

    print(f"JD: {len(jd_text)} chars, hash {jd_hash[:12]}…")
    print("Extracting JD via OpenRouter…")
    parsed = await extract_jd(jd_text)

    payload = {
        "title": parsed.get("title") or "Market Research Analyst",
        "company": parsed.get("company"),
        "location": parsed.get("location"),
        "reports_to": parsed.get("reports_to"),
        "min_experience_years": parsed.get("min_experience_years") or 0,
        "min_qualification": parsed.get("min_qualification"),
        "jd_text": parsed.get("jd_text") or jd_text,
        "scoring_criteria": parsed.get("scoring_criteria") or [],
    }

    sb = get_client()
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
        print(f"Adopting existing role {role_id} (most recent in DB)")
    else:
        inserted = sb.table("roles").insert(payload).execute()
        if not inserted.data:
            print("Failed to insert role", file=sys.stderr)
            sys.exit(1)
        role_id = inserted.data[0]["id"]
        print(f"Inserted new role {role_id}")

    SEED_PATH.write_text(json.dumps({"role_id": role_id, "jd_hash": jd_hash}, indent=2))
    print(f"Wrote {SEED_PATH}")
    print("Commit this file so production reads it on cold start.")


if __name__ == "__main__":
    asyncio.run(main())
