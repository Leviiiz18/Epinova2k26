import sys, os
# Fix Windows console unicode issues
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
import psycopg
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

DB_URL = os.environ.get("DATABASE_URL", "")
# PGVector with langchain_postgres needs psycopg (v3) driver prefix
# Convert postgres:// -> postgresql+psycopg://
PGVECTOR_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://").replace("postgres://", "postgresql+psycopg://")
COLLECTION_NAME = "study_buddy_syllabus"
DATA_DIR = Path("data/3rd year")

print("Loading embeddings model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# -- Step 1: Delete existing 3rd-year chunks --------------------------------
print("\n[1/3] Connecting to delete old 3rd-year chunks...")
conn = psycopg.connect(DB_URL)
cur = conn.cursor()
cur.execute("SELECT uuid FROM langchain_pg_collection WHERE name = %s;", [COLLECTION_NAME])
row = cur.fetchone()
if not row:
    print("  WARNING: Collection not found - will be created fresh on upsert.")
    collection_uuid = None
else:
    collection_uuid = row[0]
    cur.execute("""
        DELETE FROM langchain_pg_embedding
        WHERE collection_id = %s
          AND (
            cmetadata->>'year' = '3rd year'
            OR cmetadata->>'source' LIKE '%3rd year%'
            OR cmetadata->>'source' LIKE '%3rd%year%'
          )
        RETURNING uuid;
    """, [collection_uuid])
    deleted = cur.fetchall()
    print(f"  Deleted {len(deleted)} old 3rd-year chunks.")
    conn.commit()
cur.close()
conn.close()

# -- Step 2: Discover PDFs -------------------------------------------------
pdf_map = []
for subject_dir in sorted(DATA_DIR.iterdir()):
    if not subject_dir.is_dir():
        continue
    subject = subject_dir.name
    for unit_dir in sorted(subject_dir.iterdir()):
        if not unit_dir.is_dir():
            continue
        unit = unit_dir.name
        for pdf in sorted(unit_dir.glob("*.pdf")):
            pdf_map.append((pdf, subject, unit))

print(f"\n[2/3] Found {len(pdf_map)} PDFs to ingest:")
for pdf, subj, unit in pdf_map:
    print(f"  [{subj} / {unit}] {pdf.name}")

# -- Step 3: Load, chunk, and ingest via PGVector --------------------------
print(f"\n[3/3] Chunking PDFs and upserting into PGVector...")
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
all_docs = []

for pdf_path, subject, unit in pdf_map:
    print(f"  Processing: {pdf_path.name} ...", end=" ", flush=True)
    try:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        chunks = splitter.split_documents(pages)
        for chunk in chunks:
            chunk.metadata.update({
                "year": "3rd year",
                "subject": subject,
                "unit": unit,
                "source": str(pdf_path),
                "filename": pdf_path.name,
            })
        all_docs.extend(chunks)
        print(f"{len(chunks)} chunks OK")
    except Exception as e:
        print(f"ERROR: {e}")

print(f"\n  Total chunks ready: {len(all_docs)}")

if all_docs:
    from langchain_postgres import PGVector
    print("  Upserting to PGVector (psycopg v3 driver)...")
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=PGVECTOR_URL,
        use_jsonb=True,
    )
    vector_store.add_documents(all_docs)
    print("  Done! All 3rd-year chunks ingested successfully.")
else:
    print("  No documents to ingest.")

print("\nRe-ingestion complete.")
print("Subjects ingested:")
print("  AI  U1 -> Genetic Algorithms")
print("  AI  U2 -> Heuristic Search + A* Algorithm")
print("  DIP U1 -> Fundamental Steps, Image Acquisition, Image System, Introduction, Pixel Relationships, Sampling & Quantization")
print("  DIP U2 -> DIP Unit 2 Part 2")
