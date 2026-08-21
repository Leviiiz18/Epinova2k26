import os
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

dotenv_path = os.path.join(os.path.dirname(__file__), 'env')
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def run_query(query, params=None, commit=False, fetch_one=False, fetch_all=False):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query, params)
        if commit:
            conn.commit()
        
        result = None
        if fetch_one:
            result = cur.fetchone()
        elif fetch_all:
            result = cur.fetchall()
            
        return result
    except Exception as e:
        print(f"Database Query Error: {e} for query: {query}")
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def init_db():
    print("Initializing Neon PostgreSQL database...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Execute schema.sql if tables do not exist
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            # Filter comments
            clean_lines = []
            for line in schema_sql.split('\n'):
                if not line.strip().startswith('--'):
                    clean_lines.append(line)
            clean_sql = '\n'.join(clean_lines)
            
            # Split by semicolon and run clean executions to avoid transaction errors
            for statement in clean_sql.split(';'):
                stmt = statement.strip()
                if stmt:
                    cur.execute(stmt)
            
        # 2. Alter tables to add new columns if not exist
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS points INT DEFAULT 100;")
        cur.execute("ALTER TABLE doubts ADD COLUMN IF NOT EXISTS points INT DEFAULT 25;")
        cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS is_ai_verified BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE answers ADD COLUMN IF NOT EXISTS is_faculty_verified BOOLEAN DEFAULT FALSE;")
        
        # 3. Seed roles
        roles = ['student', 'peer_mentor', 'faculty', 'admin']
        for r in roles:
            cur.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;", (r,))
            
        # Get role ids
        cur.execute("SELECT id, name FROM roles;")
        role_map = {row[1]: row[0] for row in cur.fetchall()}
        
        # 4. Seed default users
        default_users = [
            ("alex.morgan@studybuddy.edu", "Alex Morgan", "student", "3rd Year", "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150", 100),
            ("rahul.sharma@studybuddy.edu", "Rahul Sharma", "peer_mentor", "4th Year", "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=150", 350),
            ("elena.vance@studybuddy.edu", "Elena Vance", "peer_mentor", "4th Year", "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=150", 280),
            ("priya.patel@studybuddy.edu", "Priya Patel", "peer_mentor", "3rd Year", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150", 210),
            ("jordan.hayes@studybuddy.edu", "Jordan Hayes", "peer_mentor", "2nd Year", "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&q=80&w=150", 110),
            ("sarah.jenkins@studybuddy.edu", "Dr. Sarah Jenkins", "faculty", "Faculty", "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=250", 100)
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
            
        # 5. Seed Taxonomy (Subjects, Topics, Concepts)
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
                    ON CONFLICT DO NOTHING
                    RETURNING id;
                """, (subj_id, top_name, f"Topic: {top_name}"))
                top_row = cur.fetchone()
                if top_row:
                    top_id = top_row[0]
                else:
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
                        ON CONFLICT DO NOTHING
                        RETURNING id;
                    """, (top_id, con_name, sub_con, diff, summary, misconception))
                    con_row = cur.fetchone()
                    if con_row:
                        con_id = con_row[0]
                    else:
                        cur.execute("SELECT id FROM concepts WHERE topic_id = %s AND name = %s;", (top_id, con_name))
                        con_id = cur.fetchone()[0]
                    concept_map[con_name] = con_id
                    
        # 6. Seed Peer Profiles
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
                
        # 7. Seed Resources from load_ppt_metadata()
        fac_id = user_map["Dr. Sarah Jenkins"]
        all_metadata = load_ppt_metadata()
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
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing Neon database: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Load PPT metadata from the separated JSON file
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PPT_METADATA_FILE = os.path.join(DATA_DIR, 'ppt_metadata.json')

def load_ppt_metadata():
    try:
        if os.path.exists(PPT_METADATA_FILE):
            with open(PPT_METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading PPT metadata: {e}")
    return []

# Taxonomy dataset aligned with schema.sql and js/data.js
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

STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'arent', 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'cant', 'cannot', 'could',
    'did', 'didnt', 'do', 'does', 'doesnt', 'doing', 'dont', 'down', 'during', 'each', 'few', 'for', 'from', 'further',
    'had', 'hadnt', 'has', 'hasnt', 'have', 'havent', 'having', 'he', 'hed', 'hell', 'hes', 'her', 'here', 'heres',
    'hers', 'herself', 'him', 'himself', 'his', 'how', 'hows', 'i', 'id', 'ill', 'im', 'ive', 'if', 'in', 'into', 'is',
    'isnt', 'it', 'its', 'itself', 'lets', 'me', 'more', 'most', 'mustnt', 'my', 'myself', 'no', 'nor', 'not', 'of',
    'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same',
    'shant', 'she', 'shed', 'shell', 'shes', 'should', 'shouldnt', 'so', 'some', 'such', 'than', 'that', 'thats',
    'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'theres', 'these', 'they', 'theyd', 'theyll',
    'theyre', 'theyve', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasnt',
    'we', 'wed', 'well', 'were', 'weve', 'werent', 'what', 'whats', 'when', 'whens', 'where', 'wheres', 'which',
    'while', 'who', 'whos', 'whom', 'why', 'whys', 'with', 'wont', 'would', 'wouldnt', 'you', 'youd', 'youll',
    'youre', 'youve', 'your', 'yours', 'yourself', 'yourselves'
}

def tokenize(text):
    if not text:
        return []
    words = re.sub(r'[^\w\s]', ' ', text.lower()).split()
    return [w for w in words if len(w) > 1]

def get_keywords(tokens):
    return [t for t in tokens if t not in STOP_WORDS]

def calculate_match_score(query_keywords, target_text):
    if not target_text:
        return 0.0
    target_tokens = tokenize(target_text)
    if not target_tokens:
        return 0.0
    
    matches = 0.0
    for kw in query_keywords:
        if kw in target_tokens:
            matches += 1.0
        elif any(kw in tok or tok in kw for tok in target_tokens):
            matches += 0.5
            
    return matches / len(query_keywords) if query_keywords else 0.0

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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "engine": "Python AutoSort 1.0 (PostgreSQL active)"})

