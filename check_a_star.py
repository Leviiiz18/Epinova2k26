import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

conn = psycopg.connect(DATABASE_URL)
cur = conn.cursor()

# Check for A* or A-star
query = """
    SELECT document, cmetadata 
    FROM langchain_pg_embedding 
    WHERE document ILIKE '%A*%' 
       OR document ILIKE '%A star%'
       OR document ILIKE '%A-star%'
    LIMIT 5;
"""
cur.execute(query)
rows = cur.fetchall()

if rows:
    print(f"Found {len(rows)} matching chunks!")
    for i, row in enumerate(rows):
        print(f"\n--- Match {i+1} ---")
        print(f"Metadata: {row[1]}")
        doc_safe = row[0].encode('ascii', 'ignore').decode('ascii')
        print(f"Document: {doc_safe[:300]}...")
else:
    print("No chunks found for A*")
