import os
import glob
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader, UnstructuredPowerPointLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
CONNECTION_STRING = DB_URL.replace("postgresql://", "postgresql+psycopg://")

def ingest_docs():
    data_dir = "data"
    all_docs = []
    
    # Supported file extensions
    pdf_files = glob.glob(os.path.join(data_dir, "**", "*.pdf"), recursive=True)
    ppt_files = glob.glob(os.path.join(data_dir, "**", "*.pptx"), recursive=True)
    txt_files = glob.glob(os.path.join(data_dir, "**", "*.txt"), recursive=True)
    
    files_to_process = pdf_files + ppt_files + txt_files

    if not files_to_process:
        print("No documents found in the data directory.")
        return

    for file in files_to_process:
        print(f"Processing {file}...")
        try:
            if file.lower().endswith(".pdf"):
                loader = PyPDFLoader(file)
            elif file.lower().endswith(".pptx"):
                loader = UnstructuredPowerPointLoader(file)
            elif file.lower().endswith(".txt"):
                loader = TextLoader(file, encoding='utf-8')
            else:
                continue

            docs = loader.load()
            all_docs.extend(docs)
        except Exception as e:
            print(f"Error processing {file}: {e}")

    if not all_docs:
        print("No text extracted from any documents.")
        return

    print(f"Extracted {len(all_docs)} document pages/slides. Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(all_docs)
    
    print(f"Created {len(chunks)} chunks. Storing in Postgres Vector DB...")

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="modules_collection",
        connection=CONNECTION_STRING,
        use_jsonb=True,
    )
    
    vectorstore.add_documents(chunks)
    print("Ingestion complete!")

if __name__ == "__main__":
    ingest_docs()
