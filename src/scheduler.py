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
from storage.conversation_history import fetch_conversation_messages
from storage.conversation_log import log_message
from whatsapp.client import send_message

logger = logging.getLogger(__name__)


def _invoke_reminder(
    wa_number: str,
    conversation_id: str,
    reminder_id: str,
    description: str,
    is_followup: bool = False,
) -> None:
    from agent.graph import graph

    history = fetch_conversation_messages(conversation_id)
    prior_messages = [
        {"role": "user" if m["direction"] == "in" else "assistant", "content": m["body"]}
        for m in history
        if m.get("direction") in {"in", "out"}
    ]

    if is_followup:
        trigger = (
            f"ACCIÓN: Enviá el follow-up del recordatorio '{description}'. "
            "Es la segunda vez que preguntás — sé empático, breve, sin presionar. "
            "No llames ninguna tool, solo escribí el mensaje directamente."
        )
    else:
        trigger = (
            f"ACCIÓN: Enviá el recordatorio '{description}' al usuario. "
            "Preguntá de forma amigable y natural si ya realizó la tarea. "
            "No llames ninguna tool, solo escribí el mensaje directamente."
        )

    result = graph.invoke({
        "messages": prior_messages,
        "conversation_id": conversation_id,
        "reminder_context": trigger,
    })

    response_text = result["messages"][-1].content
    token_usage = result.get("token_usage") or {}
    model_id = result.get("model_id") or "unknown"

    send_message(wa_number, response_text)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = "followup" if is_followup else "fire"
    log_message(
        conversation_id=conversation_id,
        message_id=f"scheduler_{reminder_id}_{suffix}_{ts}",
        wa_number=wa_number,
        direction="out",
        body=response_text,
        model_id=model_id,
        prompt_tokens=token_usage.get("input_tokens"),
        completion_tokens=token_usage.get("output_tokens"),
        total_tokens=token_usage.get("total_tokens"),
    )


def _job_fire_reminders() -> None:
    due = get_due_reminders()
    for reminder in due:
        wa_number = reminder["wa_number"]
        reminder_id = reminder["id"]
        description = reminder["description"]
        try:
            conversation_id = get_or_create_conversation(wa_number)
            _invoke_reminder(wa_number, conversation_id, reminder_id, description, is_followup=False)
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
            conversation_id = get_or_create_conversation(wa_number)
            _invoke_reminder(wa_number, conversation_id, reminder_id, description, is_followup=True)
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
