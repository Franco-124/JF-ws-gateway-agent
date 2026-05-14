# Design: Smart Reminder & Follow-up

## Overview
Se agregan tres capas al gateway existente: persistencia (`reminders` table + módulo de storage), scheduler (APScheduler integrado al lifespan de FastAPI), y lógica de contexto en el webhook para detectar reminders pendientes antes de invocar al agente. El agente recibe cuatro tools nuevas: `create_reminder`, `cancel_reminder`, `confirm_reminder`, y `list_reminders`.

## Components

### New / Modified Files
| File | Role | Change type |
|------|------|-------------|
| `scripts/create_supabase_tables.py` | Agrega DDL de tabla `reminders` | Modify |
| `src/storage/reminders.py` | CRUD de reminders contra Supabase | Create |
| `src/scheduler.py` | APScheduler: dispara reminders y cierra follow-ups expirados | Create |
| `src/agent/tools.py` | Agrega `create_reminder`, `cancel_reminder`, `confirm_reminder`, `list_reminders` | Modify |
| `src/agent/prompt.py` | Instrucciones para manejo de reminders | Modify |
| `src/app/main.py` | Arranca/detiene el scheduler en el lifespan de FastAPI | Modify |
| `src/app/routes/webhook.py` | Inyecta contexto de reminders pendientes antes de llamar al agente | Modify |
| `pyproject.toml` | Agrega dependencia `apscheduler>=3.10` | Modify |

### Key Abstractions

**`src/storage/reminders.py`**
- `create_reminder(wa_number, description, scheduled_at_utc, follow_up_at_utc) -> str` — inserta fila, retorna `id`
- `get_pending_reminders(wa_number) -> list[dict]` — filas en `awaiting_confirmation` o `awaiting_followup_confirmation`
- `get_due_reminders() -> list[dict]` — filas `pending` con `scheduled_at <= now()`
- `get_due_followups() -> list[dict]` — filas `awaiting_confirmation` con `follow_up_at <= now()` y `follow_up_sent_at IS NULL`
- `get_expired_reminders() -> list[dict]` — filas `awaiting_*` cuyo último envío supera 10 minutos
- `update_reminder_status(reminder_id, status, **extra_fields) -> None`
- `cancel_reminder(reminder_id) -> None`
- `confirm_reminder(reminder_id) -> None`
- `list_active_reminders(wa_number) -> list[dict]`

**`src/scheduler.py`**
- `build_scheduler(wa_number) -> AsyncIOScheduler` — configura y retorna el scheduler con tres jobs:
  - `job_fire_reminders` — cada 60s: dispara reminders vencidos
  - `job_fire_followups` — cada 60s: envía follow-ups vencidos
  - `job_close_expired` — cada 60s: cierra reminders sin respuesta tras 10 min

### Data Flow

**Creación de reminder:**
1. Usuario escribe "Recuérdame X a las 3 PM, si no en 30 minutos"
2. Webhook invoca al agente normalmente
3. Agente llama `create_reminder(description, scheduled_at_iso_colombia, follow_up_minutes)`
4. Tool convierte hora Colombia → UTC, calcula `follow_up_at = scheduled_at_utc + follow_up_minutes`
5. Persiste fila `status=pending` en Supabase
6. Agente confirma al usuario con hora y follow-up

**Disparo del scheduler — primer aviso:**
1. `job_fire_reminders` detecta fila `pending` con `scheduled_at <= now()`
2. Llama `get_or_create_conversation(wa_number)`
3. Llama `send_message(wa_number, "¿Ya [description]?")`
4. Actualiza fila: `status=awaiting_confirmation`

**Disparo del scheduler — follow-up:**
1. `job_fire_followups` detecta fila `awaiting_confirmation` con `follow_up_at <= now()` y `follow_up_sent_at IS NULL`
2. Llama `send_message(wa_number, "¿Pudiste [description]?")`
3. Actualiza: `status=awaiting_followup_confirmation`, `follow_up_sent_at=now()`

**Cierre por timeout:**
1. `job_close_expired` detecta filas `awaiting_*` donde el último envío supera 10 minutos sin respuesta
2. Actualiza: `status=closed_unconfirmed`

**Respuesta del usuario:**
1. Mensaje entrante en webhook
2. Antes de invocar al agente: `get_pending_reminders(wa_number)`
3. Si existen reminders pendientes: se inyecta un `SystemMessage` extra con la lista de reminders activos y sus IDs
4. Agente interpreta la respuesta; si es confirmación llama `confirm_reminder(id)`, si es negación no hace nada (el scheduler cerrará por timeout)
5. Si hay múltiples reminders pendientes, el agente pregunta cuál antes de confirmar/cancelar

### API / Interface Contracts

```python
# src/agent/tools.py

@tool
def create_reminder(description: str, scheduled_at: str, follow_up_minutes: int) -> str:
    """
    Crea un reminder. scheduled_at en ISO 8601 hora Colombia (UTC-5), ej: "2025-05-14T15:00:00".
    follow_up_minutes: minutos después del disparo inicial para el follow-up.
    """

@tool
def cancel_reminder(reminder_id: str) -> str:
    """Cancela un reminder activo por su ID."""

@tool
def confirm_reminder(reminder_id: str) -> str:
    """Marca un reminder como completado cuando el usuario confirma la tarea."""

@tool
def list_reminders() -> str:
    """Lista los reminders activos (pending / awaiting_*) del usuario."""
```

```python
# src/storage/reminders.py (firmas clave)

def create_reminder(wa_number: str, description: str, scheduled_at_utc: datetime, follow_up_at_utc: datetime) -> str: ...
def get_pending_reminders(wa_number: str) -> list[dict]: ...
def get_due_reminders() -> list[dict]: ...
def get_due_followups() -> list[dict]: ...
def get_expired_reminders(timeout_minutes: int = 10) -> list[dict]: ...
def update_reminder_status(reminder_id: str, status: str, **extra_fields) -> None: ...
def list_active_reminders(wa_number: str) -> list[dict]: ...
```

### Edge Cases & Error Handling
- **Servidor reinicia con reminders `pending`**: APScheduler los detecta al volver; el job corre al startup.
- **`scheduled_at` ya pasó cuando el servidor vuelve**: Se dispara en el primer ciclo del job (≤60s).
- **Usuario cancela reminder ya en `awaiting_*`**: `cancel_reminder` actualiza status; el scheduler lo ignora en el próximo ciclo.
- **Múltiples reminders `awaiting_*` simultáneos**: El webhook inyecta todos como contexto; el agente pregunta cuál confirmar.
- **Hora ambigua sin AM/PM**: El agente pide aclaración antes de llamar `create_reminder`.
- **Error de red al enviar mensaje desde scheduler**: Se loguea el error; la fila no cambia de status y se reintenta en el próximo ciclo (60s).
- **`follow_up_minutes` no especificado**: El agente pregunta antes de crear el reminder.

## Open Questions for Implementation
- Ninguna.
