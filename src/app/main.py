import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv
import uvicorn
from llm.openai import invoke

load_dotenv()
app = FastAPI()

TOKEN = os.getenv("ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")


@app.get("/webhook")
async def verify_webhook(request: Request):
    # Extraer parámetros de la URL
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # Verificar si el modo es 'subscribe' y el token coincide
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("¡Validación exitosa!")
        # Retornamos el challenge como texto plano
        # El header 'ngrok-skip-browser-warning' evita que Meta choque con la publicidad de ngrok
        return Response(
            content=str(challenge), 
            media_type="text/plain",
            headers={"ngrok-skip-browser-warning": "true"}
        )
    
    print("Fallo en la validación: Token o modo incorrecto")
    return Response(content="Error de validación", status_code=403)

@app.post("/webhook")
async def handle_messages(request: Request):
    data = await request.json()
    
    try:
        # Navegamos el JSON de Meta para llegar al mensaje
        entry = data['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        
        if 'messages' in value:
            message = value['messages'][0]
            number = message['from']
            message_id = message['id']
            text = message['text']['body']

            print(f"Mensaje recibido de {number}: {text}")

            marcar_como_leido(message_id)
            respuesta = invoke(text)
            enviar_mensaje(number, respuesta)
            
        return Response(content="EVENT_RECEIVED", status_code=200)
    except Exception as e:
        return Response(content="EVENT_RECEIVED", status_code=200)

def marcar_como_leido(message_id):
    url = f"https://graph.facebook.com/v25.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def enviar_mensaje(to, text):
    url = f"https://graph.facebook.com/v25.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Mantén tu @app.get("/webhook") de verificación aquí abajo...
if __name__ == "__main__":
    # Corremos en el puerto 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)