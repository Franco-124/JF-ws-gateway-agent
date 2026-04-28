import logging
from typing import Optional

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

    _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client
