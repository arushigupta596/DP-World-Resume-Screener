"""Build a portable embeddings cache for one or more folders of CV PDFs.

For each PDF in the given folder(s), this:
  1. Parses the CV text via services.cv_parser.parse_cv
  2. Extracts the candidate name
  3. Computes the cv_text_hash
  4. If an entry with that hash already exists in the cache, reuses it
     (no OpenRouter call). Otherwise: chunks the text and embeds.
  5. Writes/merges into backend/data/preloaded_resumes.json

The resulting JSON is committed to the repo so any deploy of the
backend can serve the /load-preloaded endpoint without ever touching
OpenRouter again — chunks + embeddings travel with the code.

Run locally:
    cd backend
    source .venv/bin/activate
    python scripts/build_preloaded_cache.py /path/to/folder1 [/path/to/folder2 ...]

Pass multiple folders to merge them all in one pass. Files already in
the cache (by cv_text_hash) are skipped — safe to re-run.
"""
from __future__ import annotations

import json
import pathlib
import sys

from dotenv import load_dotenv

load_dotenv()

# Add backend/ to path when invoked from scripts/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from services.cv_parser import extract_candidate_name, parse_cv
from services.embedder import chunk_cv_text, compute_text_hash, embed_texts

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_PATH = BACKEND_DIR / "data" / "preloaded_resumes.json"


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/build_preloaded_cache.py /path/to/folder [/path/to/folder ...]",
            file=sys.stderr,
        )
        sys.exit(2)

    folders: list[pathlib.Path] = []
    for arg in sys.argv[1:]:
        p = pathlib.Path(arg)
        if not p.is_dir():
            print(f"Not a directory: {p}", file=sys.stderr)
            sys.exit(2)
        folders.append(p)

    # Load existing cache so we can resume without re-embedding what's already there.
    existing: list[dict] = []
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text())
        except json.JSONDecodeError:
            existing = []
    by_hash: dict[str, dict] = {e.get("cv_text_hash"): e for e in existing if e.get("cv_text_hash")}
    print(f"Cache: {len(existing)} existing entries")

    pdfs: list[pathlib.Path] = []
    for folder in folders:
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() in (".pdf", ".docx", ".txt"):
                pdfs.append(p)
    print(f"Found {len(pdfs)} files across {len(folders)} folder(s)")

    embedded = 0
    reused = 0
    failed = 0
    for idx, p in enumerate(pdfs, start=1):
        try:
            contents = p.read_bytes()
            text = parse_cv(contents, p.name)
            if not text:
                print(f"[{idx}/{len(pdfs)}] {p.name}  ! skipped: empty text")
                continue
            cv_hash = compute_text_hash(text)
            if cv_hash in by_hash:
                # Already cached — keep the existing entry (its score, if any, stays).
                reused += 1
                print(f"[{idx}/{len(pdfs)}] {p.name}  · cache hit")
                continue
            name = extract_candidate_name(text)
            chunks = chunk_cv_text(text)
            embeddings = embed_texts(chunks)
            entry = {
                "file_name": p.name,
                "parsed_name": name,
                "cv_text": text,
                "cv_text_hash": cv_hash,
                "chunks": [
                    {"chunk_index": i, "chunk_text": c, "embedding": e}
                    for i, (c, e) in enumerate(zip(chunks, embeddings))
                ],
            }
            by_hash[cv_hash] = entry
            embedded += 1
            print(f"[{idx}/{len(pdfs)}] {p.name}  + {len(chunks)} chunks; name={name!r}")
        except Exception as e:
            failed += 1
            print(f"[{idx}/{len(pdfs)}] {p.name}  ! failed: {type(e).__name__}: {e}", file=sys.stderr)

    merged = list(by_hash.values())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(merged))
    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(
        f"\nWrote {len(merged)} total entries to {OUTPUT_PATH} ({size_mb:.1f} MB) "
        f"[+{embedded} embedded, {reused} reused, {failed} failed]"
    )


if __name__ == "__main__":
    main()
