import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

def init_db():
    conn = psycopg.connect(DB_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    # Enable pgvector explicitly
    cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    
    # Read schema.sql
    with open("schema.sql", "r") as f:
        schema_sql = f.read()
        
    cursor.execute(schema_sql)
    print("Database schema and vector extension initialized successfully.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_db()
