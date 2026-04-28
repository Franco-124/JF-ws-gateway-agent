import logging
from typing import List, Dict

from storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def fetch_conversation_messages(
    conversation_id: str,
    limit_per_direction: int = 2,
) -> List[Dict]:
    client = get_supabase_client()
    try:
        inbound = (
            client.table("message_logs")
            .select("direction, body, created_at")
            .eq("conversation_id", conversation_id)
            .eq("direction", "in")
            .order("created_at", desc=True)
            .limit(limit_per_direction)
            .execute()
        )
        outbound = (
            client.table("message_logs")
            .select("direction, body, created_at")
            .eq("conversation_id", conversation_id)
            .eq("direction", "out")
            .order("created_at", desc=True)
            .limit(limit_per_direction)
            .execute()
        )

        combined = (inbound.data or []) + (outbound.data or [])
        combined.sort(key=lambda item: item.get("created_at") or "")
        return [{"direction": item["direction"], "body": item["body"]} for item in combined]
    except Exception as exc:
        logger.error(f"No se pudo obtener historial de Supabase: {exc}")
        return []
