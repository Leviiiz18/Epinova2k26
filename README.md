# StudyBuddy — AI-Powered Peer Learning Intelligence Platform

> **Full Build Plan — PS-01 College / Peer Learning**  
> Built around three technical pillars: **Auto-Sort**, **Semantic Search**, and **Knowledge-Augmented Generation (KAG)**.

---

## 🌟 Key Architecture & Pillars

```
ASK → AUTO-SORT → SEMANTIC SEARCH → KAG REASONING → LEARN → VERIFY → UPDATE KNOWLEDGE
```

1. **Auto-Sort AI Engine**: Structures natural language queries into taxonomy (*Subject, Topic, Concept, Sub-concept, Difficulty, Intent, Misconception, Prerequisites, Confidence*).
2. **Semantic Search**: Matches conceptually relevant existing peer solutions and ranked explanations.
3. **KAG Reasoning**: 2-hop graph reasoning over canonical concepts to identify prerequisite gaps.
4. **Learning Engine**: Multi-style AI explanations (*Step-by-step, Analogy, Technical*) and targeted interventions.
5. **Peer Matching Engine**: Ranks senior peer mentors by expertise score, helpfulness rating, and availability.
6. **Understanding Verification**: Micro-quiz assessment that updates the student's **Concept Mastery Model** in real-time.
7. **Faculty Intelligence**: Aggregated campus learning gap heatmaps, unresolved doubt clusters, and lecture recommendations.

---

## 🏛️ Database (NeonDB PostgreSQL)

- **`schema.sql`**: Full production DDL for 11 normalized tables (`roles`, `users`, `subjects`, `topics`, `concepts`, `concept_relationships`, `peer_profiles`, `doubts`, `answers`, `understanding_checks`, `learning_progress`, `resources`).
- **`dummy_data.txt`**: Curated seed dataset ready for copy-paste into Neon SQL Editor.
- **`.env.example`**: Connection string configuration template.

---

## 🚀 Getting Started

1. **Open Frontend**:
   - Double-click `index.html` to launch the platform in any web browser.
2. **Setup Neon PostgreSQL**:
   - Run the SQL queries in `schema.sql` inside your Neon console.
   - Insert seed records from `dummy_data.txt`.

---

## 📂 Repository Structure

```
├── assets/                  # Visual mockups and SVG preview assets
├── css/
│   └── style.css            # Kinetic Logic clean minimalist design system
├── js/
│   ├── app.js               # Application logic, toasts & modals
│   └── data.js              # State engine mirroring NeonDB schema
├── .env.example             # Database connection template
├── dummy_data.txt           # Formatted seed records & SQL statements
├── faculty-dashboard.html   # Faculty learning gap intelligence & doubt queue
├── index.html               # 3-section landing page (Purpose, Preview, Portals)
├── login.html               # Role-based authentication (Student / Faculty)
├── schema.sql               # PostgreSQL schema for NeonDB
├── student-dashboard.html   # Student Auto-Sort, KAG graph, and Verification
└── README.md
```
