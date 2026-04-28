import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse

from supabase import create_client, Client

from config import SUPABASE_SERVICE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    global _client
    if _client is not None:
        return _client

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase no configurado. Verifica SUPABASE_URL y SUPABASE_SERVICE_KEY.")

    parsed = urlparse(SUPABASE_URL)
    normalized_path = parsed.path.replace("/rest/v1", "").rstrip("/")
    normalized_url = urlunparse(parsed._replace(path=normalized_path))

    _client = create_client(normalized_url, SUPABASE_SERVICE_KEY)
    return _client
