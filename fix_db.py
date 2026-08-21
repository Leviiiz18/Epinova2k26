"""
Fix script:
1. Deduplicate modules_collection (keeps first occurrence, drops the rest)
2. Delete all 3rd-year chunks from modules_collection that match old file paths
3. Move the 136 new study_buddy_syllabus chunks into modules_collection
4. Drop the now-empty study_buddy_syllabus collection
"""
import sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import load_dotenv
load_dotenv()
import psycopg

conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# ── 1. Get collection UUIDs ────────────────────────────────────────────────────
cur.execute("SELECT uuid, name FROM langchain_pg_collection;")
cols = {row[1]: row[0] for row in cur.fetchall()}
MC  = cols.get('modules_collection')
SBS = cols.get('study_buddy_syllabus')
print(f"modules_collection     uuid: {MC}")
print(f"study_buddy_syllabus   uuid: {SBS}")

# ── 2. Deduplicate modules_collection (keep lowest uuid per document text) ─────
print("\n[1/4] Deduplicating modules_collection...")
cur.execute("""
    DELETE FROM langchain_pg_embedding
    WHERE collection_id = %s
      AND id NOT IN (
          SELECT MIN(id)
          FROM langchain_pg_embedding
          WHERE collection_id = %s
          GROUP BY LEFT(document, 200)
      )
    RETURNING id;
""", [MC, MC])
removed = cur.fetchall()
conn.commit()
print(f"  Removed {len(removed)} duplicate chunks from modules_collection.")

# ── 3. Remove old 3rd-year chunks from modules_collection (old file paths) ─────
print("\n[2/4] Removing old 3rd-year chunks from modules_collection...")
cur.execute("""
    DELETE FROM langchain_pg_embedding
    WHERE collection_id = %s
      AND (
        cmetadata->>'source' LIKE '%%3rd year%%'
        OR cmetadata->>'source' LIKE '%%3rd%%year%%'
      )
    RETURNING id;
""", [MC])
old3rd = cur.fetchall()
conn.commit()
print(f"  Removed {len(old3rd)} old 3rd-year chunks from modules_collection.")

# ── 4. Move study_buddy_syllabus chunks INTO modules_collection ────────────────
if SBS:
    print("\n[3/4] Moving study_buddy_syllabus chunks into modules_collection...")
    cur.execute("""
        UPDATE langchain_pg_embedding
        SET collection_id = %s
        WHERE collection_id = %s
        RETURNING id;
    """, [MC, SBS])
    moved = cur.fetchall()
    conn.commit()
    print(f"  Moved {len(moved)} chunks to modules_collection.")

    # ── 5. Drop the now-empty study_buddy_syllabus collection ─────────────────
    print("\n[4/4] Dropping study_buddy_syllabus collection...")
    cur.execute("DELETE FROM langchain_pg_collection WHERE uuid = %s;", [SBS])
    conn.commit()
    print("  Dropped study_buddy_syllabus collection.")
else:
    print("\n[3/4] study_buddy_syllabus not found - nothing to move.")

# ── Final count check ──────────────────────────────────────────────────────────
print("\n=== FINAL STATE ===")
cur.execute("""
    SELECT c.name, COUNT(*) as chunks
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
    GROUP BY c.name ORDER BY chunks DESC;
""")
for r in cur.fetchall():
    print(f"  {r[0]!r}: {r[1]} chunks")

cur.close()
conn.close()
print("\nDone. All data is now in modules_collection, deduped, with fresh 3rd year data.")
