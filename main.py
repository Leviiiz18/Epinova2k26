import os
import psycopg
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.getenv("DATABASE_URL")
CONNECTION_STRING = DB_URL.replace("postgresql://", "postgresql+psycopg://")

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

try:
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="modules_collection",
        connection=CONNECTION_STRING,
        use_jsonb=True,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
except Exception as e:
    print(f"Error initializing PGVector: {e}")
    retriever = None

llm = ChatOpenAI(
    model="google/gemini-2.5-flash",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    max_tokens=1000,
)

system_prompt = (
    "You are an AI teaching assistant answering student doubts at night. "
    "Use the following pieces of retrieved context from the course curriculum to answer the student's question. "
    "If you don't know the answer based on the context, just say that you don't know. "
    "Keep your answer clear, educational, and structured.\n\n"
    "Context:\n{context}"
)
prompt = PromptTemplate.from_template(system_prompt + "\n\nQuestion: {input}\nAnswer:")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

if retriever:
    rag_chain = (
        {"context": retriever | format_docs, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
else:
    rag_chain = None

class DoubtRequest(BaseModel):
    student_id: str
    title: str
    raw_query: str

@app.post("/api/ask")
async def ask_doubt(request: DoubtRequest):
    if not rag_chain:
        return {"status": "error", "message": "RAG system not initialized."}

    # Generate embedding for the raw query to do semantic search
    try:
        query_embedding = embeddings.embed_query(request.raw_query)
        
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Search for an existing relevant doubt (cosine distance < 0.25) that has an answer
                cur.execute(
                    """
                    SELECT d.id, d.title, a.content, a.verification_state
                    FROM doubts d
                    JOIN answers a ON a.doubt_id = d.id
                    WHERE d.embedding IS NOT NULL
                    ORDER BY d.embedding <=> %s::vector
                    LIMIT 1
                    """,
                    (query_embedding,)
                )
                match = cur.fetchone()
                
                # Check if we got a match that is close enough (in a real system we'd check the distance score)
                # But since this is a quick MVP, let's just do the search and assume if it returns, we check distance.
                # Actually, pgvector order by `<=>` returns distance. We can retrieve the distance.
                cur.execute(
                    """
                    SELECT d.id, a.content, a.verification_state, (d.embedding <=> %s::vector) as distance
                    FROM doubts d
                    JOIN answers a ON a.doubt_id = d.id
                    WHERE d.embedding IS NOT NULL
                    ORDER BY distance
                    LIMIT 1
                    """,
                    (query_embedding,)
                )
                match = cur.fetchone()
                
                if match and match[3] < 0.20:
                    # Found a sufficiently similar existing answer!
                    return {
                        "status": "success",
                        "answer": f"**[Retrieved Existing Answer - {match[2]}]**\n\n{match[1]}",
                        "is_faculty_validated": match[2] == 'FACULTY_VERIFIED',
                        "verification_state": match[2],
                        "message": "Retrieved an existing verified answer from semantic search!"
                    }
                    
                # Check if there are very less users (threshold = 5)
                cur.execute("SELECT COUNT(*) FROM users")
                user_count = cur.fetchone()[0]
                
                if user_count >= 5:
                    print("Many users online. Forwarding to peer mentors instead of RAG...")
                    # Insert the new doubt with its embedding, no AI answer generated
                    cur.execute(
                        "INSERT INTO doubts (student_id, title, raw_query, status, embedding) VALUES (%s, %s, %s, %s, %s::vector) RETURNING id",
                        (request.student_id, request.title, request.raw_query, "Open", query_embedding)
                    )
                    doubt_id = cur.fetchone()[0]
                    conn.commit()
                    return {
                        "status": "success",
                        "answer": "Your doubt has been forwarded to peer mentors as there are many active users currently available to help you!",
                        "is_faculty_validated": False,
                        "verification_state": "PENDING_PEER",
                        "message": "Forwarded to peers"
                    }

                # No existing answer found, and few users: fallback to RAG
                print("Few users online. Generating provisional answer via RAG...")
                answer_text = rag_chain.invoke(request.raw_query)
                
                # Insert the new doubt with its embedding
                cur.execute(
                    "INSERT INTO doubts (student_id, title, raw_query, status, embedding) VALUES (%s, %s, %s, %s, %s::vector) RETURNING id",
                    (request.student_id, request.title, request.raw_query, "In Review", query_embedding)
                )
                doubt_id = cur.fetchone()[0]
                
                # Ensure an AI User exists
                cur.execute("SELECT id FROM users WHERE email = 'ai@studybuddy.com'")
                ai_user = cur.fetchone()
                if not ai_user:
                    cur.execute("INSERT INTO roles (name) VALUES ('ai') ON CONFLICT DO NOTHING")
                    cur.execute("SELECT id FROM roles WHERE name = 'ai'")
                    role_row = cur.fetchone()
                    role_id = role_row[0] if role_row else None

                    cur.execute(
                        "INSERT INTO users (email, password_hash, full_name, role_id) VALUES (%s, %s, %s, %s) RETURNING id",
                        ("ai@studybuddy.com", "NO_PASSWORD", "AI Teaching Assistant", role_id)
                    )
                    ai_user_id = cur.fetchone()[0]
                else:
                    ai_user_id = ai_user[0]

                # Insert Answer as AI_REVIEWED
                cur.execute(
                    "INSERT INTO answers (doubt_id, author_id, content, is_faculty_validated, verification_state) VALUES (%s, %s, %s, %s, %s)",
                    (doubt_id, ai_user_id, answer_text, False, 'AI_REVIEWED')
                )
                
            conn.commit()
            
    except Exception as e:
        print(f"Error during ask_doubt processing: {e}")
        # Fallback just in case DB fails but we can still ask Gemini
        if 'answer_text' not in locals():
            answer_text = rag_chain.invoke(request.raw_query)
            
        return {
            "status": "partial_success",
            "answer": answer_text,
            "verification_state": "AI_PENDING",
            "message": f"Provisional answer generated via RAG, but DB save failed: {e}"
        }
    
    return {
        "status": "success",
        "answer": answer_text,
        "is_faculty_validated": False,
        "verification_state": "AI_REVIEWED",
        "message": "Provisional answer generated via RAG and set to AI_REVIEWED state."
    }

@app.get("/api/doubts")
async def get_doubts():
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Fetch doubts and their latest answers
                cur.execute("""
                    SELECT d.id, d.title, d.raw_query, d.difficulty, d.status, d.created_at,
                           a.content, a.verification_state, a.author_id, u.full_name as author_name
                    FROM doubts d
                    LEFT JOIN answers a ON a.doubt_id = d.id
                    LEFT JOIN users u ON a.author_id = u.id
                    ORDER BY d.created_at DESC
                """)
                rows = cur.fetchall()
                
                doubts_dict = {}
                for row in rows:
                    doubt_id = str(row[0])
                    if doubt_id not in doubts_dict:
                        doubts_dict[doubt_id] = {
                            "id": doubt_id,
                            "title": row[1],
                            "rawQuery": row[2],
                            "difficulty": row[3],
                            "status": row[4],
                            "createdAt": str(row[5]),
                            "concept": "General", # Dummy until we join concepts
                            "subject": "All", # Dummy
                            "answers": []
                        }
                    
                    if row[6]: # If answer content exists
                        doubts_dict[doubt_id]["answers"].append({
                            "content": row[6],
                            "verification_state": row[7],
                            "authorName": row[9] or "AI Assistant",
                            "isAiVerified": row[7] in ['AI_REVIEWED', 'FACULTY_VERIFIED'],
                            "isFacultyVerified": row[7] == 'FACULTY_VERIFIED'
                        })
                
                return list(doubts_dict.values())
    except Exception as e:
        print(f"Error fetching doubts: {e}")
        return []
