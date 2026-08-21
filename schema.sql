    -- ==============================================================================
    -- STUDYBUDDY DATABASE SCHEMA FOR NEON POSTGRESQL (PS-01 SPECIFICATION)
    -- ==============================================================================

    -- 1. EXTENSIONS
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    -- CREATE EXTENSION IF NOT EXISTS "vector"; -- Enable when pgvector is active on Neon

    -- 2. ROLES
    CREATE TABLE IF NOT EXISTS roles (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) UNIQUE NOT NULL, -- 'student', 'peer_mentor', 'faculty', 'admin'
        description TEXT
    );

    -- 3. USERS
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(120) NOT NULL,
        role_id INT REFERENCES roles(id) ON DELETE RESTRICT,
        avatar_url VARCHAR(500),
        academic_year VARCHAR(50), -- '1st Year', '2nd Year', '3rd Year', '4th Year', 'Faculty'
        department VARCHAR(100) DEFAULT 'Computer Science & Engineering',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 4. TAXONOMY: SUBJECTS -> TOPICS -> CONCEPTS (Knowledge Graph Foundation)
    CREATE TABLE IF NOT EXISTS subjects (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        code VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(150) NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS topics (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
        name VARCHAR(150) NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS concepts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
        name VARCHAR(150) NOT NULL,
        sub_concept VARCHAR(150),
        difficulty_level VARCHAR(20) DEFAULT 'Beginner', -- 'Beginner', 'Intermediate', 'Advanced'
        canonical_summary TEXT,
        common_misconception TEXT
    );

    -- 5. KAG CONCEPT RELATIONSHIPS (Prerequisites & Related Concepts)
    CREATE TABLE IF NOT EXISTS concept_relationships (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
        required_prerequisite_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
        relationship_type VARCHAR(50) DEFAULT 'REQUIRES', -- 'REQUIRES', 'RELATED_TO', 'DEPENDS_ON'
        notes TEXT
    );

    -- 6. PEER PROFILES (Peer Matching Intelligence)
    CREATE TABLE IF NOT EXISTS peer_profiles (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
        expertise_score DECIMAL(3, 2) DEFAULT 0.85,
        helpfulness_rating DECIMAL(3, 2) DEFAULT 4.90,
        availability_status VARCHAR(20) DEFAULT 'Available', -- 'Available', 'Busy', 'Offline'
        total_sessions_completed INT DEFAULT 0
    );

    -- 7. DOUBTS (With Auto-Sort AI Metadata)
    CREATE TABLE IF NOT EXISTS doubts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        student_id UUID REFERENCES users(id) ON DELETE CASCADE,
        subject_id UUID REFERENCES subjects(id) ON DELETE SET NULL,
        topic_id UUID REFERENCES topics(id) ON DELETE SET NULL,
        concept_id UUID REFERENCES concepts(id) ON DELETE SET NULL,
        title VARCHAR(300) NOT NULL,
        raw_query TEXT NOT NULL,
        difficulty VARCHAR(20) DEFAULT 'Beginner',
        intent VARCHAR(50) DEFAULT 'Conceptual', -- 'Conceptual', 'Debugging', 'Problem Solving', 'Exam Prep'
        detected_misconception TEXT,
        auto_sort_confidence JSONB, -- {"topic": 0.94, "concept": 0.97}
        status VARCHAR(30) DEFAULT 'Open', -- 'Open', 'In Review', 'Resolved'
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 8. ANSWERS & PEER EXPLANATIONS
    CREATE TABLE IF NOT EXISTS answers (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        doubt_id UUID REFERENCES doubts(id) ON DELETE CASCADE,
        author_id UUID REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        explanation_style VARCHAR(30) DEFAULT 'Step-by-step', -- 'Simple', 'Technical', 'Analogy', 'Visual', 'Step-by-step'
        is_faculty_validated BOOLEAN DEFAULT FALSE,
        helpfulness_upvotes INT DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 9. UNDERSTANDING CHECKS (Verification Engine)
    CREATE TABLE IF NOT EXISTS understanding_checks (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
        micro_question TEXT NOT NULL,
        options JSONB NOT NULL, -- Array of 4 options
        correct_option_index INT NOT NULL,
        explanation TEXT NOT NULL
    );

    -- 10. STUDENT LEARNING PROGRESS & MASTERY MODEL
    CREATE TABLE IF NOT EXISTS learning_progress (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        student_id UUID REFERENCES users(id) ON DELETE CASCADE,
        concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
        mastery_score DECIMAL(3, 2) DEFAULT 0.20, -- 0.00 to 1.00
        evidence_count INT DEFAULT 1,
        misconception_status VARCHAR(50) DEFAULT 'Identified', -- 'None', 'Identified', 'Resolved'
        last_checked TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, concept_id)
    );

    -- 11. FACULTY RESOURCES
    CREATE TABLE IF NOT EXISTS resources (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        faculty_id UUID REFERENCES users(id) ON DELETE CASCADE,
        concept_id UUID REFERENCES concepts(id) ON DELETE CASCADE,
        title VARCHAR(200) NOT NULL,
        resource_type VARCHAR(50) DEFAULT 'Article', -- 'Article', 'Video', 'Slides', 'Code'
        url VARCHAR(500) NOT NULL,
        metadata JSONB, -- Extended metadata for auto-sorting (e.g. {"slideCount": 24, "difficulty": "Intermediate", "keyConcepts": [...]})
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 12. INDEXES FOR HIGH-SPEED QUERYING
    CREATE INDEX IF NOT EXISTS idx_doubts_student ON doubts(student_id);
    CREATE INDEX IF NOT EXISTS idx_doubts_concept ON doubts(concept_id);
    CREATE INDEX IF NOT EXISTS idx_doubts_status ON doubts(status);
    CREATE INDEX IF NOT EXISTS idx_learning_progress_student ON learning_progress(student_id);
    CREATE INDEX IF NOT EXISTS idx_peer_profiles_concept ON peer_profiles(concept_id);
