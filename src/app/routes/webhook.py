import logging
from fastapi import APIRouter, Request, Response
from agent.graph import graph
from whatsapp.client import send_message, mark_as_read
from config import VERIFY_TOKEN

router = APIRouter()
logger = logging.getLogger(__name__)


def _invoke_agent(message: str) -> str:
    result = graph.invoke({"messages": [{"role": "user", "content": message}]})
    return result["messages"][-1].content


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

        logger.info(f"Mensaje de {number}: {text}")

        mark_as_read(message_id)
        respuesta = _invoke_agent(text)
        send_message(number, respuesta)

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")

    return Response(content="EVENT_RECEIVED", status_code=200)
