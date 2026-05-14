import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from storage.reminders import (
    get_due_reminders,
    get_due_followups,
    get_expired_reminders,
    update_reminder_status,
)
from storage.conversations import get_or_create_conversation
from whatsapp.client import send_message

logger = logging.getLogger(__name__)


def _job_fire_reminders() -> None:
    due = get_due_reminders()
    for reminder in due:
        wa_number = reminder["wa_number"]
        reminder_id = reminder["id"]
        description = reminder["description"]
        try:
            get_or_create_conversation(wa_number)
            send_message(wa_number, f"¿Ya {description}?")
            update_reminder_status(reminder_id, "awaiting_confirmation")
            logger.info("Reminder fired: %s", reminder_id)
        except Exception:
            logger.exception("Error firing reminder %s", reminder_id)


def _job_fire_followups() -> None:
    due = get_due_followups()
    for reminder in due:
        wa_number = reminder["wa_number"]
        reminder_id = reminder["id"]
        description = reminder["description"]
        try:
            get_or_create_conversation(wa_number)
            send_message(wa_number, f"¿Pudiste {description}?")
            now = datetime.now(timezone.utc).isoformat()
            update_reminder_status(
                reminder_id,
                "awaiting_followup_confirmation",
                follow_up_sent_at=now,
            )
            logger.info("Follow-up fired: %s", reminder_id)
        except Exception:
            logger.exception("Error firing follow-up %s", reminder_id)


def _job_close_expired() -> None:
    expired = get_expired_reminders(timeout_minutes=10)
    for reminder in expired:
        try:
            update_reminder_status(reminder["id"], "closed_unconfirmed")
            logger.info("Reminder closed (no response): %s", reminder["id"])
        except Exception:
            logger.exception("Error closing expired reminder %s", reminder["id"])


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(_job_fire_reminders, "interval", seconds=60, id="fire_reminders")
    scheduler.add_job(_job_fire_followups, "interval", seconds=60, id="fire_followups")
    scheduler.add_job(_job_close_expired, "interval", seconds=60, id="close_expired")
    return scheduler
