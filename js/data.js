/**
 * StudyBuddy — Core Data Engine (Aligned with NeonDB PostgreSQL Schema & PS-01 Spec)
 */

const STUDY_BUDDY_DATA = {
  // Taxonomy Hierarchy (Subject -> Topic -> Concept -> Sub-concept)
  taxonomy: [
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000002",
      subjectName: "C Programming",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000004",
          topicName: "C Basics",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000005",
              conceptName: "C Variables & Data Types",
              subConcept: "Variables & Types",
              difficulty: "Beginner",
              canonicalSummary: "Introduction to memory storage and standard representations in C.",
              misconception: "C variables do not have fixed data types",
              prerequisites: ["Syntax"]
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000006",
              conceptName: "Control Flow & Conditionals",
              subConcept: "Branching & Loops",
              difficulty: "Beginner",
              canonicalSummary: "Conditional execution and loop constructs.",
              misconception: "Loops always terminate automatically",
              prerequisites: ["C Variables & Data Types"]
            }
          ]
        }
      ]
    },
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000003",
      subjectName: "Leadership & Relationship Management Skills",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000005",
          topicName: "Leadership",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000007",
              conceptName: "Leadership Foundations",
              subConcept: "Styles & Roles",
              difficulty: "Beginner",
              canonicalSummary: "Overview of management styles and team leadership principles.",
              misconception: "Leadership is only for senior executives",
              prerequisites: []
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000008",
              conceptName: "Emotional Intelligence",
              subConcept: "Self-Awareness & Empathy",
              difficulty: "Beginner",
              canonicalSummary: "Methods of managing relationships and self-awareness.",
              misconception: "Emotional intelligence is a soft skill with no measurable impact",
              prerequisites: ["Leadership Foundations"]
            }
          ]
        }
      ]
    },
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000004",
      subjectName: "C# Programming",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000006",
          topicName: "Object Oriented C#",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000009",
              conceptName: "C# Object Oriented Programming",
              subConcept: "Classes & Interfaces",
              difficulty: "Intermediate",
              canonicalSummary: "OOP principles implemented in C# syntax.",
              misconception: "Structs and classes behave identically in C#",
              prerequisites: ["C Programming"]
            }
          ]
        }
      ]
    },
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000005",
      subjectName: "Machine Learning",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000007",
          topicName: "Supervised Algorithms",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000010",
              conceptName: "Supervised Learning",
              subConcept: "Regression & Classification",
              difficulty: "Intermediate",
              canonicalSummary: "Methods for mapping inputs to labeled outputs.",
              misconception: "Supervised learning can fit any non-linear function without overfitting",
              prerequisites: ["Calculus", "Linear Algebra"]
            }
          ]
        }
      ]
    },
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000006",
      subjectName: "Artificial Intelligence",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000008",
          topicName: "Heuristic Optimization",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000011",
              conceptName: "Genetic Algorithms",
              subConcept: "Evolutionary Operators",
              difficulty: "Intermediate",
              canonicalSummary: "Heuristic optimization modeling natural selection.",
              misconception: "Genetic algorithms guarantee mathematical global maximum convergence",
              prerequisites: ["Probability & Statistics"]
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000012",
              conceptName: "Heuristic Search",
              subConcept: "A* Pathfinding",
              difficulty: "Intermediate",
              canonicalSummary: "Optimal search procedures utilizing heuristic weights.",
              misconception: "Admissible heuristics can overestimate the actual remaining path cost",
              prerequisites: ["Depth-First Search (DFS)"]
            }
          ]
        }
      ]
    },
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000007",
      subjectName: "Digital Image Processing",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000009",
          topicName: "Image Representation",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000013",
              conceptName: "Digital Image Processing Basics",
              subConcept: "Sampling & Quantization",
              difficulty: "Intermediate",
              canonicalSummary: "Discretization of continuous image frames.",
              misconception: "Higher sampling rates always increase perceptual quality infinitely",
              prerequisites: []
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000014",
              conceptName: "Image Enhancement",
              subConcept: "Histogram Transformations",
              difficulty: "Intermediate",
              canonicalSummary: "Methods of modifying contrast and spatial domain filters.",
              misconception: "Histogram equalization is a lossless operation",
              prerequisites: ["Digital Image Processing Basics"]
            }
          ]
        }
      ]
    },
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000008",
      subjectName: "Advanced Web Technologies",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000010",
          topicName: "Architectures",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000015",
              conceptName: "Advanced Web Architectures",
              subConcept: "REST & MVC Patterns",
              difficulty: "Advanced",
              canonicalSummary: "Architectural models of web communication protocols.",
              misconception: "REST API calls must be stateless on server networks",
              prerequisites: []
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000016",
              conceptName: "Client-Server State Management",
              subConcept: "JSON Web Tokens (JWT)",
              difficulty: "Advanced",
              canonicalSummary: "Securing web routes and sessions using credentials.",
              misconception: "JWT payload signatures encrypt the payload data",
              prerequisites: ["Advanced Web Architectures"]
            }
          ]
        }
      ]
    },
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000009",
      subjectName: "Soft Computing",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000011",
          topicName: "Approximate Reasoning",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000017",
              conceptName: "Soft Computing Fundamentals",
              subConcept: "Imprecise Models",
              difficulty: "Advanced",
              canonicalSummary: "Overview of neural, fuzzy, and genetic computing paradigms.",
              misconception: "Soft computing yields exact analytical solutions",
              prerequisites: []
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000018",
              conceptName: "Fuzzy Inference Systems",
              subConcept: "Membership Defuzzification",
              difficulty: "Advanced",
              canonicalSummary: "Mapping crisp inputs to fuzzy values and defuzzifying.",
              misconception: "Fuzzy logic is based on random probability distributions",
              prerequisites: ["Soft Computing Fundamentals"]
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000019",
              conceptName: "Neuro-Fuzzy Hybridization",
              subConcept: "ANFIS Systems",
              difficulty: "Advanced",
              canonicalSummary: "Integrating neural learning features with fuzzy systems.",
              misconception: "Fuzzy rules cannot be adjusted automatically",
              prerequisites: ["Fuzzy Inference Systems", "Backpropagation"]
            }
          ]
        }
      ]
    }
  ],

  // Peer Mentors (Matching Engine Data)
  peers: [
    {
      id: "22222222-0000-0000-0000-000000000001",
      name: "Rahul Sharma",
      year: "4th Year Senior",
      avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=150",
      expertiseConcept: "Depth-First Search (DFS)",
      expertiseScore: 0.95,
      helpfulnessRating: 4.92,
      availability: "Available Now",
      sessionsCompleted: 28,
      matchReason: "Ranked #1 in Graph Algorithms & 95% explanation success rate"
    },
    {
      id: "22222222-0000-0000-0000-000000000002",
      name: "Elena Vance",
      year: "4th Year Senior",
      avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=150",
      expertiseConcept: "Backpropagation",
      expertiseScore: 0.92,
      helpfulnessRating: 4.88,
      availability: "Available Today",
      sessionsCompleted: 19,
      matchReason: "Top peer in Neural Network math & TA for Machine Learning"
    }
  ],

  // Knowledge Gaps & Doubts
  initialDoubts: [],

  // Faculty Resources (Specifically PPTs/Slides for Auto-Sorting & Identification)
  resources: [
    {
      id: "rrrrrrrr-0000-0000-0000-000000000001",
      facultyId: "33333333-0000-0000-0000-000000000001", // Dr. Sarah Jenkins
      conceptId: "cccccccc-0000-0000-0000-000000000003", // DFS
      title: "Lecture 8: Advanced Graph Traversals & Call Stack Mechanics",
      resourceType: "Slides",
      url: "/materials/dfs_slides.pptx",
      metadata: {
        subject: "Computer Science",
        topic: "Algorithms",
        concept: "Depth-First Search (DFS)",
        difficulty: "Intermediate",
        slideCount: 24,
        keyConcepts: ["DFS", "Recursion", "Backtracking", "Call Stack"],
        prerequisites: ["Recursion", "Stack Data Structure"],
        fileSize: "4.2MB",
        format: "PPTX",
        description: "Comprehensive guide on DFS traversal, stack simulation, and complexity analysis."
      }
    },
    {
      id: "rrrrrrrr-0000-0000-0000-000000000002",
      facultyId: "33333333-0000-0000-0000-000000000002", // Prof. David Kumar
      conceptId: "cccccccc-0000-0000-0000-000000000001", // Binary Search
      title: "Lecture 3: Divide and Conquer — Binary Search & Sorted Assertions",
      resourceType: "Slides",
      url: "/materials/binary_search_slides.pptx",
      metadata: {
        subject: "Computer Science",
        topic: "Algorithms",
        concept: "Binary Search",
        difficulty: "Beginner",
        slideCount: 18,
        keyConcepts: ["Binary Search", "Divide & Conquer", "Sorted Order", "Logarithmic Time"],
        prerequisites: ["Arrays"],
        fileSize: "3.1MB",
        format: "PPTX",
        description: "Introduction to binary search logic, implementation, and explaining the sorted array prerequisite."
      }
    },
    {
      id: "rrrrrrrr-0000-0000-0000-000000000003",
      facultyId: "33333333-0000-0000-0000-000000000001", // Dr. Sarah Jenkins
      conceptId: "cccccccc-0000-0000-0000-000000000004", // Backpropagation
      title: "Lecture 12: Neural Network Gradients & Softmax-Cross-Entropy Optimization",
      resourceType: "Slides",
      url: "/materials/backpropagation_math.pptx",
      metadata: {
        subject: "Computer Science",
        topic: "Neural Networks & Optimization",
        concept: "Backpropagation",
        difficulty: "Advanced",
        slideCount: 32,
        keyConcepts: ["Backpropagation", "Softmax", "Cross-Entropy", "Gradient Descent", "Chain Rule"],
        prerequisites: ["Multivariate Calculus", "Linear Algebra"],
        fileSize: "8.5MB",
        format: "PPTX",
        description: "Mathematical derivation of the Softmax and Cross-Entropy loss derivative, simplified via Kronecker delta cancellation."
      }
    }
  ]
};

