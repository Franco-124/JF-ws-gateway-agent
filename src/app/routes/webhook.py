import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response
from agent.graph import graph
from whatsapp.client import send_message, mark_as_read
from storage.conversation_log import log_message
from storage.conversation_history import fetch_conversation_messages
from storage.message_dedup import register_message_id
from storage.conversations import get_or_create_conversation
from storage.reminders import get_pending_reminders, get_latest_pending_creation, update_reminder_status
import config

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_reminder_context(pending: list[dict]) -> str:
    lines = ["Reminders pendientes de confirmación del usuario:"]
    for r in pending:
        lines.append(f"- ID: {r['id']} | Tarea: {r['description']} | Estado: {r['status']}")
    lines.append(
        "Si el mensaje del usuario es una respuesta a alguno de estos reminders, "
        "interpretalo y llamá confirm_reminder con el ID correspondiente. "
        "Si hay varios y no queda claro a cuál responde, preguntá antes de confirmar."
    )
    return "\n".join(lines)


def _invoke_agent(message: str, conversation_id: str, wa_number: str) -> tuple[str, dict, str]:
    print(f"[WEBHOOK] _invoke_agent called — message={message!r}", flush=True)
    history = fetch_conversation_messages(conversation_id)
    prior_messages = [
        {"role": "user" if item["direction"] == "in" else "assistant", "content": item["body"]}
        for item in history
        if item.get("direction") in {"in", "out"}
    ]

    pending_reminders = get_pending_reminders(wa_number)
    extra_context = _build_reminder_context(pending_reminders) if pending_reminders else None

    payload = {
        "messages": prior_messages + [{"role": "user", "content": message}],
        "conversation_id": conversation_id,
    }
    if extra_context:
        payload["reminder_context"] = extra_context

    result = graph.invoke(payload)
    content = result["messages"][-1].content
    token_usage = result.get("token_usage") or {}
    model_id = result.get("model_id") or "unknown"
    return content, token_usage, model_id


@router.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == config.VERIFY_TOKEN:
        logger.info("Webhook verificado exitosamente")
        return Response(
            content=str(challenge),
            media_type="text/plain",
            headers={"ngrok-skip-browser-warning": "true"},
        )

    logger.error("Verificación fallida: token o modo incorrecto")
    return Response(content="Error de validación", status_code=403)


@router.post("/webhook")
async def handle_messages(request: Request):
    data = await request.json()

    try:
        value_data = data["entry"][0]["changes"][0]["value"]
        
        # Extract user profile name dynamically from contacts payload
        contacts = value_data.get("contacts")
        if contacts:
            profile_name = contacts[0].get("profile", {}).get("name")
            if profile_name:
                config.TEMPLATE_USER_NAME = profile_name
                logger.info(f"Updated dynamic TEMPLATE_USER_NAME: {profile_name}")

        messages = value_data.get("messages")
        if not messages:
            return Response(content="EVENT_RECEIVED", status_code=200)

        message = messages[0]
        number = message["from"]
        message_id = message["id"]
        conversation_id = get_or_create_conversation(number)

        if not register_message_id(message_id, number):
            return Response(content="EVENT_RECEIVED", status_code=200)

        # Parse message type and body safely
        msg_type = message.get("type", "text")
        if msg_type == "text":
            text = message.get("text", {}).get("body", "")
        elif msg_type == "button":
            button_data = message.get("button", {})
            text = button_data.get("payload") or button_data.get("text", "")
        else:
            text = ""

        logger.info(f"Mensaje de {number} (tipo {msg_type}): {text}")

        # Check for button confirmation / rejection flow
        if msg_type == "button":
            button_payload = text.strip().lower()
            if button_payload in {"confirmar", "confirm"}:
                reminder = get_latest_pending_creation(number)
                if reminder:
                    update_reminder_status(reminder["id"], "pending")
                    try:
                        scheduled_utc = datetime.fromisoformat(reminder["scheduled_at"])
                        colombia_tz = timezone(timedelta(hours=-5))
                        scheduled_local = scheduled_utc.astimezone(colombia_tz).strftime("%I:%M %p")
                    except Exception:
                        scheduled_local = reminder["scheduled_at"]
                    respuesta = f"¡Excelente! Tu recordatorio sobre '{reminder['description']}' ha sido programado para las {scheduled_local}."
                else:
                    respuesta = "No encontré ningún recordatorio pendiente de confirmación."

                mark_as_read(message_id)
                log_message(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    wa_number=number,
                    direction="in",
                    body=f"[Botón: {text}]",
                )
                send_message(number, respuesta)
                log_message(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    wa_number=number,
                    direction="out",
                    body=respuesta,
                    model_id="system_button_action",
                )
                return Response(content="EVENT_RECEIVED", status_code=200)

            elif button_payload in {"rechazar", "reject"}:
                reminder = get_latest_pending_creation(number)
                if reminder:
                    update_reminder_status(reminder["id"], "cancelled")
                    respuesta = f"Listo, he cancelado la creación del recordatorio: '{reminder['description']}'."
                else:
                    respuesta = "No encontré ningún recordatorio pendiente de confirmación."

                mark_as_read(message_id)
                log_message(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    wa_number=number,
                    direction="in",
                    body=f"[Botón: {text}]",
                )
                send_message(number, respuesta)
                log_message(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    wa_number=number,
                    direction="out",
                    body=respuesta,
                    model_id="system_button_action",
                )
                return Response(content="EVENT_RECEIVED", status_code=200)

        # Standard message flow
        mark_as_read(message_id)
        log_message(
            conversation_id=conversation_id,
            message_id=message_id,
            wa_number=number,
            direction="in",
            body=text,
        )

        respuesta, token_usage, model_id = _invoke_agent(text, conversation_id, number)
        send_message(number, respuesta)
        log_message(
            conversation_id=conversation_id,
            message_id=message_id,
            wa_number=number,
            direction="out",
            body=respuesta,
            model_id=model_id,
            prompt_tokens=token_usage.get("input_tokens"),
            completion_tokens=token_usage.get("output_tokens"),
            total_tokens=token_usage.get("total_tokens"),
        )

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")

    return Response(content="EVENT_RECEIVED", status_code=200)
