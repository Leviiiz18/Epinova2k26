/**
 * StudyBuddy - Auto-Sort NLP Classification Engine
 */
const AutoSortEngine = {
  // Common stop words to filter out before matching
  STOP_WORDS: new Set([
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
  ]),

  tokenize(text) {
    return text.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(token => token.length > 1);
  },

  getKeywords(tokens) {
    return tokens.filter(token => !this.STOP_WORDS.has(token));
  },

  // Calculate keyword match score (exact & partial overlap)
  calculateMatchScore(queryKeywords, targetText) {
    if (!targetText) return 0;
    const targetTokens = this.tokenize(targetText);
    if (targetTokens.length === 0) return 0;
    
    let matches = 0;
    queryKeywords.forEach(keyword => {
      if (targetTokens.includes(keyword)) {
        matches += 1.0;
      } else if (targetTokens.some(tok => tok.includes(keyword) || keyword.includes(tok))) {
        matches += 0.5;
      }
    });

    return matches / Math.max(1, targetTokens.length);
  },

  classify(rawQuery) {
    const tokens = this.tokenize(rawQuery);
    const keywords = this.getKeywords(tokens);

    if (keywords.length === 0) {
      return this.getFallbackClassification();
    }

    let bestMatch = null;
    let maxScore = -1;

    // Scan taxonomy dynamically from js/data.js
    const data = STUDY_BUDDY_DATA;
    data.taxonomy.forEach(subject => {
      subject.topics.forEach(topic => {
        topic.concepts.forEach(concept => {
          const nameScore = this.calculateMatchScore(keywords, concept.conceptName) * 4.0;
          const subScore = this.calculateMatchScore(keywords, concept.subConcept) * 2.0;
          const summaryScore = this.calculateMatchScore(keywords, concept.canonicalSummary) * 1.5;
          const misconceptionScore = this.calculateMatchScore(keywords, concept.misconception) * 1.5;

          const totalScore = nameScore + subScore + summaryScore + misconceptionScore;

          if (totalScore > maxScore) {
            maxScore = totalScore;
            bestMatch = {
              subjectName: subject.subjectName,
              topicName: topic.topicName,
              concept: concept,
              score: totalScore
            };
          }
        });
      });
    });

    if (!bestMatch || maxScore < 0.05) {
      return this.getFallbackClassification();
    }

    const matchedConcept = bestMatch.concept;
    let confidence = 0.50 + Math.min(0.49, maxScore / 4.0);

    // Determine intent from query words
    let intent = "Conceptual";
    const rawLower = rawQuery.toLowerCase();
    if (/\b(error|bug|fail|wrong|output|null|incorrect|debug|broken|fix|why not|doesn't work|does not work|failing)\b/.test(rawLower)) {
      intent = "Debugging";
    } else if (/\b(calculate|solve|derive|formula|math|equation|proof|compute|value|differentiation|derivative)\b/.test(rawLower)) {
      intent = "Problem Solving";
    } else if (/\b(exam|quiz|test|grade|midterm|final|marks|practice)\b/.test(rawLower)) {
      intent = "Exam Prep";
    }

    // Check if typical misconception is triggered
    let isMisconceptionTriggered = false;
    if (matchedConcept.misconception) {
      const misconceptionWords = this.getKeywords(this.tokenize(matchedConcept.misconception));
      let matchCount = 0;
      misconceptionWords.forEach(w => {
        if (tokens.includes(w)) matchCount++;
      });
      // If query shares multiple descriptive words with standard misconception
      if (matchCount >= Math.min(2, misconceptionWords.length)) {
        isMisconceptionTriggered = true;
      }
    }

    // Graph path
    const graphPath = this.generateGraphPath(bestMatch.topicName, matchedConcept);
    const explanations = this.generateTargetedExplanation(matchedConcept, intent);

    return {
      subject: bestMatch.subjectName,
      topic: bestMatch.topicName,
      concept: matchedConcept.conceptName,
      subConcept: matchedConcept.subConcept,
      difficulty: matchedConcept.difficulty,
      intent: intent,
      misconception: isMisconceptionTriggered ? matchedConcept.misconception : "No common misconception active. Query aligns with canonical understanding.",
      isMisconceptionTriggered: isMisconceptionTriggered,
      prerequisites: matchedConcept.prerequisites || [],
      confidence: confidence,
      graphPath: graphPath,
      explanation: explanations
    };
  },

  generateGraphPath(topicName, concept) {
    const path = [];
    path.push({ name: topicName, type: "Topic" });
    path.push({ name: concept.conceptName, type: "Concept" });
    if (concept.prerequisites && concept.prerequisites.length > 0) {
      concept.prerequisites.forEach(prereq => {
        path.push({ name: prereq, type: "Prerequisite" });
      });
    }
    return path;
  },

  generateTargetedExplanation(concept, intent) {
    const conceptName = concept.conceptName;
    
    if (conceptName === "Binary Search") {
      return {
        "Step-by-step": "1. Find the middle element of the sorted array.\n2. Compare target with the middle element.\n3. If target matches, return index.\n4. If target is smaller, repeat on left half.\n5. If target is larger, repeat on right half.\n*Note: Array must be sorted first!*",
        "Analogy": "Searching an unsorted list is like looking for a word in a dictionary where the pages are shuffled in random order—you'd have to check page-by-page. Sorting the array is what allows you to open directly to the middle page and know which direction to turn.",
        "Technical": "Binary search is a divide-and-conquer algorithm with O(log N) time complexity. It relies on the random-access property of arrays and strict monotonic ordering, where indices establish a transitive relationship: A[i] <= A[j] for all i < j."
      };
    } else if (conceptName === "Depth-First Search (DFS)") {
      return {
        "Step-by-step": "1. Push the start node onto the stack.\n2. Mark it as visited.\n3. While stack is not empty, pop the top node.\n4. Push all unvisited neighbors onto the stack, marking them visited.\n5. Repeat until all connected components are explored.",
        "Analogy": "DFS is like exploring a maze: you walk down a single path as far as you can go. When you hit a dead-end, you backtrack to the last fork in the road and try the other direction. Recursion handles this backtracking automatically using the call stack.",
        "Technical": "DFS visits graph vertices by traversing deep along each branch before backtracking. It operates in O(V + E) time. It uses a LIFO discipline, either implicitly via recursive runtime call stack frames or explicitly via a Stack data structure."
      };
    } else if (conceptName === "Backpropagation") {
      return {
        "Step-by-step": "1. Perform a forward pass to calculate predictions and loss.\n2. Compute the gradient of the loss with respect to output activation.\n3. Apply the mathematical chain rule layer by layer backwards.\n4. Multiply local derivatives to find parameter gradients.\n5. Update weights using gradient descent.",
        "Analogy": "Imagine a factory assembly line making toy cars. At the end, a quality checker flags errors. Backpropagation is like traced feedback going backwards along the line, telling each worker exactly how much their specific action contributed to the final defect.",
        "Technical": "Backpropagation computes the gradient of a loss function with respect to weights using the reverse-mode automatic differentiation chain rule: ∂L/∂w_ij = (∂L/∂z_j) * (∂z_j/∂w_ij). For Softmax with Cross-Entropy, the vector gradient simplifies directly to the error vector (y_hat - y)."
      };
    }

    return {
      "Step-by-step": `1. Break down the concept of ${conceptName}.\n2. Identify prerequisite concepts like ${concept.prerequisites ? concept.prerequisites.join(', ') : 'none'}.\n3. Apply fundamental equations or rules.\n4. Verify outputs against baseline assertions.`,
      "Analogy": `Understanding ${conceptName} is like constructing a building. The sub-concepts like ${concept.subConcept} are the building blocks, and without them, the structure collapses under pressure.`,
      "Technical": `The canonical system definition of ${conceptName} is: ${concept.canonicalSummary}. Implementation utilizes O(N) memory allocations with state representation constrained by prerequisite definitions.`
    };
  },

  getFallbackClassification() {
    return {
      subject: "Computer Science",
      topic: "Algorithms",
      concept: "Recursion",
      subConcept: "Base Case",
      difficulty: "Beginner",
      intent: "Conceptual",
      misconception: "No common misconception active.",
      isMisconceptionTriggered: false,
      prerequisites: ["Functions"],
      confidence: 0.35,
      graphPath: [
        { name: "Algorithms", type: "Topic" },
        { name: "Recursion", type: "Concept" }
      ],
      explanation: {
        "Step-by-step": "1. Identify the base case.\n2. Define recursive step.\n3. Verify call stack size.",
        "Analogy": "Like looking into two mirrors facing each other, reflecting infinitely until a terminal boundary breaks the loop.",
        "Technical": "Recursion calls a function from within itself, utilizing active stack frame contexts. Requires a strictly defined base case to avoid stack overflow."
      }
    };
  }
};
