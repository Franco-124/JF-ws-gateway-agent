import logging
import requests
from config import ACCESS_TOKEN, PHONE_ID, FACEBOOK_BASE_URL

logger = logging.getLogger(__name__)

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def send_message(to: str, text: str) -> dict:
    url = f"{FACEBOOK_BASE_URL}/{PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    response = requests.post(url, json=payload, headers=_headers())
    logger.info(f"send_message to={to} status={response.status_code}")
    return response.json()


def mark_as_read(message_id: str) -> dict:
    url = f"{FACEBOOK_BASE_URL}/{PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    response = requests.post(url, json=payload, headers=_headers())
    logger.info(f"mark_as_read id={message_id} status={response.status_code}")
    return response.json()
