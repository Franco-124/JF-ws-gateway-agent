import os
import psycopg
from dotenv import load_dotenv

def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set.")
        return 1

    # SQL to update the constraint
    # We will find the check constraint name or just drop all check constraints on 'status' and add a new one.
    sql = """
    DO $$
    DECLARE
        r RECORD;
    BEGIN
        -- Find check constraints on column 'status' in table 'reminders' and drop them
        FOR r IN 
            SELECT conname 
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_attribute att ON att.attrelid = rel.oid AND att.attnum = ANY(con.conkey)
            WHERE rel.relname = 'reminders' 
              AND con.contype = 'c'
              AND att.attname = 'status'
        LOOP
            EXECUTE 'ALTER TABLE reminders DROP CONSTRAINT ' || quote_ident(r.conname);
            RAISE NOTICE 'Dropped constraint: %', r.conname;
        END LOOP;
    END $$;

    -- Add the new check constraint supporting 'pending_creation'
    ALTER TABLE reminders ADD CONSTRAINT reminders_status_check CHECK (
        status IN (
            'pending_creation',
            'pending',
            'awaiting_confirmation',
            'awaiting_followup_confirmation',
            'confirmed',
            'cancelled',
            'closed_unconfirmed'
          )
    );
    """

    print("Running migration to update 'status' check constraint in reminders table...")
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        print("Migration successful: status constraint updated.")
        return 0
    except Exception as e:
        print(f"Migration failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
