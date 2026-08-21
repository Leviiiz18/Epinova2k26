import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM pg_constraint
            WHERE conname = 'doubts_student_rawquery_unique'
        """)
        exists = cur.fetchone()[0]
        if not exists:
            cur.execute("""
                ALTER TABLE doubts
                ADD CONSTRAINT doubts_student_rawquery_unique
                UNIQUE (student_id, raw_query)
            """)
            print("Unique constraint (student_id, raw_query) added — no more duplicate doubts.")
        else:
            print("Constraint already exists — all good.")
    conn.commit()
