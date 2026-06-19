"""Build a portable embeddings cache for a set of CV PDFs.

For each PDF in OneDrive_4_19-06-2026/ (configurable), this:
  1. Parses the CV text via services.cv_parser.parse_cv
  2. Extracts the candidate name
  3. Computes the cv_text_hash
  4. Chunks the text and embeds the chunks via OpenRouter
  5. Appends an entry to backend/data/preloaded_resumes.json

The resulting JSON is committed to the repo so any deploy of the
backend can serve the /load-preloaded endpoint without ever touching
OpenRouter again — chunks + embeddings travel with the code.

Run once locally:
    cd backend
    source .venv/bin/activate
    python scripts/build_preloaded_cache.py /path/to/OneDrive_4_19-06-2026
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
        print("Usage: python scripts/build_preloaded_cache.py /path/to/folder", file=sys.stderr)
        sys.exit(2)
    folder = pathlib.Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Not a directory: {folder}", file=sys.stderr)
        sys.exit(2)

    pdfs = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".pdf", ".docx", ".txt"))
    print(f"Found {len(pdfs)} files in {folder}")

    entries = []
    for idx, p in enumerate(pdfs, start=1):
        print(f"[{idx}/{len(pdfs)}] {p.name}")
        try:
            contents = p.read_bytes()
            text = parse_cv(contents, p.name)
            if not text:
                print(f"  ! skipped: empty text (scanned PDF?)")
                continue
            name = extract_candidate_name(text)
            chunks = chunk_cv_text(text)
            embeddings = embed_texts(chunks)
            entry = {
                "file_name": p.name,
                "parsed_name": name,
                "cv_text": text,
                "cv_text_hash": compute_text_hash(text),
                "chunks": [
                    {"chunk_index": i, "chunk_text": c, "embedding": e}
                    for i, (c, e) in enumerate(zip(chunks, embeddings))
                ],
            }
            entries.append(entry)
            print(f"  ok: {len(chunks)} chunks; name={name!r}")
        except Exception as e:
            print(f"  ! failed: {type(e).__name__}: {e}", file=sys.stderr)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(entries))
    size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\nWrote {len(entries)} entries to {OUTPUT_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
