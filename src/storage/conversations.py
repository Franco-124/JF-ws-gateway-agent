import logging
from datetime import datetime, timezone
from typing import Optional

from storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def get_or_create_conversation(wa_number: str) -> str:
    client = get_supabase_client()
    try:
        response = (
            client.table("conversations")
            .select("id")
            .eq("wa_number", wa_number)
            .eq("status", "open")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]["id"]

        created = (
            client.table("conversations")
            .insert({"wa_number": wa_number, "status": "open"})
            .execute()
        )
        return created.data[0]["id"]
    except Exception as exc:
        logger.error(f"No se pudo obtener/crear conversacion en Supabase: {exc}")
        raise


def close_conversation(conversation_id: str, reason: Optional[str] = None) -> None:
    client = get_supabase_client()
    closed_at = datetime.now(timezone.utc).isoformat()
    payload = {"status": "closed", "closed_at": closed_at}
    if reason:
        payload["closed_reason"] = reason
    try:
        client.table("conversations").update(payload).eq("id", conversation_id).execute()
    except Exception as exc:
        logger.error(f"No se pudo cerrar conversacion en Supabase: {exc}")
