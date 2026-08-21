import os
import json
import re
import psycopg
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Try importing LangChain & OpenRouter dependencies gracefully
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_postgres.vectorstores import PGVector
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except Exception as e:
    print(f"Warning: LangChain components not available: {e}")
    LANGCHAIN_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

dotenv_path = os.path.join(BASE_DIR, '.env')
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(BASE_DIR, 'env')
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI(title="StudyBuddy All-in-One Server", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)


# Mount Static Directories for Frontend Assets
if os.path.exists(os.path.join(BASE_DIR, "css")):
    app.mount("/css", StaticFiles(directory=os.path.join(BASE_DIR, "css")), name="css")
if os.path.exists(os.path.join(BASE_DIR, "js")):
    app.mount("/js", StaticFiles(directory=os.path.join(BASE_DIR, "js")), name="js")
if os.path.exists(os.path.join(BASE_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets")), name="assets")
if os.path.exists(os.path.join(BASE_DIR, "data")):
    app.mount("/data", StaticFiles(directory=os.path.join(BASE_DIR, "data")), name="data")

DB_URL = os.getenv("DATABASE_URL")
CONNECTION_STRING = DB_URL.replace("postgresql://", "postgresql+psycopg://") if DB_URL else ""

# Vector store & LLM Setup
embeddings = None
vectorstore = None
retriever = None
rag_chain = None
rag_chains_by_mode = {}

if LANGCHAIN_AVAILABLE and DB_URL:
    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = PGVector(
            embeddings=embeddings,
            collection_name="modules_collection",
            connection=CONNECTION_STRING,
            use_jsonb=True,
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    except Exception as e:
        print(f"Error initializing PGVector: {e}")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        try:
            llm = ChatOpenAI(
                model="google/gemini-2.5-flash",
                openai_api_base="https://openrouter.ai/api/v1",
                openai_api_key=api_key,
                max_tokens=1000,
                timeout=20,       # fail fast to the fallback instead of hanging the request
                max_retries=1,
            )
            # Shorter, capped generations per exam mode = faster round trip
            LLM_MAX_TOKENS = {"none": 700, "5m": 260, "10m": 550}

            # STRICT SYLLABUS GROUNDING: the previous prompt explicitly told the
            # model to "rely on your core expertise" whenever retrieval came up
            # empty/irrelevant — which is exactly how answers not backed by the
            # ingested course material (chunked via ingest.py into the
            # `modules_collection` pgvector store) could slip in. The model must
            # now ONLY answer from {context}; if that's not enough it must say
            # so verbatim so the app can show a clear "not in syllabus" message
            # instead of a guess.
            NOT_IN_SYLLABUS_TOKEN = "NOT_IN_SYLLABUS"
            NOT_IN_SYLLABUS_MSG = (
                "I couldn't find this topic in the ingested course syllabus / lecture material yet, "
                "so I won't guess at an answer. Please check with your faculty, or ask them to upload "
                "the relevant slides/notes (via ingest.py) so this can be answered from verified sources."
            )
            system_prompt = (
                "You are an academic assistant that answers ONLY using the official ingested course "
                "syllabus/lecture material provided below as Context. This context was chunked directly "
                "from faculty-uploaded slides and notes — treat it as the single source of truth.\n\n"
                "Context:\n{context}\n\n"
                "STRICT RULES (do not break these under any circumstance):\n"
                f"1. Use ONLY the Context above to answer. Do NOT use outside/general knowledge, even if "
                f"you personally know the answer, and even if the Context looks incomplete.\n"
                f"2. If the Context is empty or does not actually contain information relevant to the "
                f"question, respond with EXACTLY the single token `{NOT_IN_SYLLABUS_TOKEN}` and nothing else.\n"
                "3. Never invent facts, formulas, numbers, or examples that are not present in the Context.\n"
                "4. Stay strictly on the topic asked — do not pull in unrelated syllabus material just "
                "because it was retrieved alongside the relevant chunk.\n"
                "{exam_instructions}"
            )
            prompt = PromptTemplate.from_template(system_prompt + "\n\nQuestion: {input}\nAnswer:")
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            EXAM_INSTRUCTIONS = {
                "none": "",
                "5m": (
                    "5. EXAM MODE: Write this as a university '5-Mark' short answer. "
                    "Target ~80-120 words. Use a 1-line definition, 3-4 crisp bullet points "
                    "covering the core mechanism, and skip lengthy derivations or examples."
                ),
                "10m": (
                    "5. EXAM MODE: Write this as a university '10-Mark' long answer. "
                    "Target ~250-350 words. Structure it as: Definition/Intro, Working/Steps "
                    "(numbered), a small diagram description or example if relevant, "
                    "Advantages/Limitations or Common Misconceptions, and a short Conclusion."
                ),
            }

            class GroundedRagChain:
                """Retrieves syllabus context ourselves (instead of a blind
                retriever-pipe) so we can refuse to call the LLM at all when
                nothing was ingested for this topic — cheaper AND removes any
                chance of the model improvising from general knowledge."""
                def __init__(self, exam_mode):
                    instructions = EXAM_INSTRUCTIONS.get(exam_mode, "")
                    self.chain = prompt.partial(exam_instructions=instructions) | llm.bind(max_tokens=LLM_MAX_TOKENS.get(exam_mode, 700)) | StrOutputParser()

                def invoke(self, query):
                    docs = []
                    if retriever:
                        try:
                            docs = retriever.invoke(query)
                        except Exception as e:
                            print(f"Retrieval error: {e}")
                    if not docs:
                        return NOT_IN_SYLLABUS_MSG
                    context = format_docs(docs)
                    answer = self.chain.invoke({"context": context, "input": query})
                    if answer.strip().upper().startswith(NOT_IN_SYLLABUS_TOKEN):
                        return NOT_IN_SYLLABUS_MSG
                    return answer

            if retriever:
                rag_chain = GroundedRagChain("none")
                rag_chains_by_mode = {
                    "none": rag_chain,
                    "5m": GroundedRagChain("5m"),
                    "10m": GroundedRagChain("10m"),
                }
        except Exception as e:
            print(f"LLM chain init error: {e}")

# Database helper functions
def get_db_connection():
    if not DB_URL:
        raise Exception("DATABASE_URL environment variable is not set!")
    return psycopg.connect(DB_URL)

def run_query(query, params=None, commit=False, fetch_one=False, fetch_all=False):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
            
            result = None
            if fetch_one:
                row = cur.fetchone()
                if row and cur.description:
                    colnames = [desc[0] for desc in cur.description]
                    result = dict(zip(colnames, row))
            elif fetch_all:
                rows = cur.fetchall()
                if rows and cur.description:
                    colnames = [desc[0] for desc in cur.description]
                    result = [dict(zip(colnames, row)) for row in rows]
                else:
                    result = []
        conn.close()
        return result
    except Exception as e:
        print(f"Database Query Error: {e} for query: {query}")
        return None

# Taxonomy & Seed Data
TAXONOMY = [
    {
        "subjectName": "Computer Science",
        "topics": [
            {
                "topicName": "Algorithms",
                "concepts": [
                    {
                        "conceptName": "Binary Search",
                        "subConcept": "Sorted Array Requirement",
                        "difficulty": "Beginner",
                        "canonicalSummary": "Divide-and-conquer search requiring monotonic ordering.",
                        "misconception": "Binary search works on unsorted data",
                        "prerequisites": ["Arrays", "Monotonic Ordering"]
                    },
                    {
                        "conceptName": "Recursion",
                        "subConcept": "Base Case & Call Stack",
                        "difficulty": "Beginner",
                        "canonicalSummary": "Self-referencing function execution requiring terminal state.",
                        "misconception": "Recursion has no stopping condition and executes forever",
                        "prerequisites": ["Functions", "Conditionals"]
                    },
                    {
                        "conceptName": "Depth-First Search (DFS)",
                        "subConcept": "Graph Traversal with Call Stack",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "Graph search exploring deepest branch before backtracking.",
                        "misconception": "DFS can only be implemented recursively and fails on cyclic graphs",
                        "prerequisites": ["Recursion", "Stack Data Structure", "Graph Adjacency"]
                    }
                ]
            },
            {
                "topicName": "Neural Networks & Optimization",
                "concepts": [
                    {
                        "conceptName": "Backpropagation",
                        "subConcept": "Softmax & Cross-Entropy Gradient",
                        "difficulty": "Advanced",
                        "canonicalSummary": "Chain-rule gradient computation across network layers.",
                        "misconception": "Softmax derivatives require individual Jacobian matrix inversion",
                        "prerequisites": ["Multivariate Calculus", "Chain Rule", "Log-Likelihood Loss"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "C Programming",
        "topics": [
            {
                "topicName": "C Basics",
                "concepts": [
                    {
                        "conceptName": "C Variables & Data Types",
                        "subConcept": "Variables & Types",
                        "difficulty": "Beginner",
                        "canonicalSummary": "Introduction to memory storage and standard representations in C.",
                        "misconception": "C variables do not have fixed data types",
                        "prerequisites": ["Syntax"]
                    },
                    {
                        "conceptName": "Control Flow & Conditionals",
                        "subConcept": "Branching & Loops",
                        "difficulty": "Beginner",
                        "canonicalSummary": "Conditional execution and loop constructs.",
                        "misconception": "Loops always terminate automatically",
                        "prerequisites": ["C Variables & Data Types"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "Leadership & Relationship Management Skills",
        "topics": [
            {
                "topicName": "Leadership",
                "concepts": [
                    {
                        "conceptName": "Leadership Foundations",
                        "subConcept": "Styles & Roles",
                        "difficulty": "Beginner",
                        "canonicalSummary": "Overview of management styles and team leadership principles.",
                        "misconception": "Leadership is only for senior executives",
                        "prerequisites": []
                    },
                    {
                        "conceptName": "Emotional Intelligence",
                        "subConcept": "Self-Awareness & Empathy",
                        "difficulty": "Beginner",
                        "canonicalSummary": "Methods of managing relationships and self-awareness.",
                        "misconception": "Emotional intelligence is a soft skill with no measurable impact",
                        "prerequisites": ["Leadership Foundations"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "C# Programming",
        "topics": [
            {
                "topicName": "Object Oriented C#",
                "concepts": [
                    {
                        "conceptName": "C# Object Oriented Programming",
                        "subConcept": "Classes & Interfaces",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "OOP principles implemented in C# syntax.",
                        "misconception": "Structs and classes behave identically in C#",
                        "prerequisites": ["C Programming"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "Machine Learning",
        "topics": [
            {
                "topicName": "Supervised Algorithms",
                "concepts": [
                    {
                        "conceptName": "Supervised Learning",
                        "subConcept": "Regression & Classification",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "Methods for mapping inputs to labeled outputs.",
                        "misconception": "Supervised learning can fit any non-linear function without overfitting",
                        "prerequisites": ["Calculus", "Linear Algebra"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "Artificial Intelligence",
        "topics": [
            {
                "topicName": "Heuristic Optimization",
                "concepts": [
                    {
                        "conceptName": "Genetic Algorithms",
                        "subConcept": "Evolutionary Operators",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "Heuristic optimization modeling natural selection.",
                        "misconception": "Genetic algorithms guarantee mathematical global maximum convergence",
                        "prerequisites": ["Probability & Statistics"]
                    },
                    {
                        "conceptName": "Heuristic Search",
                        "subConcept": "A* Pathfinding",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "Optimal search procedures utilizing heuristic weights.",
                        "misconception": "Admissible heuristics can overestimate the actual remaining path cost",
                        "prerequisites": ["Depth-First Search (DFS)"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "Digital Image Processing",
        "topics": [
            {
                "topicName": "Image Representation",
                "concepts": [
                    {
                        "conceptName": "Digital Image Processing Basics",
                        "subConcept": "Sampling & Quantization",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "Discretization of continuous image frames.",
                        "misconception": "Higher sampling rates always increase perceptual quality infinitely",
                        "prerequisites": []
                    },
                    {
                        "conceptName": "Image Enhancement",
                        "subConcept": "Histogram Transformations",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "Methods of modifying contrast and spatial domain filters.",
                        "misconception": "Histogram equalization is a lossless operation",
                        "prerequisites": ["Digital Image Processing Basics"]
                    },
                    {
                        "conceptName": "Sobel vs. Laplacian Filters",
                        "subConcept": "First vs Second Derivative Edge Detection",
                        "difficulty": "Intermediate",
                        "canonicalSummary": "Spatial domain filtering comparing first-order gradient operators (Sobel filter) and second-order isotropic operators (Laplacian filter) for edge detection.",
                        "misconception": "Laplacian filters calculate directional edge gradients like Sobel operators.",
                        "prerequisites": ["Image Enhancement", "Spatial Filtering"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "Advanced Web Technologies",
        "topics": [
            {
                "topicName": "Architectures",
                "concepts": [
                    {
                        "conceptName": "Advanced Web Architectures",
                        "subConcept": "REST & MVC Patterns",
                        "difficulty": "Advanced",
                        "canonicalSummary": "Architectural models of web communication protocols.",
                        "misconception": "REST API calls must be stateless on server networks",
                        "prerequisites": []
                    },
                    {
                        "conceptName": "Client-Server State Management",
                        "subConcept": "JSON Web Tokens (JWT)",
                        "difficulty": "Advanced",
                        "canonicalSummary": "Securing web routes and sessions using credentials.",
                        "misconception": "JWT payload signatures encrypt the payload data",
                        "prerequisites": ["Advanced Web Architectures"]
                    }
                ]
            }
        ]
    },
    {
        "subjectName": "Soft Computing",
        "topics": [
            {
                "topicName": "Approximate Reasoning",
                "concepts": [
                    {
                        "conceptName": "Soft Computing Fundamentals",
                        "subConcept": "Imprecise Models",
                        "difficulty": "Advanced",
                        "canonicalSummary": "Overview of neural, fuzzy, and genetic computing paradigms.",
                        "misconception": "Soft computing yields exact analytical solutions",
                        "prerequisites": []
                    },
                    {
                        "conceptName": "Fuzzy Inference Systems",
                        "subConcept": "Membership Defuzzification",
                        "difficulty": "Advanced",
                        "canonicalSummary": "Mapping crisp inputs to fuzzy values and defuzzifying.",
                        "misconception": "Fuzzy logic is based on random probability distributions",
                        "prerequisites": ["Soft Computing Fundamentals"]
                    },
                    {
                        "conceptName": "Neuro-Fuzzy Hybridization",
                        "subConcept": "ANFIS Systems",
                        "difficulty": "Advanced",
                        "canonicalSummary": "Integrating neural learning features with fuzzy systems.",
                        "misconception": "Fuzzy rules cannot be adjusted automatically",
                        "prerequisites": ["Fuzzy Inference Systems", "Backpropagation"]
                    }
                ]
            }
        ]
    }
]

def load_ppt_metadata():
    ppt_file = os.path.join(BASE_DIR, 'data', 'ppt_metadata.json')
    try:
        if os.path.exists(ppt_file):
            with open(ppt_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading ppt_metadata.json: {e}")
    return []

def init_database():
    print("Initializing Neon PostgreSQL database...")
    if not DB_URL:
        print("DATABASE_URL not set. Skipping DB initialization.")
        return
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Quick check if tables already exist
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');")
            tables_exist = cur.fetchone()[0]
            
            if not tables_exist:
                schema_path = os.path.join(BASE_DIR, 'schema.sql')
                if os.path.exists(schema_path):
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    clean_lines = [l for l in schema_sql.split('\n') if not l.strip().startswith('--')]
                    clean_sql = '\n'.join(clean_lines)
                    cur.execute(clean_sql)
                    conn.commit()

            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS points INT DEFAULT 100;")
            cur.execute("ALTER TABLE doubts ADD COLUMN IF NOT EXISTS points INT DEFAULT 25;")
            cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS is_ai_verified BOOLEAN DEFAULT FALSE;")
            cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS is_faculty_verified BOOLEAN DEFAULT FALSE;")
            cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS verification_state VARCHAR(50) DEFAULT 'Reviewing';")
            cur.execute("ALTER TABLE doubts ADD COLUMN IF NOT EXISTS embedding vector(384);")
            conn.commit()

            roles = ['student', 'peer_mentor', 'faculty', 'admin']
            for r in roles:
                cur.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;", (r,))
            conn.commit()

            cur.execute("SELECT id, name FROM roles;")
            role_map = {row[1]: row[0] for row in cur.fetchall()}

            default_users = [
                ("alex.morgan@studybuddy.edu", "Alex Morgan", "student", "3rd Year", "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150", 100),
                ("rahul.sharma@studybuddy.edu", "Rahul Sharma", "peer_mentor", "4th Year", "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=150", 350),
                ("elena.vance@studybuddy.edu", "Elena Vance", "peer_mentor", "4th Year", "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=150", 280),
                ("priya.patel@studybuddy.edu", "Priya Patel", "peer_mentor", "3rd Year", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150", 210),
                ("jordan.hayes@studybuddy.edu", "Jordan Hayes", "peer_mentor", "2nd Year", "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&q=80&w=150", 110),
                ("sarah.jenkins@studybuddy.edu", "Dr. Sarah Jenkins", "faculty", "Faculty", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=250", 100),
                ("ai@studybuddy.com", "AI Teaching Assistant", "admin", "AI Agent", "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=150", 999)
            ]
            user_map = {}
            user_rows = [
                (email, name, role_map[role_name], avatar, year, points)
                for email, name, role_name, year, avatar, points in default_users
            ]
            cur.executemany("""
                INSERT INTO users (email, password_hash, full_name, role_id, avatar_url, academic_year, points)
                VALUES (%s, 'hash', %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE 
                SET full_name = EXCLUDED.full_name, avatar_url = EXCLUDED.avatar_url, academic_year = EXCLUDED.academic_year;
            """, user_rows)
            conn.commit()
            cur.execute("SELECT id, full_name FROM users WHERE full_name = ANY(%s);", ([n for _, n, *_ in default_users],))
            for u_id, u_name in cur.fetchall():
                user_map[u_name] = u_id

            # NOTE: this used to be gated behind `if not tables_exist:`, which
            # meant that once a DB had been initialized once, any concepts
            # added to TAXONOMY later (e.g. "Sobel vs. Laplacian Filters")
            # would NEVER get seeded in on an already-running deployment —
            # so lookups for that concept would silently come back empty,
            # doubts couldn't be tagged with it, and the RAG grounding had
            # nothing correct to retrieve. The insert pattern below is
            # already idempotent (select-then-insert), so it's safe to run
            # on every startup.
            for subj in TAXONOMY:
                subj_name = subj["subjectName"]
                subj_code = subj_name.lower().replace(" ", "_")[:20]
                cur.execute("""
                    INSERT INTO subjects (code, name, description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id;
                """, (subj_code, subj_name, f"Course in {subj_name}"))
                subj_id = cur.fetchone()[0]

                for top in subj["topics"]:
                    top_name = top["topicName"]
                    cur.execute("SELECT id FROM topics WHERE subject_id = %s AND name = %s;", (subj_id, top_name))
                    top_row = cur.fetchone()
                    if not top_row:
                        cur.execute("""
                            INSERT INTO topics (subject_id, name, description)
                            VALUES (%s, %s, %s) RETURNING id;
                        """, (subj_id, top_name, f"Topic: {top_name}"))
                        top_id = cur.fetchone()[0]
                    else:
                        top_id = top_row[0]

                    if top_id:
                        for con in top["concepts"]:
                            con_name = con["conceptName"]
                            sub_con = con.get("subConcept", "")
                            diff = con.get("difficulty", "Beginner")
                            summary = con.get("canonicalSummary", "")
                            misconception = con.get("misconception", "")

                            cur.execute("SELECT id FROM concepts WHERE topic_id = %s AND name = %s;", (top_id, con_name))
                            con_row = cur.fetchone()
                            if not con_row:
                                cur.execute("""
                                    INSERT INTO concepts (topic_id, name, sub_concept, difficulty_level, canonical_summary, common_misconception)
                                    VALUES (%s, %s, %s, %s, %s, %s);
                                """, (top_id, con_name, sub_con, diff, summary, misconception))
            conn.commit()

            print("Neon PostgreSQL Database initialized & seeded successfully!")
        conn.close()
    except Exception as e:
        print(f"Error during DB initialization: {e}")

@app.on_event("startup")
def startup_event():
    import threading
    # Run DB init off the event loop thread so the server starts accepting
    # requests (static files, health check) immediately instead of blocking
    # on Neon round trips for the whole seed process.
    threading.Thread(target=init_database, daemon=True).start()

# Frontend HTML Page Routes
@app.get("/")
def read_root():
    return FileResponse(os.path.join(BASE_DIR, "student-dashboard.html"))

@app.get("/student-dashboard.html")
def read_student_dashboard():
    return FileResponse(os.path.join(BASE_DIR, "student-dashboard.html"))

@app.get("/faculty-dashboard.html")
def read_faculty_dashboard():
    return FileResponse(os.path.join(BASE_DIR, "faculty-dashboard.html"))

@app.get("/login.html")
def read_login():
    return FileResponse(os.path.join(BASE_DIR, "login.html"))

@app.get("/index.html")
def read_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/knowledge_graph.html")
def read_knowledge_graph():
    return FileResponse(os.path.join(BASE_DIR, "knowledge_graph.html"))

class KgRagRequest(BaseModel):
    concept: str
    question: str = ""
    exam_mode: str = "none"  # "none" | "5m" | "10m"

@app.post("/api/kg_rag")
@app.post("/kg_rag")
def kg_rag(request: KgRagRequest):
    """RAG endpoint called by the Knowledge Graph when 'Ask Doubt in Portal'
    is clicked. Returns a grounded answer from the syllabus vector store."""
    concept = request.concept.strip()
    question = request.question.strip() or f"Explain {concept} in detail."
    mode = request.exam_mode

    # Try the active RAG chain first
    if rag_chains_by_mode:
        chain = rag_chains_by_mode.get(mode) or rag_chains_by_mode.get("none")
        if chain:
            try:
                answer = chain.invoke(question + " " + concept)
                return {"success": True, "answer": answer, "source": "rag", "concept": concept}
            except Exception as e:
                print(f"kg_rag chain error: {e}")

    # Fallback: pull the concept record from the taxonomy table
    concept_row = run_query("""
        SELECT c.name, c.canonical_summary, c.misconception, c.prerequisites,
               t.name as topic, s.name as subject
        FROM concepts c
        JOIN topics t ON c.topic_id = t.id
        JOIN subjects s ON t.subject_id = s.id
        WHERE c.name ILIKE %s
        LIMIT 1;
    """, [f"%{concept}%"], fetch_one=True)

    if concept_row:
        ans = f"**{concept_row['name']}** ({concept_row['subject']} / {concept_row['topic']})\n\n"
        if concept_row.get('canonical_summary'):
            ans += concept_row['canonical_summary'] + "\n\n"
        if concept_row.get('misconception'):
            ans += f"⚠️ Common misconception: {concept_row['misconception']}"
        return {"success": True, "answer": ans, "source": "taxonomy", "concept": concept}

    return {
        "success": False,
        "answer": f"No syllabus content found for '{concept}'. Try searching the Student Portal.",
        "source": "none",
        "concept": concept
    }

# NLP Helpers
def tokenize(text):
    return re.findall(r'\b\w+\b', text.lower())

def get_keywords(tokens):
    stopwords = {'why', 'does', 'need', 'recursion', 'what', 'happens', 'if', 'we', 'don', 't', 'use', 'it', 
                 'is', 'the', 'of', 'in', 'and', 'to', 'a', 'for', 'on', 'with', 'an', 'by', 'that', 'from',
                 'how', 'when', 'should', 'at', 'which', 'or', 'about'}
    return [t for t in tokens if t not in stopwords and len(t) > 2]

def calculate_match_score(query_keywords, target_text):
    if not query_keywords:
        return 0.0
    target_tokens = tokenize(target_text)
    matches = 0
    for kw in query_keywords:
        if kw in target_tokens:
            matches += 1.0
        elif any(kw in tok or tok in kw for tok in target_tokens):
            matches += 0.5
    return matches / max(1, len(target_tokens))

def generate_graph_path(topic_name, concept):
    path = []
    path.append({"name": topic_name, "type": "Topic"})
    path.append({"name": concept["conceptName"], "type": "Concept"})
    if "prerequisites" in concept:
        for prereq in concept["prerequisites"]:
            path.append({"name": prereq, "type": "Prerequisite"})
    return path

def generate_explanations(concept_name):
    if concept_name == "Binary Search":
        return {
            "Step-by-step": "1. Find the middle element of the sorted array.\n2. Compare target with middle element.\n3. If target matches, return index.\n4. If target is smaller, repeat on left half.\n5. If target is larger, repeat on right half.\n*Note: Array must be sorted first!*",
            "Analogy": "Searching an unsorted list is like looking for a word in a dictionary with shuffled pages. Sorting allows you to open right to the middle page and know which way to turn.",
            "Technical": "Binary search is a divide-and-conquer algorithm with O(log N) complexity operating on monotonically ordered array structures."
        }
    elif concept_name == "Depth-First Search (DFS)":
        return {
            "Step-by-step": "1. Push start node to stack.\n2. Mark visited.\n3. While stack not empty, pop top node.\n4. Push unvisited neighbors.\n5. Repeat until explored.",
            "Analogy": "DFS is like exploring a maze: walk down a single path as far as possible. At a dead end, backtrack to the last fork.",
            "Technical": "DFS visits graph vertices by going deep along branches before backtracking. Operates in O(V + E) using LIFO stack semantics."
        }
    elif concept_name == "Sobel vs. Laplacian Filters" or "sobel" in concept_name.lower():
        return {
            "Step-by-step": "1. **Sobel Filter**: Uses 3x3 horizontal and vertical gradient masks (first-order derivative) to detect edge magnitude and direction.\n2. **Laplacian Filter**: Uses a 3x3 isotropic mask (second-order derivative) to highlight rapid intensity changes, fine details, and zero-crossings.\n3. **Key Difference**: Sobel is directional and robust against noise, whereas Laplacian is non-directional (isotropic) but highly sensitive to noise.",
            "Analogy": "Sobel is like measuring how steep a slope is in a specific direction, while Laplacian detects sharp crests and valleys regardless of direction.",
            "Technical": "Sobel computes spatial gradient magnitude G = sqrt(Gx^2 + Gy^2) via Gx/Gy kernels. Laplacian calculates scalar ∇^2 f = ∂^2f/∂x^2 + ∂^2f/∂y^2 via a 3x3 central kernel."
        }
    return {
        "Step-by-step": f"1. Analyze concept: {concept_name}.\n2. Resolve prerequisites.\n3. Execute computation.",
        "Analogy": f"Structural component in {concept_name} hierarchy.",
        "Technical": f"Execution of {concept_name} utilizes O(N) allocation boundaries."
    }

def format_exam_answer(concept, exam_mode, base_answer):
    """Fallback formatter (no LLM required) that reshapes a base explanation
    into a '5 Mark' short answer or '10 Mark' long answer exam style."""
    name = concept.get("conceptName", "Concept")
    summary = concept.get("canonicalSummary", "")
    misconception = concept.get("misconception", "")
    prereqs = concept.get("prerequisites", [])

    if exam_mode == "5m":
        lines = [f"**{name} — 5 Mark Answer**", ""]
        if summary:
            lines.append(f"**Definition:** {summary}")
        lines.append("")
        lines.append("**Key Points:**")
        for point in base_answer.split("\n"):
            point = point.strip("- •\t ")
            if point:
                lines.append(f"- {point}")
        if misconception:
            lines.append(f"- Common mistake to avoid: {misconception}")
        return "\n".join(lines)

    if exam_mode == "10m":
        lines = [f"**{name} — 10 Mark Answer**", ""]
        lines.append("**1. Introduction**")
        lines.append(summary or f"{name} is a core concept covered in this course.")
        lines.append("")
        lines.append("**2. Working / Explanation**")
        for i, point in enumerate([p.strip("- •\t ") for p in base_answer.split("\n") if p.strip()], start=1):
            lines.append(f"   {i}. {point}")
        lines.append("")
        if prereqs:
            lines.append("**3. Prerequisites / Related Concepts**")
            lines.append(", ".join(prereqs))
            lines.append("")
        if misconception:
            lines.append("**4. Common Misconception**")
            lines.append(misconception)
            lines.append("")
        lines.append("**5. Conclusion**")
        lines.append(f"A solid grasp of {name} requires understanding both the mechanism above and its prerequisites.")
        return "\n".join(lines)

    return base_answer

# API Endpoints (Handling both /api/ and non-/api/ prefixes)
@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok", "db": "PostgreSQL Neon Active", "server": "FastAPI Unified Server"}

@app.get("/api/doubts")
@app.get("/doubts")
def get_doubts(subject: str = "All"):
    # Single round-trip: pull all doubts + their answers via a LEFT JOIN LATERAL
    # json_agg instead of the previous N+1 (one query per doubt for its answers),
    # which is what made the feed/queue feel slow to load as data grew.
    query = """
        SELECT d.id, d.title, d.raw_query as "rawQuery", d.difficulty, d.intent,
               d.detected_misconception as "misconception", d.status, d.created_at, d.points,
               u.full_name as "studentName", u.academic_year as "studentYear", u.avatar_url as "studentAvatar",
               s.name as "subject", t.name as "topic", c.name as "concept",
               COALESCE(ans.answers, '[]'::json) as "answers"
        FROM doubts d
        JOIN users u ON d.student_id = u.id
        LEFT JOIN subjects s ON d.subject_id = s.id
        LEFT JOIN topics t ON d.topic_id = t.id
        LEFT JOIN concepts c ON d.concept_id = c.id
        LEFT JOIN LATERAL (
            SELECT json_agg(json_build_object(
                'id', a.id,
                'content', a.content,
                'style', a.explanation_style,
                'isAiVerified', a.is_ai_verified,
                'isFacultyVerified', a.is_faculty_verified,
                'verificationState', a.verification_state,
                'authorName', au.full_name,
                'authorAvatar', au.avatar_url
            ) ORDER BY a.created_at ASC) as answers
            FROM answers a
            JOIN users au ON a.author_id = au.id
            WHERE a.doubt_id = d.id
        ) ans ON true
    """
    params = []
    if subject != "All":
        query += " WHERE s.name = %s"
        params.append(subject)

    query += " ORDER BY d.created_at DESC"

    doubts_rows = run_query(query, params, fetch_all=True)
    if doubts_rows is None:
        doubts_rows = []

    for d in doubts_rows:
        if isinstance(d.get('answers'), str):
            d['answers'] = json.loads(d['answers'])
        for a in d.get('answers') or []:
            a['id'] = str(a['id'])
        d['id'] = str(d['id'])
        d['created_at'] = str(d['created_at'])
        d['timestamp'] = d['created_at']

    return doubts_rows

class DoubtRequest(BaseModel):
    student_id: str = "alex.morgan@studybuddy.edu"
    title: str = ""
    raw_query: str
    exam_mode: str = "none"  # "none" | "5m" | "10m"

@app.post("/api/ask")
@app.post("/api/doubts")
@app.post("/doubts")
def ask_doubt(request: DoubtRequest):
    raw_query = request.raw_query
    exam_mode = request.exam_mode if request.exam_mode in ("none", "5m", "10m") else "none"
    full_text = f"{request.title} {request.raw_query}".strip()
    if not full_text:
        raise HTTPException(status_code=400, detail="Empty doubt query")
        
    tokens = tokenize(full_text)
    keywords = get_keywords(tokens)
    query_lower = full_text.lower()
    
    best_match = None
    max_score = 0.0
    
    # Priority keyword rules for subjects
    if any(k in query_lower for k in ['sobel', 'laplacian', 'filter', 'filters', 'dip', 'image processing', 'edge detection', 'spatial domain', 'histogram', 'quantization', 'pixel', 'convolution']):
        for subject in TAXONOMY:
            if subject["subjectName"] == "Digital Image Processing":
                topic = subject["topics"][0]
                concept = topic["concepts"][-1] # Sobel vs Laplacian Filters
                for c in topic["concepts"]:
                    if "sobel" in c["conceptName"].lower() or "filter" in c["conceptName"].lower():
                        concept = c
                        break
                best_match = {
                    "subject": "Digital Image Processing",
                    "topic": topic["topicName"],
                    "concept": concept
                }
                max_score = 3.5
                break
    elif any(k in query_lower for k in ['ai', 'heuristic', 'genetic', 'a*', 'search', 'evolutionary', 'optimization']):
        for subject in TAXONOMY:
            if subject["subjectName"] == "Artificial Intelligence":
                topic = subject["topics"][0]
                best_match = {
                    "subject": "Artificial Intelligence",
                    "topic": topic["topicName"],
                    "concept": topic["concepts"][0]
                }
                max_score = 3.0
                break

    if not best_match:
        for subject in TAXONOMY:
            for topic in subject["topics"]:
                for concept in topic["concepts"]:
                    name_score = calculate_match_score(keywords, concept["conceptName"]) * 4.0
                    sub_score = calculate_match_score(keywords, concept["subConcept"]) * 2.0
                    summary_score = calculate_match_score(keywords, concept["canonicalSummary"]) * 1.5
                    misconception_score = calculate_match_score(keywords, concept["misconception"]) * 1.5
                    
                    total_score = name_score + sub_score + summary_score + misconception_score
                    
                    if total_score > max_score:
                        max_score = total_score
                        best_match = {
                            "subject": subject["subjectName"],
                            "topic": topic["topicName"],
                            "concept": concept
                        }
                    
    if not best_match or max_score < 0.05:
        fallback_concept = {
            "conceptName": "Recursion",
            "subConcept": "Base Case",
            "difficulty": "Beginner",
            "misconception": "No common misconception active.",
            "prerequisites": ["Functions"]
        }
        best_match = {
            "subject": "Computer Science",
            "topic": "Algorithms",
            "concept": fallback_concept
        }
        max_score = 0.0
        
    concept = best_match["concept"]
    confidence = 0.50 + min(0.49, max_score / 4.0) if max_score > 0 else 0.35
    
    intent = "Conceptual"
    if any(word in query_lower for word in ['error', 'bug', 'fail', 'wrong', 'output', 'null', 'incorrect', 'debug', 'broken', 'fix', 'why not', "doesn't work", "does not work", "failing"]):
        intent = "Debugging"
    elif any(word in query_lower for word in ['calculate', 'solve', 'derive', 'formula', 'math', 'equation', 'proof', 'compute', 'value', 'differentiation', 'derivative']):
        intent = "Problem Solving"
    elif any(word in query_lower for word in ['exam', 'quiz', 'test', 'grade', 'midterm', 'final', 'marks', 'practice']):
        intent = "Exam Prep"
        
    is_misconception_triggered = False
    if "misconception" in concept and concept["misconception"]:
        mis_words = get_keywords(tokenize(concept["misconception"]))
        matches = len([w for w in mis_words if w in tokens])
        if matches >= min(2, len(mis_words)):
            is_misconception_triggered = True
            
    subj_row = run_query("SELECT id FROM subjects WHERE name = %s;", [best_match["subject"]], fetch_one=True)
    subj_id = subj_row['id'] if subj_row else None
    
    topic_row = run_query("SELECT id FROM topics WHERE name = %s AND subject_id = %s;", [best_match["topic"], subj_id], fetch_one=True)
    topic_id = topic_row['id'] if topic_row else None
    
    concept_row = run_query("SELECT id FROM concepts WHERE name = %s AND topic_id = %s;", [concept["conceptName"], topic_id], fetch_one=True)
    concept_id = concept_row['id'] if concept_row else None
    
    user_row = run_query("SELECT id FROM users WHERE email = %s;", [request.student_id], fetch_one=True)
    if not user_row:
        user_row = run_query("SELECT id FROM users WHERE email = 'alex.morgan@studybuddy.edu';", fetch_one=True)
    student_id = user_row['id'] if user_row else None
    
    run_query("UPDATE users SET points = GREATEST(0, points - 15) WHERE id = %s;", [student_id], commit=True)
    
    title = request.title if request.title else (raw_query.split('?')[0] + '?' if '?' in raw_query else raw_query + '?')
    detected_misconception = concept["misconception"] if is_misconception_triggered else "No common misconception active. Query aligns with canonical understanding."
    
    query_embedding = None
    if embeddings:
        try:
            query_embedding = embeddings.embed_query(full_text)
        except Exception as e:
            print(f"Error embedding query: {e}")

    # BUGFIX: this used to search across ALL doubts regardless of concept,
    # so a semantically-similar-sounding question from a totally different
    # subject (e.g. an old "Artificial Intelligence" doubt) could match and
    # get returned instead — and critically, the new doubt was NEVER
    # inserted into the DB in that case, so it silently reused the OLD
    # doubt's subject/channel instead of the freshly (correctly) classified
    # one. This is what caused a Digital Image Processing question to show
    # up filed under the AI channel. Fix: only reuse an answer if it's from
    # the SAME concept we just classified into, and always insert the new
    # doubt with the correct subject/topic/concept regardless.
    existing_resolved = None
    if query_embedding and concept_id:
        try:
            match_row = run_query("""
                SELECT d.id, a.content, a.verification_state, (d.embedding <=> %s::vector) as distance
                FROM doubts d
                JOIN answers a ON a.doubt_id = d.id
                WHERE d.embedding IS NOT NULL AND d.concept_id = %s
                ORDER BY distance LIMIT 1
            """, [str(query_embedding), concept_id], fetch_one=True)
            if match_row and match_row['distance'] < 0.08:
                existing_resolved = match_row
        except Exception as e:
            print(f"Error querying semantic cache: {e}")

    if existing_resolved:
        # Reuse the verified answer content (skips a slow LLM call) but still
        # create a proper new doubt row so it's correctly filed & visible.
        answer_text = existing_resolved['content']
        if exam_mode != "none":
            answer_text = format_exam_answer(concept, exam_mode, answer_text)
        cache_hit = True
    else:
        answer_text = ""
        cache_hit = False
        active_chain = rag_chains_by_mode.get(exam_mode) or rag_chain
        if active_chain:
            try:
                answer_text = active_chain.invoke(full_text)
            except Exception as e:
                print(f"LLM chain invoke warning: {e}")
                exps = generate_explanations(concept["conceptName"])
                answer_text = f"**{concept['conceptName']} Overview:**\n{exps['Step-by-step']}\n\n*Note: AI LLM is operating in fallback mode using cached course materials.*"
                if exam_mode != "none":
                    answer_text = format_exam_answer(concept, exam_mode, exps['Step-by-step'])
        else:
            exps = generate_explanations(concept["conceptName"])
            if exam_mode != "none":
                answer_text = format_exam_answer(concept, exam_mode, exps['Step-by-step'])
            else:
                answer_text = f"**{concept['conceptName']} Overview:**\n{exps['Step-by-step']}"

    insert_query = """
        INSERT INTO doubts (student_id, subject_id, topic_id, concept_id, title, raw_query, difficulty, intent, detected_misconception, auto_sort_confidence, status, points, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Open', 25, %s::vector)
        RETURNING id;
    """
    confidence_json = json.dumps({"topic": confidence, "concept": confidence})
    inserted = run_query(insert_query, [
        student_id, subj_id, topic_id, concept_id, title, raw_query, 
        concept.get("difficulty", "Beginner"), intent, detected_misconception, 
        confidence_json, str(query_embedding) if query_embedding else None
    ], commit=True, fetch_one=True)

    if cache_hit:
        run_query("UPDATE users SET points = points + 15 WHERE id = %s;", [student_id], commit=True)

    ai_user = run_query("SELECT id FROM users WHERE email = 'ai@studybuddy.com';", fetch_one=True)
    if ai_user and inserted:
        run_query("""
            INSERT INTO answers (doubt_id, author_id, content, explanation_style, is_ai_verified, is_faculty_verified, verification_state)
            VALUES (%s, %s, %s, 'Step-by-step', TRUE, FALSE, 'AI_REVIEWED');
        """, [inserted['id'], ai_user['id'], answer_text], commit=True)

    matching_resources = run_query("""
        SELECT title, url, metadata 
        FROM resources 
        WHERE concept_id = %s
    """, [concept_id], fetch_all=True)
    if matching_resources:
        for r in matching_resources:
            r['metadata'] = r['metadata'] if isinstance(r['metadata'], dict) else json.loads(r['metadata'])

    result = {
        "id": str(inserted['id']) if inserted else "",
        "subject": best_match["subject"],
        "topic": best_match["topic"],
        "concept": concept["conceptName"],
        "subConcept": concept.get("subConcept", ""),
        "difficulty": concept.get("difficulty", "Beginner"),
        "intent": intent,
        "misconception": detected_misconception,
        "isMisconceptionTriggered": is_misconception_triggered,
        "prerequisites": concept.get("prerequisites", []),
        "confidence": confidence,
        "examMode": exam_mode,
        "cacheHit": cache_hit,
        "graphPath": generate_graph_path(best_match["topic"], concept),
        "explanation": {
            "Step-by-step": answer_text, "Analogy": answer_text, "Technical": answer_text
        },
        "resources": matching_resources if matching_resources else []
    }
    return result

class AnswerRequest(BaseModel):
    content: str
    authorEmail: str = "rahul.sharma@studybuddy.edu"

@app.post("/api/doubts/{doubt_id}/answers")
@app.post("/doubts/{doubt_id}/answers")
def add_answer(doubt_id: str, request: AnswerRequest):
    content = request.content
    if not content.strip():
        raise HTTPException(status_code=400, detail="Empty answer content")

    # Use a SINGLE connection for all 4 operations to avoid multiple
    # Neon TCP round-trips which were causing the visible 'Post Answer' lag.
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Resolve author
            cur.execute("SELECT id FROM users WHERE email = %s;", [request.authorEmail])
            user_row = cur.fetchone()
            if not user_row:
                raise HTTPException(status_code=404, detail="User not found")
            author_id = user_row[0]

            # 2. Get doubt bounty
            cur.execute("SELECT points FROM doubts WHERE id = %s;", [doubt_id])
            doubt_row = cur.fetchone()
            bounty = doubt_row[0] if doubt_row else 25

            # 3. Insert answer
            cur.execute("""
                INSERT INTO answers (doubt_id, author_id, content, explanation_style,
                                     is_ai_verified, is_faculty_verified, verification_state)
                VALUES (%s, %s, %s, 'Technical', FALSE, FALSE, 'Reviewing')
                RETURNING id;
            """, [doubt_id, author_id, content])
            inserted = cur.fetchone()
            answer_id = str(inserted[0]) if inserted else ""

            # 4. Update doubt status + user points in the same transaction
            cur.execute("UPDATE doubts SET status = 'Resolved' WHERE id = %s;", [doubt_id])
            cur.execute("UPDATE users SET points = points + %s WHERE id = %s;", [bounty, author_id])

            conn.commit()
        conn.close()
    except HTTPException:
        raise
    except Exception as e:
        print(f"add_answer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to post answer")

    return {
        "success": True,
        "answerId": answer_id,
        "bountyAwarded": bounty
    }

@app.post("/api/answers/{answer_id}/verify")
@app.post("/answers/{answer_id}/verify")
def verify_answer(answer_id: str):
    run_query("""
        UPDATE answers 
        SET is_faculty_verified = TRUE, verification_state = 'FACULTY_VERIFIED' 
        WHERE id = %s;
    """, [answer_id], commit=True)
    
    author_row = run_query("SELECT author_id FROM answers WHERE id = %s;", [answer_id], fetch_one=True)
    if author_row:
        author_id = author_row['author_id']
        run_query("UPDATE users SET points = points + 15 WHERE id = %s;", [author_id], commit=True)
        
    return {"success": True, "message": "Answer verified by Faculty. +15 points awarded."}

class VerifyAiRequest(BaseModel):
    verified: bool

@app.post("/api/answers/{answer_id}/verify_ai")
@app.post("/answers/{answer_id}/verify_ai")
def verify_ai_answer(answer_id: str, request: VerifyAiRequest):
    if request.verified:
        run_query("""
            UPDATE answers 
            SET is_ai_verified = TRUE, verification_state = 'AI_REVIEWED' 
            WHERE id = %s;
        """, [answer_id], commit=True)
        author_row = run_query("SELECT author_id FROM answers WHERE id = %s;", [answer_id], fetch_one=True)
        if author_row:
            author_id = author_row['author_id']
            run_query("UPDATE users SET points = points + 10 WHERE id = %s;", [author_id], commit=True)
            
    return {"success": True, "message": "AI verification state synchronized."}

@app.delete("/api/answers/{answer_id}")
@app.delete("/answers/{answer_id}")
def delete_answer(answer_id: str):
    ans_row = run_query("""
        SELECT doubt_id, author_id, is_faculty_verified, is_ai_verified 
        FROM answers 
        WHERE id = %s;
    """, [answer_id], fetch_one=True)
    if not ans_row:
        raise HTTPException(status_code=404, detail="Answer not found")
        
    doubt_id = ans_row['doubt_id']
    author_id = ans_row['author_id']
    
    doubt_row = run_query("SELECT points FROM doubts WHERE id = %s;", [doubt_id], fetch_one=True)
    bounty = doubt_row['points'] if doubt_row else 25
    
    deduction = bounty
    if ans_row['is_faculty_verified']:
        deduction += 15
    if ans_row['is_ai_verified']:
        deduction += 10
        
    run_query("DELETE FROM answers WHERE id = %s;", [answer_id], commit=True)
    run_query("UPDATE users SET points = GREATEST(0, points - %s) WHERE id = %s;", [deduction, author_id], commit=True)
    
    rem = run_query("SELECT COUNT(*) as cnt FROM answers WHERE doubt_id = %s;", [doubt_id], fetch_one=True)
    rem_count = rem['cnt'] if rem else 0
    if rem_count == 0:
        run_query("UPDATE doubts SET status = 'Open' WHERE id = %s;", [doubt_id], commit=True)
        
    return {"success": True, "message": "Answer deleted successfully.", "deductedPoints": deduction}

class UpdateAnswerRequest(BaseModel):
    content: str

@app.put("/api/answers/{answer_id}")
@app.put("/answers/{answer_id}")
def update_answer(answer_id: str, request: UpdateAnswerRequest):
    content = request.content
    if not content.strip():
        raise HTTPException(status_code=400, detail="Empty answer content")
        
    ans = run_query("SELECT id FROM answers WHERE id = %s;", [answer_id], fetch_one=True)
    if not ans:
        raise HTTPException(status_code=404, detail="Answer not found")
        
    run_query("UPDATE answers SET content = %s WHERE id = %s;", [content, answer_id], commit=True)
    return {"success": True, "message": "Answer updated successfully."}

class UpdateDoubtRequest(BaseModel):
    title: str
    raw_query: str

@app.put("/api/doubts/{doubt_id}")
@app.put("/doubts/{doubt_id}")
def update_doubt(doubt_id: str, request: UpdateDoubtRequest):
    if not request.title.strip() or not request.raw_query.strip():
        raise HTTPException(status_code=400, detail="Title and query cannot be empty")
        
    db_doubt = run_query("SELECT id FROM doubts WHERE id = %s;", [doubt_id], fetch_one=True)
    if not db_doubt:
        raise HTTPException(status_code=404, detail="Doubt not found")
        
    run_query("""
        UPDATE doubts 
        SET title = %s, raw_query = %s 
        WHERE id = %s;
    """, [request.title, request.raw_query, doubt_id], commit=True)
    return {"success": True, "message": "Doubt updated successfully."}

@app.delete("/api/doubts/{doubt_id}")
@app.delete("/doubts/{doubt_id}")
def delete_doubt(doubt_id: str):
    db_doubt = run_query("SELECT student_id FROM doubts WHERE id = %s;", [doubt_id], fetch_one=True)
    if not db_doubt:
        raise HTTPException(status_code=404, detail="Doubt not found")
        
    student_id = db_doubt['student_id']
    run_query("UPDATE users SET points = points + 15 WHERE id = %s;", [student_id], commit=True)
    run_query("DELETE FROM doubts WHERE id = %s;", [doubt_id], commit=True)
    return {"success": True, "message": "Doubt deleted successfully."}

class ValidateRequest(BaseModel):
    query: str
    answer: str
    concept: str

@app.post("/api/validate_answer")
@app.post("/validate_answer")
def validate_answer(request: ValidateRequest):
    query = request.query
    answer = request.answer
    concept = request.concept
    
    if not answer.strip():
        return {"verified": False, "reason": "Answer is empty."}
        
    matching_res = run_query("""
        SELECT r.title, r.metadata
        FROM resources r
        JOIN concepts c ON r.concept_id = c.id
        WHERE c.name ILIKE %s OR %s ILIKE CONCAT('%%', c.name, '%%')
    """, [concept, concept], fetch_one=True)
    
    if not matching_res:
        target_reference = query + " " + concept
        resource_title = concept
    else:
        meta = matching_res['metadata'] if isinstance(matching_res['metadata'], dict) else json.loads(matching_res['metadata'])
        target_reference = meta.get("description", "") + " " + concept
        resource_title = matching_res['title']
        
    answer_tokens = tokenize(answer)
    answer_keywords = get_keywords(answer_tokens)
    ref_tokens = tokenize(target_reference)
    ref_keywords = get_keywords(ref_tokens)
    
    overlap = [w for w in answer_keywords if w in ref_keywords]
    verified = len(overlap) >= 2
    
    reason = f"Evaluated against course slide content: '{resource_title}'."
    if verified:
        return {
            "verified": True,
            "reason": f"{reason} AI verified alignment on key terms: {', '.join(overlap[:3])}."
        }
    else:
        return {
            "verified": False,
            "reason": f"{reason} Insufficient technical overlap with course materials."
        }

@app.get("/api/leaderboard")
@app.get("/leaderboard")
def get_leaderboard():
    query = """
        SELECT u.full_name as "name", u.academic_year as "year", u.avatar_url as "avatar", u.points,
               r.name as "role"
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE r.name IN ('peer_mentor', 'student')
        ORDER BY u.points DESC;
    """
    rows = run_query(query, fetch_all=True)
    if rows is None:
        rows = []
        
    for idx, row in enumerate(rows):
        if idx == 0:
            row['rank'] = "Expert"
        elif idx == 1:
            row['rank'] = "Brainiac"
        elif idx == 2:
            row['rank'] = "Contributor"
        elif idx == 3:
            row['rank'] = "Helper"
        else:
            row['rank'] = "Novice"
            
    return rows

@app.get("/api/user/{email}")
@app.get("/user/{email}")
def get_user(email: str):
    row = run_query("""
        SELECT u.id, u.full_name as "name", u.academic_year as "year", u.avatar_url as "avatar", u.points,
               r.name as "role"
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.email = %s;
    """, [email], fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    row['id'] = str(row['id'])
    return row

class PointsRequest(BaseModel):
    diff: int

@app.post("/api/user/{email}/points")
@app.post("/user/{email}/points")
def update_user_points(email: str, request: PointsRequest):
    row = run_query("SELECT id, points FROM users WHERE email = %s;", [email], fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
        
    new_points = max(0, row['points'] + request.diff)
    run_query("UPDATE users SET points = %s WHERE id = %s;", [new_points, row['id']], commit=True)
    
    return {"success": True, "points": new_points}

if __name__ == '__main__':
    import uvicorn
    print("Starting StudyBuddy Unified Server on http://127.0.0.1:8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)