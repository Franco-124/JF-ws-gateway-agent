import logging
from typing import Optional

from storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def log_message(
    conversation_id: str,
    message_id: str,
    wa_number: str,
    direction: str,
    body: str,
    model_id: Optional[str] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    provider: str = "openai",
) -> None:
    client = get_supabase_client()
    payload = {
        "conversation_id": conversation_id,
        "message_id": message_id,
        "wa_number": wa_number,
        "direction": direction,
        "body": body,
        "model_id": model_id,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "provider": provider,
    }

    try:
        client.table("message_logs").insert(payload).execute()
    except Exception as exc:
        logger.error(f"No se pudo registrar mensaje en Supabase: {exc}")