// Database local mock storage
const DB = {
  getDoubts() {
    const saved = localStorage.getItem("studybuddy_doubts");
    if (!saved) {
      localStorage.setItem("studybuddy_doubts", JSON.stringify(STUDY_BUDDY_DATA.initialDoubts));
      return STUDY_BUDDY_DATA.initialDoubts;
    }
    try { return JSON.parse(saved); } catch (e) { return STUDY_BUDDY_DATA.initialDoubts; }
  },

  async syncDoubts() {
    try {
      const response = await fetch("http://localhost:8000/api/doubts");
      if (response.ok) {
        const backendDoubts = await response.json();
        if (backendDoubts) {
          backendDoubts.forEach(d => {
            if (d.subject && d.topic && typeof STUDY_BUDDY_DATA !== 'undefined') {
              const taxonomyMatch = STUDY_BUDDY_DATA.taxonomy.find(t => t.subjectName === d.subject);
              if (taxonomyMatch) {
                const topicIndex = taxonomyMatch.topics.findIndex(t => t.topicName === d.topic);
                if (topicIndex !== -1) {
                  d.subject = `Unit ${topicIndex + 1}: ${d.topic}`;
                }
              }
            }
          });
          this.saveDoubts(backendDoubts);
          return backendDoubts;
        }
      }
    } catch (e) {
      console.warn("Could not sync with real backend API:", e);
    }
    return this.getDoubts();
  },


  saveDoubts(doubts) {
    localStorage.setItem("studybuddy_doubts", JSON.stringify(doubts));
  },

  getResources() {
    const saved = localStorage.getItem("studybuddy_resources");
    if (!saved) {
      localStorage.setItem("studybuddy_resources", JSON.stringify(STUDY_BUDDY_DATA.resources));
      return STUDY_BUDDY_DATA.resources;
    }
    try { return JSON.parse(saved); } catch (e) { return STUDY_BUDDY_DATA.resources; }
  },

  getResourcesByConcept(conceptName) {
    const resources = this.getResources();
    return resources.filter(r => r.metadata.concept.toLowerCase() === conceptName.toLowerCase() || r.metadata.concept.toLowerCase().includes(conceptName.toLowerCase()));
  },

  async addDoubt(newDoubt) {
    try {
      const email = (newDoubt.studentName || "").includes("Alex") ? "alex.morgan@studybuddy.edu" :
                    (newDoubt.studentName || "").includes("Rahul") ? "rahul.sharma@studybuddy.edu" :
                    (newDoubt.studentName || "").includes("Elena") ? "elena.vance@studybuddy.edu" :
                    (newDoubt.studentName || "").includes("Priya") ? "priya.patel@studybuddy.edu" : "jordan.hayes@studybuddy.edu";
                    
      const response = await fetch(`http://localhost:8000/api/doubts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: email,
          title: newDoubt.title,
          raw_query: newDoubt.rawQuery,
          exam_mode: newDoubt.examMode || "none"
        })
      });
      if (response.ok) {
        const data = await response.json();
        await this.syncDoubts();
        return data;
      }
    } catch (e) {
      console.warn("Backend unavailable for addDoubt (RAG won't trigger):", e);
      // Fallback
      const doubts = this.getDoubts();
      doubts.unshift(newDoubt);
      this.saveDoubts(doubts);
    }
    
    return this.getDoubts();
  },

  async resolveDoubt(doubtId, answerData) {
    const doubts = this.getDoubts();
    const doubt = doubts.find(d => d.id === doubtId);
    if (doubt) {
      doubt.status = "Resolved";
      if (!doubt.answers) doubt.answers = [];
      doubt.answers.push(answerData);
      this.saveDoubts(doubts);
    }
    
    try {
      const email = answerData.authorEmail || (
                    answerData.authorName.includes("Alex") ? "alex.morgan@studybuddy.edu" :
                    answerData.authorName.includes("Rahul") ? "rahul.sharma@studybuddy.edu" :
                    answerData.authorName.includes("Elena") ? "elena.vance@studybuddy.edu" :
                    answerData.authorName.includes("Priya") ? "priya.patel@studybuddy.edu" : "jordan.hayes@studybuddy.edu");
                    
      const response = await fetch(`http://localhost:8000/api/doubts/${doubtId}/answers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: answerData.content,
          authorEmail: email
        })
      });
      if (response.ok) {
        await this.syncDoubts();
      }
    } catch (e) {
      console.warn("Offline resolveDoubt fallback:", e);
    }
    return doubts;
  },

  async deleteAnswer(answerId) {
    try {
      const response = await fetch(`http://localhost:8000/api/answers/${answerId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        await this.syncDoubts();
        return true;
      }
    } catch (e) {
      console.warn("Error deleting answer:", e);
    }
    return false;
  },

  async updateAnswer(answerId, content) {
    try {
      const response = await fetch(`http://localhost:8000/api/answers/${answerId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content })
      });
      if (response.ok) {
        await this.syncDoubts();
        return true;
      }
    } catch (e) {
      console.warn("Error updating answer:", e);
    }
    return false;
  },

  async deleteDoubt(doubtId) {
    try {
      const response = await fetch(`http://localhost:8000/api/doubts/${doubtId}`, {
        method: "DELETE"
      });
      if (response.ok) {
        await this.syncDoubts();
        return true;
      }
    } catch (e) {
      console.warn("Error deleting doubt:", e);
    }
    return false;
  },

  async updateDoubt(doubtId, title, rawQuery) {
    try {
      const response = await fetch(`http://localhost:8000/api/doubts/${doubtId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, raw_query: rawQuery })
      });
      if (response.ok) {
        await this.syncDoubts();
        return true;
      }
    } catch (e) {
      console.warn("Error updating doubt:", e);
    }
    return false;
  },

  async likeAnswer(answerId) {
    try {
      const response = await fetch(`http://localhost:8000/api/answers/${answerId}/like`, {
        method: "POST"
      });
      if (response.ok) {
        await this.syncDoubts();
        return await response.json();
      }
    } catch (e) {
      console.warn("Error liking answer:", e);
    }
    return null;
  },

  async rateAnswer(answerId, rating, userEmail) {
    try {
      const response = await fetch(`http://localhost:8000/api/answers/${answerId}/rate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, userEmail })
      });
      if (response.ok) {
        await this.syncDoubts();
        return await response.json();
      }
    } catch (e) {
      console.warn("Error rating answer:", e);
    }
    return null;
  },

  async addReply(answerId, authorName, authorAvatar, content) {
    try {
      const response = await fetch(`http://localhost:8000/api/answers/${answerId}/replies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ authorName, authorAvatar, content })
      });
      if (response.ok) {
        await this.syncDoubts();
        return true;
      }
    } catch (e) {
      console.warn("Error adding reply:", e);
    }
    return false;
  },


  async setAnswerAiVerified(doubtId, answerIdx, isVerified) {
    const doubts = this.getDoubts();
    const doubt = doubts.find(d => d.id === doubtId);
    if (doubt && doubt.answers && doubt.answers[answerIdx]) {
      doubt.answers[answerIdx].isAiVerified = isVerified;
      this.saveDoubts(doubts);
      
      const answer = doubt.answers[answerIdx];
      if (answer.id) {
        try {
          await fetch(`http://localhost:8000/api/answers/${answer.id}/verify_ai`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ verified: isVerified })
          });
        } catch (e) {
          console.warn("AI verification sync failed:", e);
        }
      }
    }
    return doubts;
  },

  async setAnswerFacultyVerified(doubtId, answerIdx, isVerified) {
    const doubts = this.getDoubts();
    const doubt = doubts.find(d => d.id === doubtId);
    if (doubt && doubt.answers && doubt.answers[answerIdx]) {
      doubt.answers[answerIdx].isFacultyVerified = isVerified;
      this.saveDoubts(doubts);
      
      const answer = doubt.answers[answerIdx];
      if (answer.id) {
        try {
          await fetch(`http://localhost:8000/api/answers/${answer.id}/verify`, {
            method: "POST"
          });
        } catch (e) {
          console.warn("Faculty verification sync failed:", e);
        }
      }
    }
    return doubts;
  },

  getCurrentUser() {
    const user = localStorage.getItem("studybuddy_current_user");
    if (user) {
      try {
        const u = JSON.parse(user);
        if (u.points === undefined) u.points = 100;
        return u;
      } catch (e) {}
    }
    const defaultUser = {
      id: "11111111-0000-0000-0000-000000000001",
      name: "Alex Morgan",
      role: "student",
      year: "3rd Year",
      email: "alex.morgan@studybuddy.edu",
      avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150",
      points: 100
    };
    this.setCurrentUser(defaultUser);
    return defaultUser;
  },

  setCurrentUser(user) {
    localStorage.setItem("studybuddy_current_user", JSON.stringify(user));
  },

  async updateUserPoints(diff) {
    const user = this.getCurrentUser();
    user.points = Math.max(0, (user.points || 0) + diff);
    this.setCurrentUser(user);
    if (window.onPointsUpdate) {
      window.onPointsUpdate(user.points, diff);
    }
    
    try {
      const response = await fetch(`http://localhost:8000/api/user/${user.email}/points`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ diff: diff })
      });
      if (response.ok) {
        const resData = await response.json();
        user.points = resData.points;
        this.setCurrentUser(user);
      }
    } catch (e) {
      console.warn("Points sync with DB failed:", e);
    }
    return user.points;
  },

  getFacultyById(facId) {
    const defaultFaculty = {
      id: facId || "fac-ai-01",
      name: "Dr. Sarah Jenkins",
      title: "Lead Faculty - Computer Science",
      domain: "Artificial Intelligence & Data Structures",
      email: "sarah.jenkins@studybuddy.edu",
      avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=250",
      status: "online"
    };
    return defaultFaculty;
  },

  getFacultyForDomain(domain) {
    return {
      id: "fac-ai-01",
      name: "Dr. Sarah Jenkins",
      title: `Faculty Lead - ${domain || "Computer Science"}`,
      domain: domain || "Computer Science & Engineering",
      email: "sarah.jenkins@studybuddy.edu",
      avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=250",
      status: "online"
    };
  }
};
