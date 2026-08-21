/**
 * StudyBuddy — Core Data Engine (Aligned with NeonDB PostgreSQL Schema & PS-01 Spec)
 */

const STUDY_BUDDY_DATA = {
  // Taxonomy Hierarchy (Subject -> Topic -> Concept -> Sub-concept)
  taxonomy: [
    {
      subjectId: "aaaaaaaa-0000-0000-0000-000000000001",
      subjectName: "Computer Science",
      topics: [
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000001",
          topicName: "Algorithms",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000001",
              conceptName: "Binary Search",
              subConcept: "Sorted Array Requirement",
              difficulty: "Beginner",
              intent: "Conceptual",
              canonicalSummary: "Divide-and-conquer search requiring monotonic ordering.",
              misconception: "Binary search works on unsorted data",
              prerequisites: ["Arrays", "Monotonic Ordering"],
              confidence: { topic: 0.98, concept: 0.99 }
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000002",
              conceptName: "Recursion",
              subConcept: "Base Case & Call Stack",
              difficulty: "Beginner",
              intent: "Conceptual",
              canonicalSummary: "Self-referencing function execution requiring terminal state.",
              misconception: "Recursion has no stopping condition and executes forever",
              prerequisites: ["Functions", "Conditionals"],
              confidence: { topic: 0.95, concept: 0.98 }
            },
            {
              conceptId: "cccccccc-0000-0000-0000-000000000003",
              conceptName: "Depth-First Search (DFS)",
              subConcept: "Graph Traversal with Call Stack",
              difficulty: "Intermediate",
              intent: "Conceptual",
              canonicalSummary: "Graph search exploring deepest branch before backtracking.",
              misconception: "DFS can only be implemented recursively and fails on cyclic graphs",
              prerequisites: ["Recursion", "Stack Data Structure", "Graph Adjacency"],
              confidence: { topic: 0.96, concept: 0.98 }
            }
          ]
        },
        {
          topicId: "bbbbbbbb-0000-0000-0000-000000000003",
          topicName: "Neural Networks & Optimization",
          concepts: [
            {
              conceptId: "cccccccc-0000-0000-0000-000000000004",
              conceptName: "Backpropagation",
              subConcept: "Softmax & Cross-Entropy Gradient",
              difficulty: "Advanced",
              intent: "Problem Solving",
              canonicalSummary: "Chain-rule gradient computation across network layers.",
              misconception: "Softmax derivatives require individual Jacobian matrix inversion",
              prerequisites: ["Multivariate Calculus", "Chain Rule", "Log-Likelihood Loss"],
              confidence: { topic: 0.94, concept: 0.97 }
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
  initialDoubts: [
    {
      id: "eeeeeeee-0000-0000-0000-000000000001",
      studentName: "Alex Morgan",
      studentYear: "3rd Year",
      studentAvatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150",
      rawQuery: "Why does DFS need recursion? What happens if we don't use it?",
      title: "Why does DFS need recursion?",
      subject: "Computer Science",
      topic: "Algorithms",
      concept: "Depth-First Search (DFS)",
      subConcept: "Graph Traversal with Call Stack",
      difficulty: "Intermediate",
      intent: "Conceptual",
      misconception: "DFS can only be implemented recursively and fails without recursion",
      prerequisites: ["Recursion", "Stack (LIFO)", "Graph Adjacency"],
      confidence: { topic: 0.96, concept: 0.98 },
      status: "Resolved",
      timestamp: "20 mins ago",
      similarCount: 4,
      answers: [
        {
          authorName: "Rahul Sharma (Peer Mentor)",
          authorAvatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&q=80&w=150",
          style: "Step-by-step",
          isFacultyValidated: true,
          content: "DFS does NOT strictly require recursion! Recursion simply utilizes the CPU's internal Call Stack to store backtracking points. You can implement DFS iteratively using an explicit Stack (LIFO data structure) with `while (!stack.isEmpty())`. Recursion is just syntax sugar for a stack!"
        }
      ],
      understandingCheck: {
        id: "gggggggg-0000-0000-0000-000000000001",
        question: "Which data structure is fundamentally used to convert a recursive DFS into an iterative one?",
        options: ["Queue (FIFO)", "Stack (LIFO)", "Binary Heap", "Hash Table"],
        correctIndex: 1,
        explanation: "The computer's call stack is a LIFO stack. Replacing function calls with an explicit Stack replicates DFS iteratively."
      }
    },
    {
      id: "eeeeeeee-0000-0000-0000-000000000002",
      studentName: "Priya Patel",
      studentYear: "3rd Year",
      studentAvatar: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150",
      rawQuery: "Clarification on Backpropagation gradient calculation for Softmax with Cross-Entropy Loss",
      title: "Softmax & Cross-Entropy gradient cancellation",
      subject: "Computer Science",
      topic: "Neural Networks & Optimization",
      concept: "Backpropagation",
      subConcept: "Softmax & Cross-Entropy Gradient",
      difficulty: "Advanced",
      intent: "Problem Solving",
      misconception: "Requires explicit Jacobian matrix computation",
      prerequisites: ["Chain Rule", "Log-Likelihood"],
      confidence: { topic: 0.94, concept: 0.97 },
      status: "Resolved",
      timestamp: "1 hour ago",
      similarCount: 6,
      answers: [
        {
          authorName: "Dr. Sarah Jenkins (Faculty Lead)",
          authorAvatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=250",
          style: "Technical",
          isFacultyValidated: true,
          content: "When deriving ∂L/∂z_i = ∑_j (∂L/∂y_hat_j) * (∂y_hat_j/∂z_i), the summation over the Kronecker delta (δ_ij) causes cross-terms to cancel out, leaving the elegant and efficient result: (y_hat_i - y_i)."
        }
      ],
      understandingCheck: {
        id: "gggggggg-0000-0000-0000-000000000002",
        question: "What is the final simplified gradient of Cross-Entropy Loss with Softmax logits z_i?",
        options: ["(y_hat_i * y_i)", "(y_hat_i - y_i)", "1 / (1 + e^-z_i)", "y_hat_i^2 - 1"],
        correctIndex: 1,
        explanation: "The Softmax-with-Cross-Entropy derivative simplifies directly to prediction error: (y_hat_i - y_i)."
      }
    },
    {
      id: "eeeeeeee-0000-0000-0000-000000000003",
      studentName: "Jordan Hayes",
      studentYear: "2nd Year",
      studentAvatar: "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&q=80&w=150",
      rawQuery: "Why doesn't binary search work on my array [5, 2, 8, 1, 9]?",
      title: "Binary search failing on unsorted list",
      subject: "Computer Science",
      topic: "Algorithms",
      concept: "Binary Search",
      subConcept: "Sorted Array Requirement",
      difficulty: "Beginner",
      intent: "Debugging",
      misconception: "Binary search works on unsorted data",
      prerequisites: ["Arrays", "Monotonic Ordering"],
      confidence: { topic: 0.98, concept: 0.99 },
      status: "Open",
      timestamp: "Just now",
      similarCount: 8,
      answers: [],
      understandingCheck: {
        id: "gggggggg-0000-0000-0000-000000000003",
        question: "What is the mandatory prerequisite condition for Binary Search to guarantee correct results?",
        options: ["Elements must be unique", "Data must be stored in a linked list", "Array must be monotonically sorted", "Array size must be a power of 2"],
        correctIndex: 2,
        explanation: "Binary search relies on sorted order to eliminate half the search space on each comparison."
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

  saveDoubts(doubts) {
    localStorage.setItem("studybuddy_doubts", JSON.stringify(doubts));
  },

  addDoubt(newDoubt) {
    const doubts = this.getDoubts();
    doubts.unshift(newDoubt);
    this.saveDoubts(doubts);
    return doubts;
  },

  resolveDoubt(doubtId, answerData) {
    const doubts = this.getDoubts();
    const doubt = doubts.find(d => d.id === doubtId);
    if (doubt) {
      doubt.status = "Resolved";
      if (!doubt.answers) doubt.answers = [];
      doubt.answers.push(answerData);
      this.saveDoubts(doubts);
    }
    return doubts;
  },

  getCurrentUser() {
    const user = localStorage.getItem("studybuddy_current_user");
    if (user) {
      try { return JSON.parse(user); } catch (e) {}
    }
    return {
      id: "11111111-0000-0000-0000-000000000001",
      name: "Alex Morgan",
      role: "student",
      year: "3rd Year",
      email: "alex.morgan@studybuddy.edu",
      avatar: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150"
    };
  },

  setCurrentUser(user) {
    localStorage.setItem("studybuddy_current_user", JSON.stringify(user));
  }
};
