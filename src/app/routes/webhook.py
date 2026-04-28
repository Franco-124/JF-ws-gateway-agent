import logging
from fastapi import APIRouter, Request, Response
from agent.graph import graph
from whatsapp.client import send_message, mark_as_read
from storage.conversation_log import log_message
from storage.conversation_history import fetch_conversation_messages
from storage.message_dedup import register_message_id
from storage.conversations import get_or_create_conversation
from config import VERIFY_TOKEN

router = APIRouter()
logger = logging.getLogger(__name__)


def _invoke_agent(message: str, conversation_id: str) -> tuple[str, dict, str]:
    history = fetch_conversation_messages(conversation_id)
    prior_messages = [
        {"role": "user" if item["direction"] == "in" else "assistant", "content": item["body"]}
        for item in history
        if item.get("direction") in {"in", "out"}
    ]
    payload = {"messages": prior_messages + [{"role": "user", "content": message}]}
    result = graph.invoke({**payload, "conversation_id": conversation_id})
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

    if mode == "subscribe" and token == VERIFY_TOKEN:
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
        messages = data["entry"][0]["changes"][0]["value"].get("messages")
        if not messages:
            return Response(content="EVENT_RECEIVED", status_code=200)

        message = messages[0]
        number = message["from"]
        message_id = message["id"]
        text = message["text"]["body"]
        conversation_id = get_or_create_conversation(number)

        if not register_message_id(message_id, number):
            return Response(content="EVENT_RECEIVED", status_code=200)

        logger.info(f"Mensaje de {number}: {text}")

        mark_as_read(message_id)
        log_message(
            conversation_id=conversation_id,
            message_id=message_id,
            wa_number=number,
            direction="in",
            body=text,
        )

        respuesta, token_usage, model_id = _invoke_agent(text, conversation_id)
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
