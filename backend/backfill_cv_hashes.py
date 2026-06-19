"""One-time hash backfill for existing candidates.

For each candidate with cv_text set but cv_text_hash NULL, computes the
SHA-256 (same normalization as services.embedder.compute_text_hash) and
writes it back. Idempotent — re-running is safe.

Required after 04_cv_hash.sql so dedup works on the first re-upload of a
previously-uploaded CV.
"""
from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()

from db.supabase import get_client
from services.embedder import compute_text_hash


def main() -> None:
    sb = get_client()
    cands = (
        sb.table("candidates")
        .select("id, cv_text")
        .is_("cv_text_hash", "null")
        .not_.is_("cv_text", "null")
        .execute()
        .data
        or []
    )
    print(f"{len(cands)} candidates need a hash backfill")

    updated = 0
    failed = 0
    for c in cands:
        cid = c["id"]
        text = c.get("cv_text") or ""
        if not text:
            continue
        try:
            h = compute_text_hash(text)
            sb.table("candidates").update({"cv_text_hash": h}).eq("id", cid).execute()
            updated += 1
        except Exception as e:
            failed += 1
            print(f"  ! {cid[:8]}  failed: {e}", file=sys.stderr)

    print(f"\nDone. updated={updated}  failed={failed}")


if __name__ == "__main__":
    main()
