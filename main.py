import os
import json
import re
import psycopg
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(__file__), 'env')
load_dotenv(dotenv_path=dotenv_path)

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

# Initialize HuggingFace Embeddings & PGVector store
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

# OpenRouter ChatOpenAI (Gemini-2.5-Flash)
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
            "Step-by-step": "1. Find the middle element of the sorted array.\n2. Compare target with the middle element.\n3. If target matches, return index.\n4. If target is smaller, repeat on left half.\n5. If target is larger, repeat on right half.\n*Note: Array must be sorted first!*",
            "Analogy": "Searching an unsorted list is like looking for a word in a dictionary where the pages are shuffled in random order—you'd have to check page-by-page. Sorting the array is what allows you to open directly to the middle page and know which direction to turn.",
            "Technical": "Binary search is a divide-and-conquer algorithm with O(log N) time complexity. It relies on the random-access property of arrays and strict monotonic ordering, where indices establish a transitive relationship: A[i] <= A[j] for all i < j."
        }
    elif concept_name == "Depth-First Search (DFS)":
        return {
            "Step-by-step": "1. Push the start node onto the stack.\n2. Mark it as visited.\n3. While stack is not empty, pop the top node.\n4. Push all unvisited neighbors onto the stack, marking them visited.\n5. Repeat until all connected components are explored.",
            "Analogy": "DFS is like exploring a maze: you walk down a single path as far as you can go. When you hit a dead-end, you backtrack to the last fork in the road and try the other direction. Recursion handles this backtracking automatically using the call stack.",
            "Technical": "DFS visits graph vertices by traversing deep along each branch before backtracking. It operates in O(V + E) time. It uses a LIFO discipline, either implicitly via recursive runtime call stack frames or explicitly via a Stack data structure."
        }
    elif concept_name == "Backpropagation":
        return {
            "Step-by-step": "1. Perform a forward pass to calculate predictions and loss.\n2. Compute the gradient of the loss with respect to output activation.\n3. Apply the mathematical chain rule layer by layer backwards.\n4. Multiply local derivatives to find parameter gradients.\n5. Update weights using gradient descent.",
            "Analogy": "Imagine a factory assembly line making toy cars. At the end, a quality checker flags errors. Backpropagation is like traced feedback going backwards along the line, telling each worker exactly how much their specific action contributed to the final defect.",
            "Technical": "Backpropagation computes the gradient of a loss function with respect to weights using the reverse-mode automatic differentiation chain rule: ∂L/∂w_ij = (∂L/∂z_j) * (∂z_j/∂w_ij). For Softmax with Cross-Entropy, the vector gradient simplifies directly to the error vector (y_hat - y)."
        }
    
    return {
        "Step-by-step": f"1. Analyze target concept: {concept_name}.\n2. Resolve dependencies.\n3. Implement recursively or iteratively.",
        "Analogy": f"Like building block assemblies where {concept_name} is the structural component.",
        "Technical": f"System execution of {concept_name} utilizes O(N) allocation boundaries."
    }

# Course Curriculum Taxonomy
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

def run_query(query, params=None, commit=False, fetch_one=False, fetch_all=False):
    with psycopg.connect(DB_URL) as conn:
        from psycopg.rows import dict_row
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
            
            result = None
            if fetch_one:
                result = cur.fetchone()
            elif fetch_all:
                result = cur.fetchall()
            return result

