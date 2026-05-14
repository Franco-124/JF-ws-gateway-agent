# Implementation Plan: Smart Reminder & Follow-up

## Tasks

- [x] **Task 1**: Agregar dependencia `apscheduler` — `pyproject.toml`
- [x] **Task 2**: Agregar DDL de tabla `reminders` — `scripts/create_supabase_tables.py`
- [x] **Task 3**: Crear módulo de storage para reminders — `src/storage/reminders.py`
- [x] **Task 4**: Crear el scheduler con los tres jobs — `src/scheduler.py`
- [x] **Task 5**: Agregar las cuatro tools al agente — `src/agent/tools.py`
- [x] **Task 6**: Actualizar el system prompt — `src/agent/prompt.py`
- [x] **Task 7**: Integrar scheduler al lifespan de FastAPI — `src/app/main.py`
- [x] **Task 8**: Inyectar contexto de reminders en el webhook — `src/app/routes/webhook.py`

## Execution Log

### Task 1 — apscheduler
Status: ✅ Done
Notes: `uv sync` instaló apscheduler 3.11.2 + tzlocal 5.3.1 como dependencia transitiva.

### Task 2 — DDL reminders
Status: ✅ Done
Notes: Tabla con 6 estados, dos índices (wa_number+status, scheduled_at filtrado por pending).

### Task 3 — storage/reminders.py
Status: ✅ Done
Notes: 8 funciones públicas cubriendo todo el ciclo de vida del reminder.

### Task 4 — scheduler.py
Status: ✅ Done
Notes: AsyncIOScheduler con 3 jobs cada 60s. Errores individuales no detienen el job completo.

### Task 5 — tools.py
Status: ✅ Done
Notes: 4 tools nuevas + close_conversation_tool. Se detectó que `config.WA_NUMBER` no existía → se agregó en config.py. Requiere variable de entorno `WA_NUMBER` en `.env`.

### Task 6 — prompt.py
Status: ✅ Done
Notes: Prompt enfocado en reminders: creación, confirmación, cancelación, cierre de conversación.

### Task 7 — main.py lifespan
Status: ✅ Done
Notes: Scheduler arranca en lifespan async; shutdown con wait=False para no bloquear el cierre.

### Task 8 — webhook.py + state.py + graph.py
Status: ✅ Done
Notes: Se extendió AgentState con `reminder_context: Optional[str]`. Graph inyecta el contexto como SystemMessage adicional. Webhook pasa `wa_number` a `_invoke_agent` para consultar reminders pendientes.