@app.route('/doubts', methods=['GET'])
def get_doubts():
    subject_filter = request.args.get('subject', 'All')
    
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
    if subject_filter != 'All':
        query += " WHERE s.name = %s"
        params.append(subject_filter)
        
    query += " ORDER BY d.created_at DESC"
    
    doubts_rows = run_query(query, params, fetch_all=True)
    if doubts_rows is None:
        doubts_rows = []
        
    # Map answers array for each doubt
    for d in doubts_rows:
        ans_query = """
            SELECT a.id, a.content, a.explanation_style as "style", a.is_ai_verified as "isAiVerified", a.is_faculty_verified as "isFacultyVerified",
                   u.full_name as "authorName", u.avatar_url as "authorAvatar"
            FROM answers a
            JOIN users u ON a.author_id = u.id
            WHERE a.doubt_id = %s
            ORDER BY a.created_at ASC
        """
        answers = run_query(ans_query, [d['id']], fetch_all=True)
        d['answers'] = answers if answers else []
        d['created_at'] = d['created_at'].isoformat() if d['created_at'] else 'Just now'
        d['timestamp'] = d['created_at']
        
    return jsonify(doubts_rows)

@app.route('/doubts', methods=['POST'])
def create_doubt():
    data = request.get_json() or {}
    raw_query = data.get('rawQuery', '')
    
    if not raw_query.strip():
        return jsonify({"error": "Empty doubt query"}), 400
        
    # AI Classification logic
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
            
    # Lookup foreign key IDs in Postgres
    subj_row = run_query("SELECT id FROM subjects WHERE name = %s;", [best_match["subject"]], fetch_one=True)
    subj_id = subj_row['id'] if subj_row else None
    
    topic_row = run_query("SELECT id FROM topics WHERE name = %s AND subject_id = %s;", [best_match["topic"], subj_id], fetch_one=True)
    topic_id = topic_row['id'] if topic_row else None
    
    concept_row = run_query("SELECT id FROM concepts WHERE name = %s AND topic_id = %s;", [concept["conceptName"], topic_id], fetch_one=True)
    concept_id = concept_row['id'] if concept_row else None
    
    # Get student ID (Alex Morgan)
    user_row = run_query("SELECT id FROM users WHERE email = %s;", ["alex.morgan@studybuddy.edu"], fetch_one=True)
    student_id = user_row['id'] if user_row else None
    
    title = raw_query.split('?')[0] + '?' if '?' in raw_query else raw_query + '?'
    detected_misconception = concept["misconception"] if is_misconception_triggered else "No common misconception active. Query aligns with canonical understanding."
    
    insert_query = """
        INSERT INTO doubts (student_id, subject_id, topic_id, concept_id, title, raw_query, difficulty, intent, detected_misconception, auto_sort_confidence, status, points)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Open', 25)
        RETURNING id;
    """
    confidence_json = json.dumps({"topic": confidence, "concept": confidence})
    inserted = run_query(insert_query, [
        student_id, subj_id, topic_id, concept_id, title, raw_query, 
        concept.get("difficulty", "Beginner"), intent, detected_misconception, 
        confidence_json
    ], commit=True, fetch_one=True)
    
    # Deduct points from asking student (Alex Morgan)
    run_query("UPDATE users SET points = GREATEST(0, points - 15) WHERE id = %s;", [student_id], commit=True)
    
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
        "id": inserted['id'],
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
    
    return jsonify(result)

