# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ws-gateway** is a WhatsApp-to-ClickUp gateway. It receives WhatsApp messages via webhook, runs a LangGraph agent (OpenAI GPT-4.1-mini) that can perform ClickUp task CRUD operations, and sends the response back via the Facebook Graph API. All interactions are persisted in Supabase (PostgreSQL).

## Development Commands

**Package manager:** `uv`

```bash
# Install dependencies
uv sync

# Run the server locally
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir src

# Run the database setup script (creates Supabase tables)
uv run python scripts/create_supabase_tables.py
```

**Docker:**
```bash
docker build -t ws-gateway .
docker run -p 8000:8000 --env-file .env ws-gateway
```

The server listens on `PORT` env var (default 8000). Python 3.13 is required.

## Architecture

### Request Flow

```
WhatsApp webhook POST → webhook.py
  → message_dedup (skip if duplicate)
  → get_or_create_conversation (Supabase)
  → log_message (direction="in")
  → fetch_conversation_messages (last 2 in + 2 out for context)
  → agent/graph.py (LangGraph ReAct agent)
      → tools.py (ClickUp API: get/create/update/delete tasks, close_conversation)
  → log_message (direction="out", with token usage)
  → whatsapp/client.py → send_message (Facebook Graph API)
```

### Key Modules

- **`src/agent/graph.py`** — LangGraph `StateGraph` with two nodes: `agent` (LLM call) and `tools` (tool execution). Entry point for all AI logic.
- **`src/agent/tools.py`** — Six `@tool`-decorated functions wrapping ClickUp REST API. Each raises `ClickUpError` with Spanish user-facing messages on failure.
- **`src/agent/prompt.py`** — System prompt defining the "Lupita" persona (Colombian Spanish, formal "usted").
- **`src/agent/state.py`** — `AgentState` TypedDict: `messages`, `token_usage`, `model_id`, `conversation_id`.
- **`src/storage/`** — Five modules covering Supabase client singleton, conversation lifecycle, message logging, conversation history fetching, and deduplication (24h window via `message_dedup` table).
- **`src/config.py`** — Single source of truth for all env var reads.

### Database Tables (Supabase/PostgreSQL)

| Table | Purpose |
|-------|---------|
| `conversations` | One row per WhatsApp number session; status `open`/`closed` |
| `message_logs` | Every inbound/outbound message with token usage metrics |
| `message_dedup` | Prevents reprocessing; rows expire after 24h |

### API Endpoints

```
GET  /webhook   — Webhook verification (hub.verify_token check)
POST /webhook   — Inbound WhatsApp message processing (always returns 200)
```

## Required Environment Variables

Defined in `src/config.py` and loaded from `.env`:

| Variable | Purpose |
|----------|---------|
| `ACCESS_TOKEN` | WhatsApp / Facebook Graph API bearer token |
| `VERIFY_TOKEN` | Webhook verification secret |
| `PHONE_ID` | WhatsApp Business Phone Number ID |
| `FACEBOOK_BASE_URL` | Meta Graph API base URL |
| `OPENAI_API_KEY` | OpenAI key (model: `gpt-4.1-mini`) |
| `CLICK_UP_API_TOKEN` | ClickUp personal API token |
| `CLICK_UP_BASE_URL` | ClickUp API base URL |
| `CLICKUP_LIST_ID` | Default ClickUp list ID for task creation |
| `SUPABASE_URL` | Supabase REST endpoint |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `DATABASE_URL` | PostgreSQL connection string (for direct psycopg queries) |

## Design Decisions

- **Deduplication** uses a PostgreSQL unique constraint on `message_dedup.message_id`; a `23505` integrity error is caught to detect duplicates (no separate SELECT query).
- **Conversation history** is capped at 2 messages per direction (4 messages total) when building LLM context.
- **ClickUp tools** use `httpx` with a 15s timeout; errors are surfaced to the LLM as structured `ClickUpError` strings in Spanish.
- **`close_conversation_tool`** is a LangGraph tool that updates conversation status in Supabase — the agent decides when to close a conversation.
