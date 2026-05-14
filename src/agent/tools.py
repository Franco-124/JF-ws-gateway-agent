import logging
from datetime import datetime, timezone, timedelta

from langchain_core.tools import tool

from storage.conversations import close_conversation as _close_conversation
from storage.reminders import (
    create_reminder as _create_reminder,
    cancel_reminder as _cancel_reminder,
    confirm_reminder as _confirm_reminder,
    list_active_reminders,
)
import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# UTC-5 offset for Colombia (Bogotá)
_COLOMBIA_OFFSET = timedelta(hours=-5)


def _colombia_to_utc(iso_colombia: str) -> datetime:
    """Parse ISO 8601 datetime in Colombia time (UTC-5) and return UTC datetime."""
    naive = datetime.fromisoformat(iso_colombia.strip())
    colombia_tz = timezone(_COLOMBIA_OFFSET)
    if naive.tzinfo is None:
        aware = naive.replace(tzinfo=colombia_tz)
    else:
        aware = naive
    return aware.astimezone(timezone.utc)


@tool
def create_reminder(description: str, scheduled_at: str, follow_up_minutes: int) -> str:
    """Crea un recordatorio inteligente.

    Args:
        description: Qué debe recordar el usuario. Ej: "enviar el presupuesto".
        scheduled_at: Hora del recordatorio en formato ISO 8601, hora Colombia (UTC-5).
                      Ej: "2025-05-14T15:00:00". Siempre confirma AM/PM antes de llamar.
        follow_up_minutes: Minutos después del disparo inicial para el follow-up si no confirma.
    """
    try:
        wa_number = config.WA_NUMBER
        scheduled_utc = _colombia_to_utc(scheduled_at)
        follow_up_utc = scheduled_utc + timedelta(minutes=follow_up_minutes)

        reminder_id = _create_reminder(
            wa_number=wa_number,
            description=description,
            scheduled_at_utc=scheduled_utc,
            follow_up_at_utc=follow_up_utc,
        )

        colombia_tz = timezone(_COLOMBIA_OFFSET)
        scheduled_local = scheduled_utc.astimezone(colombia_tz).strftime("%I:%M %p")
        followup_local = follow_up_utc.astimezone(colombia_tz).strftime("%I:%M %p")

        logger.info("Reminder created: %s", reminder_id)
        return (
            f"Reminder creado (ID: {reminder_id}). "
            f"Te pregunto a las {scheduled_local}; "
            f"si no confirmás, vuelvo a preguntar a las {followup_local}."
        )
    except Exception as exc:
        logger.error("Error creating reminder: %s", exc)
        return "No pude crear el reminder. Intentá de nuevo."


@tool
def cancel_reminder(reminder_id: str) -> str:
    """Cancela un reminder activo por su ID.

    Siempre lista los reminders con list_reminders primero y confirma con el usuario
    cuál desea cancelar antes de llamar esta tool.
    """
    try:
        _cancel_reminder(reminder_id)
        logger.info("Reminder cancelled: %s", reminder_id)
        return f"Reminder {reminder_id} cancelado."
    except Exception as exc:
        logger.error("Error cancelling reminder %s: %s", reminder_id, exc)
        return "No pude cancelar el reminder. Intentá de nuevo."


@tool
def confirm_reminder(reminder_id: str) -> str:
    """Marca un reminder como completado cuando el usuario confirma que realizó la tarea.

    Llamá esta tool cuando el usuario responda afirmativamente a un reminder pendiente.
    Si hay varios reminders pendientes, siempre preguntá cuál antes de llamar.
    """
    try:
        _confirm_reminder(reminder_id)
        logger.info("Reminder confirmed: %s", reminder_id)
        return f"Reminder {reminder_id} marcado como completado."
    except Exception as exc:
        logger.error("Error confirming reminder %s: %s", reminder_id, exc)
        return "No pude confirmar el reminder. Intentá de nuevo."


@tool
def list_reminders() -> str:
    """Lista todos los reminders activos del usuario (pending, awaiting_confirmation, awaiting_followup_confirmation)."""
    try:
        wa_number = config.WA_NUMBER
        reminders = list_active_reminders(wa_number)
        if not reminders:
            return "No tenés reminders activos."

        colombia_tz = timezone(_COLOMBIA_OFFSET)
        lines = []
        for r in reminders:
            scheduled = datetime.fromisoformat(r["scheduled_at"]).astimezone(colombia_tz).strftime("%d/%m %I:%M %p")
            lines.append(f"- [{r['id']}] {r['description']} | {scheduled} | {r['status']}")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("Error listing reminders: %s", exc)
        return "No pude obtener los reminders. Intentá de nuevo."


@tool
def close_conversation_tool(conversation_id: str, reason: str = "") -> str:
    """Cierra una conversacion activa cuando el usuario se despide o confirma que no necesita mas ayuda."""
    try:
        _close_conversation(conversation_id, reason or None)
        return "Conversacion cerrada."
    except Exception as exc:
        logger.error("Error cerrando conversacion: %s", exc)
        return "No pude cerrar la conversacion en este momento."


tools = [
    create_reminder,
    cancel_reminder,
    confirm_reminder,
    list_reminders,
    close_conversation_tool,
]
