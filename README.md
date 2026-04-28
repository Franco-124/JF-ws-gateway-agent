
# ws-gateway

Gateway para WhatsApp que recibe mensajes por webhook, ejecuta un agente LLM con
tools de ClickUp y responde al usuario por la API de WhatsApp.

## Que hace

- Valida el webhook de WhatsApp (GET /webhook)
- Procesa mensajes entrantes (POST /webhook)
- Invoca un agente (LangGraph + OpenAI) con herramientas de ClickUp
- Envia respuestas al usuario por WhatsApp

## Arquitectura

- API: FastAPI en `src/app/main.py` y rutas en `src/app/routes/webhook.py`
- Agente: LangGraph en `src/agent/graph.py` con prompt en `src/agent/prompt.py`
- Tools: ClickUp CRUD en `src/agent/tools.py`
- WhatsApp client: `src/whatsapp/client.py`
- Config: `src/config.py` carga variables desde `.env`

## Requisitos

- Python 3.13
- uv (recomendado) o un entorno equivalente

## Variables de entorno

Crear un archivo `.env` en la raiz con:

```
ACCESS_TOKEN=...
VERIFY_TOKEN=...
PHONE_ID=...
FACEBOOK_BASE_URL=https://graph.facebook.com/v25.0
OPENAI_API_KEY=...
CLICK_UP_API_TOKEN=...
CLICK_UP_BASE_URL=https://api.clickup.com/api/v2
CLICKUP_LIST_ID=...
SUPABASE_SERVICE_KEY=...
SUPABASE_URL=...
DATABASE_URL=...
```

Notas:

- `.env` ya esta en `.gitignore`
- Las credenciales no deben subirse a git

## Ejecutar en local (uv)

```
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir src
```

## Ejecutar con Docker

```
docker build -t ws-gateway .
docker run -p 8000:8000 --env-file .env ws-gateway
```

## Endpoints

- GET `/webhook` : verificacion del webhook de WhatsApp
- POST `/webhook` : recibe mensajes, ejecuta el agente y responde

## Supabase

Se registra el historial en la tabla `message_logs` y se guarda el consumo de tokens
del modelo por cada respuesta. El historial se usa para reconstruir el contexto.

Schema sugerido para `message_logs`:

```
create table if not exists message_logs (
  id uuid primary key default gen_random_uuid(),
  conversation_id text not null,
  message_id text not null,
  wa_number text not null,
  direction text not null check (direction in ('in','out')),
  body text not null,
  model_id text,
  prompt_tokens integer,
  completion_tokens integer,
  total_tokens integer,
  provider text default 'openai',
  created_at timestamptz default now()
);

create index if not exists message_logs_conversation_id_idx
  on message_logs (conversation_id, created_at);
```

## Flujo principal

1. WhatsApp envia el mensaje al webhook.
2. El server marca el mensaje como leido.
3. El agente genera la respuesta y puede llamar tools de ClickUp.
4. Se responde al usuario por WhatsApp.
