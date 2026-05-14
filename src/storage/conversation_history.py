import logging
from typing import List, Dict

from storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def fetch_conversation_messages(
    conversation_id: str,
    limit: int = 20,
) -> List[Dict]:
    client = get_supabase_client()
    try:
        result = (
            client.table("message_logs")
            .select("direction, body, created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        messages = sorted(result.data or [], key=lambda x: x.get("created_at") or "")
        return [{"direction": m["direction"], "body": m["body"]} for m in messages]
    except Exception as exc:
        logger.error(f"No se pudo obtener historial de Supabase: {exc}")
        return []
