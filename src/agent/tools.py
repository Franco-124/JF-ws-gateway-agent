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
from whatsapp.client import send_template as _send_template
import config

logger = logging.getLogger(__name__)

# UTC-5 offset for Colombia (Bogotá)
_COLOMBIA_OFFSET = timedelta(hours=-5)


def _colombia_to_utc(iso_colombia: str) -> datetime:
    """Parse ISO 8601 datetime in Colombia time (UTC-5) and return UTC datetime."""
    try:
        naive = datetime.fromisoformat(iso_colombia.strip())
    except ValueError as exc:
        raise ValueError(f"Formato de fecha inválido '{iso_colombia}'. Usá ISO 8601, ej: '2025-05-14T15:00:00'") from exc

    colombia_tz = timezone(_COLOMBIA_OFFSET)
    aware = naive.replace(tzinfo=colombia_tz) if naive.tzinfo is None else naive
    return aware.astimezone(timezone.utc)


@tool
def create_reminder(description: str, scheduled_at: str, follow_up_minutes: int) -> str:
    """Crea un recordatorio inteligente.

    Args:
        description: Qué debe recordar el usuario. Ej: "enviar el presupuesto".
        scheduled_at: Hora del recordatorio en formato ISO 8601, hora Colombia (UTC-5).
                      Ej: "2025-05-14T15:00:00". Confirmá AM/PM si es ambiguo.
        follow_up_minutes: Minutos después del disparo inicial para el follow-up. Default: 30.
    """
    logger.info("[create_reminder] called — description=%r scheduled_at=%s follow_up_minutes=%s", description, scheduled_at, follow_up_minutes)
    try:
        wa_number = config.WA_NUMBER
        if not wa_number:
            raise ValueError("WA_NUMBER no está configurado en las variables de entorno")

        scheduled_utc = _colombia_to_utc(scheduled_at)
        follow_up_utc = scheduled_utc + timedelta(minutes=follow_up_minutes)
        logger.info("[create_reminder] times — scheduled_utc=%s follow_up_utc=%s", scheduled_utc, follow_up_utc)

        reminder_id = _create_reminder(
            wa_number=wa_number,
            description=description,
            scheduled_at_utc=scheduled_utc,
            follow_up_at_utc=follow_up_utc,
        )

        colombia_tz = timezone(_COLOMBIA_OFFSET)
        scheduled_local = scheduled_utc.astimezone(colombia_tz).strftime("%I:%M %p")
        followup_local = follow_up_utc.astimezone(colombia_tz).strftime("%I:%M %p")

        logger.info("[create_reminder] sending template — id=%s", reminder_id)
        # Send WhatsApp template
        template_name = getattr(config, "TEMPLATE_NAME", "NOMBRE_DE_TU_PLANTILLA")
        language_code = getattr(config, "TEMPLATE_LANGUAGE_CODE", "es")
        user_name = getattr(config, "TEMPLATE_USER_NAME", "Juan Carlos")
        

        template_rsp = _send_template(
            to=wa_number,
            template_name=template_name,
            language_code=language_code,
            user_name=user_name,
        )

        if not template_rsp.get("success"):
            
            # Create the reminder but log the failure to send the template
            logger.error("[create_reminder] failed to send template — id=%s response=%s", reminder_id, template_rsp)
            try:
                _create_reminder(
                    wa_number=wa_number,
                    description=description,
                    scheduled_at_utc=scheduled_utc,
                    follow_up_at_utc=follow_up_utc,
                )
                return f"Reminder creado con exito, Descripción: '{description}', Hora programada: {scheduled_local}, Hora de follow-up: {followup_local}."
            
            except Exception as exc:
                logger.exception("[create_reminder] failed to create reminder after template failure — id=%s", reminder_id)
                return f"Error creando el reminder después de fallar al enviar la plantilla ({type(exc).__name__}: {exc})"
            
        logger.info("[create_reminder] success — id=%s", reminder_id)
        return (
            f"Reminder guardado como borrador (ID: {reminder_id}) esperando confirmación. "
            f"Se le ha enviado al usuario la plantilla de WhatsApp para Confirmar o Rechazar la creación de la tarea."
        )
    except ValueError as exc:
        logger.error("[create_reminder] validation error — %s", exc)
        return f"No pude crear el reminder: {exc}"
    except Exception as exc:
        logger.exception("[create_reminder] unexpected error — %s: %s", type(exc).__name__, exc)
        return f"Error inesperado creando el reminder ({type(exc).__name__}: {exc})"


@tool
def cancel_reminder(reminder_id: str) -> str:
    """Cancela un reminder activo por su ID.

    Siempre llamá list_reminders primero y confirmá con el usuario cuál cancelar.
    """
    logger.info("[cancel_reminder] called — id=%s", reminder_id)
    try:
        _cancel_reminder(reminder_id)
        return f"Reminder {reminder_id} cancelado."
    except Exception as exc:
        logger.exception("[cancel_reminder] failed — id=%s", reminder_id)
        return f"No pude cancelar el reminder ({type(exc).__name__}: {exc})"


@tool
def confirm_reminder(reminder_id: str) -> str:
    """Marca un reminder como completado cuando el usuario confirma que realizó la tarea.

    Llamá esta tool cuando el usuario responda afirmativamente a un reminder pendiente.
    Si hay varios reminders pendientes, preguntá cuál antes de llamar.
    """
    logger.info("[confirm_reminder] called — id=%s", reminder_id)
    try:
        _confirm_reminder(reminder_id)
        return f"Reminder {reminder_id} marcado como completado."
    except Exception as exc:
        logger.exception("[confirm_reminder] failed — id=%s", reminder_id)
        return f"No pude confirmar el reminder ({type(exc).__name__}: {exc})"


@tool
def list_reminders() -> str:
    """Lista todos los reminders activos del usuario (pending, awaiting_confirmation, awaiting_followup_confirmation)."""
    logger.info("[list_reminders] called")
    try:
        wa_number = config.WA_NUMBER
        if not wa_number:
            return "WA_NUMBER no está configurado."

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
        logger.exception("[list_reminders] failed")
        return f"No pude obtener los reminders ({type(exc).__name__}: {exc})"


@tool
def close_conversation_tool(conversation_id: str, reason: str = "") -> str:
    """Cierra una conversacion activa cuando el usuario se despide o confirma que no necesita mas ayuda."""
    logger.info("[close_conversation_tool] called — id=%s", conversation_id)
    try:
        _close_conversation(conversation_id, reason or None)
        return "Conversacion cerrada."
    except Exception as exc:
        logger.exception("[close_conversation_tool] failed — id=%s", conversation_id)
        return f"No pude cerrar la conversacion ({type(exc).__name__}: {exc})"


tools = [
    create_reminder,
    cancel_reminder,
    confirm_reminder,
    list_reminders,
    close_conversation_tool,
]
