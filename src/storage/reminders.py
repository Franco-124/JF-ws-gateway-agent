import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

_TABLE = "reminders"


def create_reminder(
    wa_number: str,
    description: str,
    scheduled_at_utc: datetime,
    follow_up_at_utc: datetime,
) -> str:
    if not wa_number:
        raise ValueError("wa_number es requerido")
    if not description:
        raise ValueError("description es requerida")

    client = get_supabase_client()
    row = {
        "wa_number": wa_number,
        "description": description,
        "scheduled_at": scheduled_at_utc.isoformat(),
        "follow_up_at": follow_up_at_utc.isoformat(),
        "status": "pending",
    }
    logger.info("Inserting reminder — wa_number=%s description=%r scheduled_at=%s", wa_number, description, scheduled_at_utc)
    result = client.table(_TABLE).insert(row).execute()

    if not result.data:
        raise RuntimeError(f"Supabase insert returned no data. Response: {result}")

    reminder_id = result.data[0]["id"]
    logger.info("Reminder inserted — id=%s", reminder_id)
    return reminder_id


def get_pending_reminders(wa_number: str) -> list[dict]:
    try:
        client = get_supabase_client()
        result = (
            client.table(_TABLE)
            .select("*")
            .eq("wa_number", wa_number)
            .in_("status", ["awaiting_confirmation", "awaiting_followup_confirmation"])
            .execute()
        )
        return result.data or []
    except Exception:
        logger.exception("get_pending_reminders failed for wa_number=%s", wa_number)
        return []


def get_due_reminders() -> list[dict]:
    try:
        client = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        result = (
            client.table(_TABLE)
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_at", now)
            .execute()
        )
        return result.data or []
    except Exception:
        logger.exception("get_due_reminders failed")
        return []


def get_due_followups() -> list[dict]:
    try:
        client = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        result = (
            client.table(_TABLE)
            .select("*")
            .eq("status", "awaiting_confirmation")
            .lte("follow_up_at", now)
            .is_("follow_up_sent_at", "null")
            .execute()
        )
        return result.data or []
    except Exception:
        logger.exception("get_due_followups failed")
        return []


def get_expired_reminders(timeout_minutes: int = 10) -> list[dict]:
    try:
        client = get_supabase_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()

        expired_first = (
            client.table(_TABLE)
            .select("*")
            .eq("status", "awaiting_confirmation")
            .is_("follow_up_sent_at", "null")
            .lte("scheduled_at", cutoff)
            .execute()
        )
        expired_followup = (
            client.table(_TABLE)
            .select("*")
            .eq("status", "awaiting_followup_confirmation")
            .lte("follow_up_sent_at", cutoff)
            .execute()
        )
        return (expired_first.data or []) + (expired_followup.data or [])
    except Exception:
        logger.exception("get_expired_reminders failed")
        return []


def update_reminder_status(reminder_id: str, status: str, **extra_fields: Any) -> None:
    try:
        client = get_supabase_client()
        payload: dict[str, Any] = {"status": status, **extra_fields}
        client.table(_TABLE).update(payload).eq("id", reminder_id).execute()
        logger.info("Reminder %s → status=%s", reminder_id, status)
    except Exception:
        logger.exception("update_reminder_status failed — id=%s status=%s", reminder_id, status)
        raise


def cancel_reminder(reminder_id: str) -> None:
    update_reminder_status(reminder_id, "cancelled")


def confirm_reminder(reminder_id: str) -> None:
    update_reminder_status(reminder_id, "confirmed")


def list_active_reminders(wa_number: str) -> list[dict]:
    try:
        client = get_supabase_client()
        result = (
            client.table(_TABLE)
            .select("id, description, scheduled_at, follow_up_at, status")
            .eq("wa_number", wa_number)
            .in_("status", ["pending", "awaiting_confirmation", "awaiting_followup_confirmation"])
            .order("scheduled_at")
            .execute()
        )
        return result.data or []
    except Exception:
        logger.exception("list_active_reminders failed for wa_number=%s", wa_number)
        return []
