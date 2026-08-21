import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import load_dotenv
load_dotenv()
import psycopg

conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# 1. What collections exist?
print("=== COLLECTIONS ===")
cur.execute("SELECT uuid, name FROM langchain_pg_collection;")
cols = cur.fetchall()
for r in cols:
    print(f"  uuid={r[0]}  name={r[1]!r}")

# 2. Chunk count per collection
print("\n=== CHUNK COUNTS PER COLLECTION ===")
cur.execute("""
    SELECT c.name, COUNT(*) as chunks
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
    GROUP BY c.name ORDER BY chunks DESC;
""")
for r in cur.fetchall():
    print(f"  {r[0]!r}: {r[1]} chunks")

# 3. Sample metadata from modules_collection
print("\n=== SAMPLE METADATA from modules_collection (5 rows) ===")
cur.execute("""
    SELECT e.cmetadata, LEFT(e.document, 120)
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
    WHERE c.name = 'modules_collection'
    ORDER BY e.id DESC LIMIT 5;
""")
for r in cur.fetchall():
    print(f"  meta={r[0]}  doc={r[1]!r}")

# 4. Sample metadata from study_buddy_syllabus
print("\n=== SAMPLE METADATA from study_buddy_syllabus (5 rows) ===")
cur.execute("""
    SELECT e.cmetadata, LEFT(e.document, 120)
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
    WHERE c.name = 'study_buddy_syllabus'
    ORDER BY e.id DESC LIMIT 5;
""")
for r in cur.fetchall():
    print(f"  meta={r[0]}  doc={r[1]!r}")

# 5. Duplicate detection
print("\n=== DUPLICATE CHUNKS (same text, same collection) ===")
cur.execute("""
    SELECT LEFT(document, 80), collection_id, COUNT(*) as cnt
    FROM langchain_pg_embedding
    GROUP BY LEFT(document, 80), collection_id
    HAVING COUNT(*) > 1
    ORDER BY cnt DESC
    LIMIT 10;
""")
dups = cur.fetchall()
if dups:
    for r in dups:
        print(f"  [{r[2]}x] {r[0]!r}")
else:
    print("  No duplicates found.")

cur.close()
conn.close()
