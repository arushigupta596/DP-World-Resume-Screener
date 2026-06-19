"""One-time backfill: embed all existing candidates that have cv_text but
no resume_chunks rows yet. Safe to re-run — skips already-embedded
candidates. Used after the pgvector migration is applied so the
previously-uploaded corpus works with RAG.

Usage:
    cd backend && source .venv/bin/activate
    python backfill_embeddings.py
"""
from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()

from db.supabase import get_client
from services.embedder import embed_and_store_candidate, has_embeddings


def main() -> None:
    sb = get_client()
    cands = (
        sb.table("candidates")
        .select("id, cv_text")
        .not_.is_("cv_text", "null")
        .execute()
        .data
        or []
    )
    print(f"{len(cands)} candidates with cv_text in DB")

    embedded = 0
    skipped = 0
    failed = 0
    for c in cands:
        cid = c["id"]
        try:
            if has_embeddings(cid):
                skipped += 1
                continue
            n = embed_and_store_candidate(cid, c["cv_text"])
            embedded += 1
            print(f"  + {cid[:8]}…  ({n} chunks)")
        except Exception as e:
            failed += 1
            print(f"  ! {cid[:8]}…  failed: {e}", file=sys.stderr)

    print(
        f"\nDone. embedded={embedded}  skipped={skipped}  failed={failed}"
    )


if __name__ == "__main__":
    main()
