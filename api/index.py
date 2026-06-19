"""Vercel serverless entry point. Vercel's Python runtime detects the
`app` ASGI object exported here and routes inbound `/api/*` requests to
it (per the rewrite rule in vercel.json).
"""
import pathlib
import sys

# Make the `backend/` package importable when this file runs from /api/.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend"))

from main import app  # noqa: E402, F401  (FastAPI ASGI app — required export)