def init_database():
    print("Initializing and seeding PostgreSQL Neon DB tables...")
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Add columns if not exist
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS points INT DEFAULT 100;")
                cur.execute("ALTER TABLE doubts ADD COLUMN IF NOT EXISTS points INT DEFAULT 25;")
                cur.execute("ALTER TABLE doubts ADD COLUMN IF NOT EXISTS embedding vector(384);")
                cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS is_ai_verified BOOLEAN DEFAULT FALSE;")
                cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS is_faculty_verified BOOLEAN DEFAULT FALSE;")
                cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS verification_state VARCHAR(50) DEFAULT 'Reviewing';")
                
                # Seed roles
                roles = ['student', 'peer_mentor', 'faculty', 'admin', 'ai']
                for r in roles:
                    cur.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;", (r,))
                    
                # Get role maps
                cur.execute("SELECT id, name FROM roles;")
                role_map = {row[1]: row[0] for row in cur.fetchall()}
                
                # Seed default users
                default_users = [
                    ("alex.morgan@studybuddy.edu", "Alex Morgan", "student", "3rd Year", "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150", 100),
                    ("rahul.sharma@studybuddy.edu", "Rahul Sharma", "peer_mentor", "4th Year", "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=150", 350),
                    ("elena.vance@studybuddy.edu", "Elena Vance", "peer_mentor", "4th Year", "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=150", 280),
                    ("priya.patel@studybuddy.edu", "Priya Patel", "peer_mentor", "3rd Year", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150", 210),
                    ("jordan.hayes@studybuddy.edu", "Jordan Hayes", "peer_mentor", "2nd Year", "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&q=80&w=150", 110),
                    ("sarah.jenkins@studybuddy.edu", "Dr. Sarah Jenkins", "faculty", "Faculty", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=250", 100),
                    ("ai@studybuddy.com", "AI Teaching Assistant", "ai", "AI", "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=150", 100)
                ]
                
                user_map = {}
                for email, name, role_name, year, avatar, points in default_users:
                    role_id = role_map[role_name]
                    cur.execute("""
                        INSERT INTO users (email, password_hash, full_name, role_id, avatar_url, academic_year, points)
                        VALUES (%s, 'hash', %s, %s, %s, %s, %s)
                        ON CONFLICT (email) DO UPDATE 
                        SET full_name = EXCLUDED.full_name, avatar_url = EXCLUDED.avatar_url, academic_year = EXCLUDED.academic_year
                        RETURNING id;
                    """, (email, name, role_id, avatar, year, points))
                    user_id = cur.fetchone()[0]
                    user_map[name] = user_id
                    
                # Seed Taxonomy
                subject_map = {}
                topic_map = {}
                concept_map = {}
                
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
                    subject_map[subj_name] = subj_id
                    
                    for top in subj["topics"]:
                        top_name = top["topicName"]
                        cur.execute("""
                            INSERT INTO topics (subject_id, name, description)
                            VALUES (%s, %s, %s)
                            ON CONFLICT DO NOTHING;
                        """, (subj_id, top_name))
                        # Fetch topic_id
                        cur.execute("SELECT id FROM topics WHERE subject_id = %s AND name = %s;", (subj_id, top_name))
                        top_id = cur.fetchone()[0]
                        topic_map[(subj_name, top_name)] = top_id
                        
                        for con in top["concepts"]:
                            con_name = con["conceptName"]
                            sub_con = con.get("subConcept", "")
                            diff = con.get("difficulty", "Beginner")
                            summary = con.get("canonicalSummary", "")
                            misconception = con.get("misconception", "")
                            
                            cur.execute("""
                                INSERT INTO concepts (topic_id, name, sub_concept, difficulty_level, canonical_summary, common_misconception)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING;
                            """, (top_id, con_name, sub_con, diff, summary, misconception))
                            
                            cur.execute("SELECT id FROM concepts WHERE topic_id = %s AND name = %s;", (top_id, con_name))
                            con_id = cur.fetchone()[0]
                            concept_map[con_name] = con_id
                            
                # Seed Peer Profiles
                peers = [
                    ("Rahul Sharma", "Depth-First Search (DFS)", 0.88, 4.92, "Available Today", 28),
                    ("Elena Vance", "Backpropagation", 0.92, 4.88, "Available Today", 19),
                    ("Priya Patel", "Control Flow & Conditionals", 0.85, 4.75, "Available Tomorrow", 12),
                    ("Jordan Hayes", "Binary Search", 0.82, 4.60, "Busy", 8)
                ]
                for name, concept_name, exp, help_r, avail, sessions in peers:
                    u_id = user_map.get(name)
                    c_id = concept_map.get(concept_name)
                    if u_id and c_id:
                        cur.execute("""
                            INSERT INTO peer_profiles (user_id, concept_id, expertise_score, helpfulness_rating, availability_status, total_sessions_completed)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (user_id) DO UPDATE
                            SET concept_id = EXCLUDED.concept_id, expertise_score = EXCLUDED.expertise_score, 
                                helpfulness_rating = EXCLUDED.helpfulness_rating, availability_status = EXCLUDED.availability_status,
                                total_sessions_completed = EXCLUDED.total_sessions_completed;
                        """, (u_id, c_id, exp, help_r, avail, sessions))
                        
                # Seed Resources
                fac_id = user_map["Dr. Sarah Jenkins"]
                data_dir = os.path.join(os.path.dirname(__file__), 'data')
                meta_file = os.path.join(data_dir, 'ppt_metadata.json')
                if os.path.exists(meta_file):
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        all_metadata = json.load(f)
                    for res in all_metadata:
                        res_title = res.get("title", "")
                        res_url = res.get("url", "")
                        res_meta = res.get("metadata", {})
                        res_concept_name = res_meta.get("concept", "")
                        
                        c_id = concept_map.get(res_concept_name)
                        if c_id:
                            cur.execute("""
                                INSERT INTO resources (faculty_id, concept_id, title, resource_type, url, metadata)
                                VALUES (%s, %s, %s, 'Slides', %s, %s)
                                ON CONFLICT DO NOTHING;
                            """, (fac_id, c_id, res_title, res_url, json.dumps(res_meta)))
                
            conn.commit()
            print("Neon PostgreSQL seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding Neon database: {e}")

@app.on_event("startup")
async def startup_event():
    init_database()

# Endpoints
@app.get("/api/health")
async def health():
    return {"status": "ok", "db": "PostgreSQL Neon Active"}

@app.get("/api/doubts")
async def get_doubts(subject: str = "All"):
    # Fetch doubts joined with student user profiles, subject name, and concept name
    query = """
        SELECT d.id, d.title, d.raw_query as "rawQuery", d.difficulty, d.intent, 
               d.detected_misconception as "misconception", d.status, d.created_at, d.points,
               u.full_name as "studentName", u.academic_year as "studentYear", u.avatar_url as "studentAvatar",
               s.name as "subject", c.name as "concept"
        FROM doubts d
        JOIN users u ON d.student_id = u.id
        LEFT JOIN subjects s ON d.subject_id = s.id
        LEFT JOIN concepts c ON d.concept_id = c.id
    """
    params = []
    if subject != "All":
        query += " WHERE s.name = %s"
        params.append(subject)
        
    query += " ORDER BY d.created_at DESC"
    
    doubts_rows = run_query(query, params, fetch_all=True)
    if doubts_rows is None:
        doubts_rows = []
        
    # Map answers array for each doubt
    for d in doubts_rows:
        ans_query = """
            SELECT a.id, a.content, a.explanation_style as "style", a.is_ai_verified as "isAiVerified", a.is_faculty_verified as "isFacultyVerified",
                   a.verification_state as "verificationState", u.full_name as "authorName", u.avatar_url as "authorAvatar"
            FROM answers a
            JOIN users u ON a.author_id = u.id
            WHERE a.doubt_id = %s
            ORDER BY a.created_at ASC
        """
        answers = run_query(ans_query, [d['id']], fetch_all=True)
        d['answers'] = answers if answers else []
        d['id'] = str(d['id'])
        d['created_at'] = str(d['created_at'])
        d['timestamp'] = d['created_at']
        
    return doubts_rows

class DoubtRequest(BaseModel):
    student_id: str = "alex.morgan@studybuddy.edu"
    title: str
    raw_query: str

@app.post("/api/ask")
@app.post("/api/doubts")
async def ask_doubt(request: DoubtRequest):
    raw_query = request.raw_query
    
    # AI Classification scan
    tokens = tokenize(raw_query)
    keywords = get_keywords(tokens)
    
    best_match = None
    max_score = -1.0
    
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
    query_lower = raw_query.lower()
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
            
    # Lookup foreign key IDs
    subj_row = run_query("SELECT id FROM subjects WHERE name = %s;", [best_match["subject"]], fetch_one=True)
    subj_id = subj_row['id'] if subj_row else None
    
    topic_row = run_query("SELECT id FROM topics WHERE name = %s AND subject_id = %s;", [best_match["topic"], subj_id], fetch_one=True)
    topic_id = topic_row['id'] if topic_row else None
    
    concept_row = run_query("SELECT id FROM concepts WHERE name = %s AND topic_id = %s;", [concept["conceptName"], topic_id], fetch_one=True)
    concept_id = concept_row['id'] if concept_row else None
    
    # Get student ID
    user_row = run_query("SELECT id FROM users WHERE email = %s;", [request.student_id], fetch_one=True)
    if not user_row:
        # Fallback to Alex Morgan
        user_row = run_query("SELECT id FROM users WHERE email = 'alex.morgan@studybuddy.edu';", fetch_one=True)
    student_id = user_row['id'] if user_row else None
    
    # Deduct points from student user
    run_query("UPDATE users SET points = GREATEST(0, points - 15) WHERE id = %s;", [student_id], commit=True)
    
    title = raw_query.split('?')[0] + '?' if '?' in raw_query else raw_query + '?'
    detected_misconception = concept["misconception"] if is_misconception_triggered else "No common misconception active. Query aligns with canonical understanding."
    
    # Generate RAG embedding
    query_embedding = None
    try:
        query_embedding = embeddings.embed_query(raw_query)
    except Exception as e:
        print(f"Error embedding query: {e}")
        
    # Check if a highly similar answered doubt already exists (RAG Semantic caching)
    existing_resolved = None
    if query_embedding:
        try:
            # Order by pgvector cosine distance
            match_row = run_query("""
                SELECT d.id, a.content, a.verification_state, (d.embedding <=> %s::vector) as distance
                FROM doubts d
                JOIN answers a ON a.doubt_id = d.id
                WHERE d.embedding IS NOT NULL
                ORDER BY distance LIMIT 1
            """, [query_embedding], fetch_one=True)
            if match_row and match_row['distance'] < 0.20:
                existing_resolved = match_row
        except Exception as e:
            print(f"Error querying semantic cache: {e}")

    if existing_resolved:
        # Re-award the deducted points since the answer already existed immediately!
        run_query("UPDATE users SET points = points + 15 WHERE id = %s;", [student_id], commit=True)
        return {
            "id": str(existing_resolved['id']),
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
            "graphPath": generate_graph_path(best_match["topic"], concept),
            "explanation": {
                "Step-by-step": f"[Retrieved Existing Answer] {existing_resolved['content']}",
                "Analogy": f"[Retrieved Existing Answer] {existing_resolved['content']}",
                "Technical": f"[Retrieved Existing Answer] {existing_resolved['content']}"
            },
            "resources": [],
            "cacheHit": True
        }

    # Falling back to RAG Gemini response generator if no cache hit
    answer_text = ""
    if rag_chain:
        try:
            answer_text = rag_chain.invoke(raw_query)
        except Exception as e:
            print(f"Gemini LLM chain error: {e}")
            answer_text = "Course resources are currently offline. Peer mentors have been notified to provide an explanation!"
    else:
        answer_text = "AI Teaching Assistant is currently offline. Peer mentors have been notified to explain!"

    # Save new doubt record to doubts table
    insert_query = """
        INSERT INTO doubts (student_id, subject_id, topic_id, concept_id, title, raw_query, difficulty, intent, detected_misconception, auto_sort_confidence, status, points, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Open', 25, %s::vector)
        RETURNING id;
    """
    confidence_json = json.dumps({"topic": confidence, "concept": confidence})
    inserted = run_query(insert_query, [
        student_id, subj_id, topic_id, concept_id, title, raw_query, 
        concept.get("difficulty", "Beginner"), intent, detected_misconception, 
        confidence_json, query_embedding
    ], commit=True, fetch_one=True)
    
    # Save the provisional AI answer
    ai_user = run_query("SELECT id FROM users WHERE email = 'ai@studybuddy.com';", fetch_one=True)
    if ai_user and inserted:
        run_query("""
            INSERT INTO answers (doubt_id, author_id, content, explanation_style, is_ai_verified, is_faculty_verified, verification_state)
            VALUES (%s, %s, %s, 'Step-by-step', TRUE, FALSE, 'AI_REVIEWED');
        """, [inserted['id'], ai_user['id'], answer_text], commit=True)

    # Fetch resources matching the concept
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
        "graphPath": generate_graph_path(best_match["topic"], concept),
        "explanation": generate_explanations(concept["conceptName"]),
        "resources": matching_resources if matching_resources else []
    }
    
    return result

class AnswerRequest(BaseModel):
    content: str
    authorEmail: str = "rahul.sharma@studybuddy.edu"

@app.post("/api/doubts/{doubt_id}/answers")
async def add_answer(doubt_id: str, request: AnswerRequest):
    content = request.content
    
    if not content.strip():
        raise HTTPException(status_code=400, detail="Empty answer content")
        
    user_row = run_query("SELECT id FROM users WHERE email = %s;", [request.authorEmail], fetch_one=True)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    author_id = user_row['id']
    
    # Get doubt points bounty
    doubt_row = run_query("SELECT points FROM doubts WHERE id = %s;", [doubt_id], fetch_one=True)
    bounty = doubt_row['points'] if doubt_row else 25
    
    # Insert answer
    ans_query = """
        INSERT INTO answers (doubt_id, author_id, content, explanation_style, is_ai_verified, is_faculty_verified, verification_state)
        VALUES (%s, %s, %s, 'Technical', FALSE, FALSE, 'Reviewing')
        RETURNING id;
    """
    inserted = run_query(ans_query, [doubt_id, author_id, content], commit=True, fetch_one=True)
    
    # Update doubt status
    run_query("UPDATE doubts SET status = 'Resolved' WHERE id = %s;", [doubt_id], commit=True)
    
    # Award base points immediately to author
    run_query("UPDATE users SET points = points + %s WHERE id = %s;", [bounty, author_id], commit=True)
    
    return {
        "success": True,
        "answerId": str(inserted['id']) if inserted else "",
        "bountyAwarded": bounty
    }

@app.post("/api/answers/{answer_id}/verify")
async def verify_answer(answer_id: str):
    run_query("""
        UPDATE answers 
        SET is_faculty_verified = TRUE, verification_state = 'FACULTY_VERIFIED' 
        WHERE id = %s;
    """, [answer_id], commit=True)
    
    # Award +15 points to author
    author_row = run_query("SELECT author_id FROM answers WHERE id = %s;", [answer_id], fetch_one=True)
    if author_row:
        author_id = author_row['author_id']
        run_query("UPDATE users SET points = points + 15 WHERE id = %s;", [author_id], commit=True)
        
    return {"success": True, "message": "Answer verified by Faculty. +15 points awarded."}

class VerifyAiRequest(BaseModel):
    verified: bool

@app.post("/api/answers/{answer_id}/verify_ai")
async def verify_ai_answer(answer_id: str, request: VerifyAiRequest):
    if request.verified:
        run_query("""
            UPDATE answers 
            SET is_ai_verified = TRUE, verification_state = 'AI_REVIEWED' 
            WHERE id = %s;
        """, [answer_id], commit=True)
        
        # Award +10 points to author
        author_row = run_query("SELECT author_id FROM answers WHERE id = %s;", [answer_id], fetch_one=True)
        if author_row:
            author_id = author_row['author_id']
            run_query("UPDATE users SET points = points + 10 WHERE id = %s;", [author_id], commit=True)
            
    return {"success": True, "message": "AI verification state synchronized."}

class ValidateRequest(BaseModel):
    query: str
    answer: str
    concept: str

@app.post("/api/validate_answer")
async def validate_answer(request: ValidateRequest):
    query = request.query
    answer = request.answer
    concept = request.concept
    
    if not answer.strip():
        return {"verified": False, "reason": "Answer is empty."}
        
    # Get resources from database dynamically
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
async def get_leaderboard():
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
async def get_user(email: str):
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
async def update_user_points(email: str, request: PointsRequest):
    row = run_query("SELECT id, points FROM users WHERE email = %s;", [email], fetch_one=True)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
        
    new_points = max(0, row['points'] + request.diff)
    run_query("UPDATE users SET points = %s WHERE id = %s;", [new_points, row['id']], commit=True)
    
    return {"success": True, "points": new_points}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
