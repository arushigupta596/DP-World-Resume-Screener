from __future__ import annotations

from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env"
            )
        _client = create_client(url, key)
    return _client
