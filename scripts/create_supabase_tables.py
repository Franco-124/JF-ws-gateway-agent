import os
import socket
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import psycopg
from dotenv import load_dotenv


SCHEMA_SQL = """
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

create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  wa_number text not null,
  status text not null check (status in ('open','closed')),
  closed_reason text,
  created_at timestamptz default now(),
  closed_at timestamptz
);

create index if not exists conversations_wa_status_idx
  on conversations (wa_number, status, created_at);

create table if not exists message_dedup (
  message_id text primary key,
  wa_number text not null,
  created_at timestamptz default now()
);

create index if not exists message_dedup_created_at_idx
  on message_dedup (created_at);
"""


def main() -> int:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL no esta definido.")
        return 1

    parsed = urlparse(database_url)
    query = dict(parse_qsl(parsed.query))
    query.pop("pgbouncer", None)
    query.setdefault("sslmode", "require")
    database_url = urlunparse(parsed._replace(query=urlencode(query)))

    hostaddr = None
    if parsed.hostname:
        try:
            infos = socket.getaddrinfo(parsed.hostname, None, family=socket.AF_INET)
            if infos:
                hostaddr = infos[0][4][0]
        except socket.gaierror:
            hostaddr = None

    try:
        with psycopg.connect(database_url, hostaddr=hostaddr, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            conn.commit()
    except Exception as exc:
        print("ERROR: No se pudo crear el schema en Supabase.")
        print(str(exc))
        return 1

    print("OK: Tablas creadas o ya existentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