@app.route('/doubts/<doubt_id>/answers', methods=['POST'])
def add_answer(doubt_id):
    data = request.get_json() or {}
    content = data.get('content', '')
    author_email = data.get('authorEmail', 'rahul.sharma@studybuddy.edu')
    
    if not content.strip():
        return jsonify({"error": "Empty answer content"}), 400
        
    user_row = run_query("SELECT id FROM users WHERE email = %s;", [author_email], fetch_one=True)
    if not user_row:
        return jsonify({"error": "User not found"}), 404
    author_id = user_row['id']
    
    # Get doubt bounty points
    doubt_row = run_query("SELECT points FROM doubts WHERE id = %s;", [doubt_id], fetch_one=True)
    bounty = doubt_row['points'] if doubt_row else 25
    
    # Insert answer record
    ans_query = """
        INSERT INTO answers (doubt_id, author_id, content, explanation_style, is_ai_verified, is_faculty_verified)
        VALUES (%s, %s, %s, 'Technical', FALSE, FALSE)
        RETURNING id;
    """
    inserted = run_query(ans_query, [doubt_id, author_id, content], commit=True, fetch_one=True)
    
    # Update doubt status
    run_query("UPDATE doubts SET status = 'Resolved' WHERE id = %s;", [doubt_id], commit=True)
    
    # Award base bounty points to answering student
    run_query("UPDATE users SET points = points + %s WHERE id = %s;", [bounty, author_id], commit=True)
    
    return jsonify({
        "success": True,
        "answerId": inserted['id'],
        "bountyAwarded": bounty
    })

@app.route('/answers/<answer_id>/verify', methods=['POST'])
def verify_answer(answer_id):
    run_query("UPDATE answers SET is_faculty_verified = TRUE WHERE id = %s;", [answer_id], commit=True)
    
    # Award additional +15 points to author
    author_row = run_query("SELECT author_id FROM answers WHERE id = %s;", [answer_id], fetch_one=True)
    if author_row:
        author_id = author_row['author_id']
        run_query("UPDATE users SET points = points + 15 WHERE id = %s;", [author_id], commit=True)
        
    return jsonify({"success": True, "message": "Answer verified by Faculty. +15 points awarded."})

@app.route('/answers/<answer_id>/verify_ai', methods=['POST'])
def verify_ai_answer(answer_id):
    data = request.get_json() or {}
    verified = data.get('verified', False)
    
    if verified:
        run_query("UPDATE answers SET is_ai_verified = TRUE WHERE id = %s;", [answer_id], commit=True)
        # Award additional +10 points to author
        author_row = run_query("SELECT author_id FROM answers WHERE id = %s;", [answer_id], fetch_one=True)
        if author_row:
            author_id = author_row['author_id']
            run_query("UPDATE users SET points = points + 10 WHERE id = %s;", [author_id], commit=True)
            
    return jsonify({"success": True, "message": "AI verification state updated in PostgreSQL."})

@app.route('/validate_answer', methods=['POST'])
def validate_answer():
    data = request.get_json() or {}
    query = data.get('query', '')
    answer = data.get('answer', '')
    concept = data.get('concept', '')
    
    if not answer.strip():
        return jsonify({"verified": False, "reason": "Answer is empty."})
        
    # Get resources from PostgreSQL database dynamically
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
        return jsonify({
            "verified": True,
            "reason": f"{reason} AI verified alignment on key terms: {', '.join(overlap[:3])}."
        })
    else:
        return jsonify({
            "verified": False,
            "reason": f"{reason} Insufficient technical overlap with course materials."
        })

@app.route('/leaderboard', methods=['GET'])
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
    
    # Map ranks
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
            
    return jsonify(rows)

@app.route('/user/<email>', methods=['GET'])
def get_user(email):
    row = run_query("""
        SELECT u.id, u.full_name as "name", u.academic_year as "year", u.avatar_url as "avatar", u.points,
               r.name as "role"
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.email = %s;
    """, [email], fetch_one=True)
    if not row:
        return jsonify({"error": "User not found"}), 404
    return jsonify(row)

@app.route('/user/<email>/points', methods=['POST'])
def update_user_points_route(email):
    data = request.get_json() or {}
    diff = data.get('diff', 0)
    
    row = run_query("SELECT id, points FROM users WHERE email = %s;", [email], fetch_one=True)
    if not row:
        return jsonify({"error": "User not found"}), 404
        
    new_points = max(0, row['points'] + diff)
    run_query("UPDATE users SET points = %s WHERE id = %s;", [new_points, row['id']], commit=True)
    
    return jsonify({"success": True, "points": new_points})


if __name__ == '__main__':
    init_db()
    print("Starting StudyBuddy Auto-Sort Python Server...")
    app.run(host='127.0.0.1', port=5000, debug=True)
