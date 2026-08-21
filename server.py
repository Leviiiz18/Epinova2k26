import os
import json
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
    return jsonify({"status": "ok", "engine": "Python AutoSort 1.0"})

@app.route('/classify', methods=['POST'])
def classify():
    data = request.get_json() or {}
    query = data.get('query', '')
    
    if not query.strip():
        return jsonify({"error": "Empty query"}), 400
    
    tokens = tokenize(query)
    keywords = get_keywords(tokens)
    
    # Run scoring scan
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
                    
    # Default fallback if match is extremely weak
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
    
    # Classify intent
    intent = "Conceptual"
    query_lower = query.lower()
    if any(word in query_lower for word in ['error', 'bug', 'fail', 'wrong', 'output', 'null', 'incorrect', 'debug', 'broken', 'fix', 'why not', "doesn't work", "does not work", "failing"]):
        intent = "Debugging"
    elif any(word in query_lower for word in ['calculate', 'solve', 'derive', 'formula', 'math', 'equation', 'proof', 'compute', 'value', 'differentiation', 'derivative']):
        intent = "Problem Solving"
    elif any(word in query_lower for word in ['exam', 'quiz', 'test', 'grade', 'midterm', 'final', 'marks', 'practice']):
        intent = "Exam Prep"
        
    # Misconception check
    is_misconception_triggered = False
    if "misconception" in concept and concept["misconception"]:
        mis_words = get_keywords(tokenize(concept["misconception"]))
        matches = len([w for w in mis_words if w in tokens])
        if matches >= min(2, len(mis_words)):
            is_misconception_triggered = True
            
    # Load PPT resources matching the concept
    all_resources = load_ppt_metadata()
    matching_resources = [
        res for res in all_resources
        if res.get("metadata", {}).get("concept", "").lower() == concept["conceptName"].lower()
    ]
    
    result = {
        "subject": best_match["subject"],
        "topic": best_match["topic"],
        "concept": concept["conceptName"],
        "subConcept": concept.get("subConcept", ""),
        "difficulty": concept.get("difficulty", "Beginner"),
        "intent": intent,
        "misconception": concept["misconception"] if is_misconception_triggered else "No common misconception active. Query aligns with canonical understanding.",
        "isMisconceptionTriggered": is_misconception_triggered,
        "prerequisites": concept.get("prerequisites", []),
        "confidence": confidence,
        "graphPath": generate_graph_path(best_match["topic"], concept),
        "explanation": generate_explanations(concept["conceptName"]),
        "resources": matching_resources
    }
    
    return jsonify(result)


if __name__ == '__main__':
    print("Starting StudyBuddy Auto-Sort Python Server...")
    app.run(host='127.0.0.1', port=5000, debug=True)
