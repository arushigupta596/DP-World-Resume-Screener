"""Score every preloaded candidate once and bake the scores into
backend/data/preloaded_resumes.json so future loads carry the full
scoring output (criteria scores, recommendation, AI summary).

Prereq: backend running locally on :8000.

Run once locally:
    cd backend && source .venv/bin/activate
    python scripts/score_preloaded.py
"""
from __future__ import annotations

import concurrent.futures
import json
import pathlib
import sys
import time

import httpx as requests  # use the SDK we already pin; sync API is identical for our needs

BACKEND = "http://localhost:8000"
BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
CACHE_PATH = BACKEND_DIR / "data" / "preloaded_resumes.json"
SCORE_FIELDS = (
    "criteria_scores",
    "total_score",
    "recommendation",
    "bonus_tools",
    "risk_flags",
    "ai_summary",
)
CONCURRENCY = 3


def _score_one(cand_id: str) -> dict | None:
    r = requests.post(f"{BACKEND}/api/candidates/{cand_id}/score", timeout=120.0)
    if r.status_code >= 400:
        return None
    return r.json().get("score")


def main() -> None:
    if not CACHE_PATH.exists():
        print(f"Cache missing: {CACHE_PATH}", file=sys.stderr)
        sys.exit(1)

    print("Loading active role...")
    role = requests.get(f"{BACKEND}/api/active-role", timeout=10).json()
    role_id = role["id"]

    print("Hydrating role with preloaded resumes...")
    r = requests.post(f"{BACKEND}/api/roles/{role_id}/load-preloaded", timeout=300.0)
    print("  load:", r.json())

    print("Fetching candidates from DB...")
    cands = requests.get(f"{BACKEND}/api/roles/{role_id}/candidates", timeout=30).json().get("candidates", [])
    by_hash = {c.get("cv_text_hash"): c for c in cands if c.get("cv_text_hash")}
    print(f"  {len(by_hash)} candidates indexed by cv_text_hash")

    entries = json.loads(CACHE_PATH.read_text())
    to_score: list[tuple[int, dict]] = []  # (entry_idx, candidate_row)
    skipped_existing = 0
    skipped_already_scored = 0
    for idx, e in enumerate(entries):
        if e.get("score"):
            skipped_already_scored += 1
            continue
        cand = by_hash.get(e.get("cv_text_hash"))
        if not cand:
            print(f"  ! no candidate row for entry {idx} ({e.get('file_name')})", file=sys.stderr)
            continue
        if cand.get("status") == "scored" and cand.get("score"):
            # DB has score but cache doesn't — copy across.
            e["score"] = {k: cand["score"].get(k) for k in SCORE_FIELDS}
            skipped_existing += 1
            continue
        to_score.append((idx, cand))

    print(
        f"\n{len(to_score)} to score, "
        f"{skipped_existing} pulled from DB without re-scoring, "
        f"{skipped_already_scored} already cached."
    )

    if to_score:
        print(f"\nScoring at concurrency {CONCURRENCY}...")
        started = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            futures = {pool.submit(_score_one, cand["id"]): (idx, cand) for idx, cand in to_score}
            done = 0
            for fut in concurrent.futures.as_completed(futures):
                idx, cand = futures[fut]
                done += 1
                try:
                    score = fut.result()
                except Exception as e:
                    print(f"  [{done}/{len(to_score)}] {cand.get('file_name')}: ERROR {e}")
                    continue
                if score:
                    entries[idx]["score"] = {k: score.get(k) for k in SCORE_FIELDS}
                    print(
                        f"  [{done}/{len(to_score)}] {cand.get('file_name'):50s} "
                        f"total={score.get('total_score')} {score.get('recommendation')}"
                    )
                else:
                    print(f"  [{done}/{len(to_score)}] {cand.get('file_name')}: no score returned")
        print(f"\nScoring elapsed: {time.time() - started:.1f}s")

    CACHE_PATH.write_text(json.dumps(entries))
    with_scores = sum(1 for e in entries if e.get("score"))
    print(f"\nSaved cache with scores: {with_scores}/{len(entries)} entries scored.")


if __name__ == "__main__":
    main()
