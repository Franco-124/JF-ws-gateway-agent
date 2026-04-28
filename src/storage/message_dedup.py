import logging
from datetime import datetime, timedelta

from storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def cleanup_message_dedup(retention_hours: int = 24) -> None:
    cutoff = datetime.utcnow() - timedelta(hours=retention_hours)
    cutoff_iso = cutoff.isoformat() + "Z"

    try:
        client = get_supabase_client()
        client.table("message_dedup").delete().lt("created_at", cutoff_iso).execute()
    except Exception as exc:
        logger.error(f"No se pudo limpiar message_dedup: {exc}")


def register_message_id(message_id: str, wa_number: str) -> bool:
    client = get_supabase_client()
    payload = {"message_id": message_id, "wa_number": wa_number}

    try:
        client.table("message_dedup").insert(payload).execute()
        cleanup_message_dedup()
        return True
    except Exception as exc:
        error_text = str(exc).lower()
        if "duplicate key" in error_text or "23505" in error_text:
            logger.info(f"Mensaje duplicado detectado. message_id={message_id}")
            return False

        logger.error(f"No se pudo registrar message_id en Supabase: {exc}")
        return True
