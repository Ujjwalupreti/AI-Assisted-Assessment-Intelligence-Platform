# Project Report: AI-Powered Intelligent Assessment & Proctoring System (QIS)
## File 1: System Overview, End-to-End Working, and Technical Architecture

---

### 1. Executive Summary & Project Description

The **Question Intelligence System (QIS) and Assessment Platform** is an enterprise-grade academic evaluation environment that bridges modern generative artificial intelligence, local semantic search, computer vision, and cognitive pedagogical frameworks (Bloom’s Revised Taxonomy).

#### Core Problem Addressed
Traditional examination platforms suffer from critical structural weaknesses:
1. **Manual Assessment Authoring**: Educators spend hours crafting questions, balancing difficulty, and ensuring syllabus coverage, often resulting in repetitive, rote-memory questions.
2. **Cognitive Imbalance**: Exams frequently skew toward surface recall ("Remember") rather than analytical or evaluation skills ("Analyze", "Evaluate"), failing outcome-based education (OBE) goals.
3. **Descriptive / Subjective Grading Bottlenecks**: Grading long-form and short-form answers manually leads to delays, fatigue-driven scoring variances, and lack of actionable rubric-based feedback.
4. **Academic Dishonesty in Remote Testing**: Remote and unmonitored exams face integrity risks, including unauthorized tab switching, device usage, and proxy test-taking.
5. **Fixed, Static Difficulty**: Lack of real-time item response analysis prevents institutions from verifying whether a question labeled "Hard" was genuinely challenging for students.

#### Solution Overview
This platform solves these challenges through:
- **Automated Blueprint Balancing**: Automatically enforces multi-dimensional distribution constraints across Syllabus Topics, Difficulty Percentages (Easy/Medium/Hard), and Bloom’s Taxonomy levels.
- **RAG-Grounded Question Authoring**: Knowledge base ingestion enables syllabus-constrained question generation with verifiable citations.
- **Hybrid Subjective Grading**: Pairs small local semantic embedding models (`all-MiniLM-L6-v2`) with cloud LLM evaluation, providing explainable scoring with human-in-the-loop teacher override.
- **Edge-Assisted Dual-Layer Proctoring**: Real-time webcam analysis via OpenCV (facial presence/movement) and Ultralytics YOLOv8 (electronic contraband detection) coupled with browser lockdown.
- **Item Response Empirical Calibration**: Recalibrates predicted question difficulty against live student attempt metrics.

---

### 2. High-Level System Architecture

The application adopts a decoupled, multi-tier micro-modular architecture consisting of a React-based single-page application (SPA), a high-concurrency FastAPI backend gateway, a modular AI/ML pipeline, and a hybrid vector-relational persistence layer.

```mermaid
graph TD
    subgraph ClientLayer ["Client Presentation Layer (React 18 + Vite)"]
        TD["Teacher Dashboard & Blueprint Studio"]
        SD["Student Exam Environment (Lockdown + Proctoring)"]
        EID["Exam Intelligence & Analytics Dashboard"]
    end

    subgraph APILayer ["API Gateway & Routing Layer (FastAPI)"]
        AUTH_R["Auth & RBAC Router (/api/auth)"]
        EXAM_R["Exam Management Router (/api/exams)"]
        QIS_R["QIS Pipeline Router (/api/qis)"]
        RAG_R["RAG & Knowledge Router (/api/rag)"]
        PROC_R["Proctoring Stream Router (/api/proctoring)"]
        EVAL_R["Evaluation Router (/api/evaluate)"]
    end

    subgraph ServiceLayer ["Core Business & Intelligence Services"]
        QIS_PIPE["QIS Pipeline (Single Source of Truth)"]
        ASSEMBLER["Assessment & Slot Assembler (Greedy Optimization)"]
        RAG_CORE["RAG Engine (Chunking, Dense Retrieval)"]
        SUBJ_EVAL["Hybrid Subjective Evaluator"]
        PROC_CORE["Proctoring Core (YOLOv8 + OpenCV Haar)"]
    end

    subgraph AIModels ["AI / ML Model Layer"]
        ST_MODEL["Local Embedding: all-MiniLM-L6-v2 (384-d)"]
        YOLO_MODEL["Local Contraband Detector: YOLOv8n"]
        HAAR_MODEL["Face Detection: OpenCV Haar Cascade"]
        LLM_CLIENT["Cloud LLM: Gemini 1.5 Flash (JSON Schema Guarded)"]
    end

    subgraph DataLayer ["Hybrid Persistence Layer"]
        SQL_DB[("Relational DB: SQLite / PostgreSQL")]
        VEC_STORE[("Vector Store: DocumentChunk Embeddings")]
        SNAP_STORE[("Static Files: Flagged Proctoring Frames")]
    end

    ClientLayer --> APILayer
    APILayer --> ServiceLayer
    ServiceLayer --> AIModels
    ServiceLayer --> DataLayer
```

---

### 3. End-to-End System Working & Lifecycle

The examination lifecycle is divided into six distinct operational phases:

```mermaid
sequenceDiagram
    autonumber
    actor Teacher
    participant FE as Frontend (React)
    participant API as FastAPI Gateway
    participant QIS as QIS Pipeline / RAG
    participant DB as Database & Vector Store
    actor Student
    participant PROC as Vision Proctoring (YOLO/OpenCV)

    Note over Teacher, DB: Phase 1 & 2: Authoring, RAG & Exam Assembly
    Teacher->>FE: Ingest Syllabus Document (PDF/TXT)
    FE->>API: Upload Syllabus to /api/rag/upload
    API->>QIS: Chunk text & compute embeddings (all-MiniLM-L6-v2)
    QIS->>DB: Store DocumentChunks with 384-d vectors
    Teacher->>FE: Define Blueprint (Topics %, Difficulty %, Bloom %)
    FE->>API: Request Slot Assembly / Generation
    API->>QIS: Greedy Assembly + RAG Question Generation
    QIS-->>FE: Balanced Assessment Preview & Quality Audit
    Teacher->>FE: Finalize & Publish Exam

    Note over Student, DB: Phase 3 & 4: Authentication & Secure Testing
    Student->>FE: Login & Pre-Exam Check (Webcam & ID Capture)
    FE->>API: Submit Pre-Exam verification data
    API-->>FE: Issue Exam Session Token
    Student->>FE: Begin Exam (Enters Fullscreen Lockdown)
    loop Active Exam Session
        FE->>PROC: WebCam Frame Stream (Silent Sampling)
        PROC->>API: Detect Face / Phone (YOLOv8 + Haar)
        API->>DB: Record ProctoringEvent if violation detected
        Student->>FE: Fill Subjective & Objective Answers
    end
    Student->>FE: Submit Exam

    Note over Teacher, DB: Phase 5 & 6: Evaluation, Analytics & Review
    FE->>API: Final Submission Payload
    API->>DB: Save Attempts & Answers (Auto-grade MCQs)
    Teacher->>FE: Trigger Subjective AI Evaluation
    API->>QIS: Evaluate Subjective Answers (Semantic Search + Gemini)
    QIS->>DB: Store ai_suggested_marks, confidence & rationale
    Teacher->>FE: Review Proctoring Gallery & Override Grades
```

#### Detailed Breakdown of Each Phase

#### Phase 1: Knowledge Base Ingestion (RAG Pre-processing)
1. **Document Upload**: The instructor uploads course reference material (PDF, TXT, DOCX).
2. **Text Normalization & Chunking**: `backend/ai/rag/document_processor.py` strips extraneous control characters and partitions the syllabus into contiguous sliding chunks of ~500 characters with 100-character overlap.
3. **Dense Vector Generation**: Each chunk is embedded via the local `sentence-transformers/all-MiniLM-L6-v2` model into a 384-dimensional floating-point array.
4. **Relational Vector Storage**: The embedding is serialized and persisted into the `DocumentChunk` SQL table, indexed by `document_id`.

#### Phase 2: Blueprint Definition & Intelligent Exam Assembly
1. **Blueprint Configuration**: The teacher specifies target distributions:
   - **Topics**: e.g., Data Structures (40%), Algorithms (40%), Database Systems (20%).
   - **Difficulty Profile**: e.g., Easy (30%), Medium (50%), Hard (20%).
   - **Bloom's Cognitive Distribution**: e.g., Remember (20%), Understand (30%), Apply (30%), Analyze (15%), Evaluate (5%).
2. **Greedy Assessment Assembler**: `backend/ai/assessment_assembler.py` calculates integer quotas for each stratum. It iterates through the active `Question` bank, computing a fitness score for each item:
   $$\text{Score} = w_{\text{topic}} \cdot \mathbb{I}_{\text{topic}} + w_{\text{diff}} \cdot \mathbb{I}_{\text{diff}} + w_{\text{bloom}} \cdot \mathbb{I}_{\text{bloom}} + w_{\text{qual}} \cdot Q_{\text{score}} - w_{\text{dup}} \cdot D_{\text{risk}}$$
3. **Gap Resolution via RAG Generation**: If the question bank lacks sufficient items matching specific criteria (e.g., Hard + Analyze in Database Systems), `backend/ai/question_generator.py` retrieves relevant context chunks via cosine similarity and prompts the LLM to generate candidate questions strictly grounded in syllabus text.
4. **Slot Division**: When multiple examination slots (variants) are needed for staggered schedules, `backend/ai/slot_divider.py` partitions items such that all sets preserve identical mean quality, equalized difficulty percentages, and matched topic coverage.

#### Phase 3: Student Pre-Exam Authentication & Verification
1. **Multi-Factor Pre-Check**: The student undergoes a hardware test (microphone and camera permissions), captures a live facial baseline, and uploads an institutional student ID.
2. **Password Verification**: The student enters the exam session key, which is verified server-side.
3. **Session Minting**: An `ExamAttempt` row is instantiated with a status of `IN_PROGRESS`, locking the attempt to the student's user ID and active timestamp.

#### Phase 4: Proctored Exam Execution & Anti-Cheating Engine
1. **Client Lockdown**:
   - The browser enters HTML5 Fullscreen mode (`requestFullscreen`).
   - Blur/focus event listeners intercept unauthorized tab switching or application switching (`window.onblur`).
   - System clipboard interception disables copy, cut, paste, and text selection.
2. **Vision-Based Proctoring**:
   - The webcam stream samples periodic frames and sends them to `/api/proctoring/analyze-frame`.
   - **Face Presence Tracking**: OpenCV’s Haar Cascade classifier determines face presence. Absences lasting $>5$ seconds trigger a `FACE_MISSING` incident. Multiple faces trigger a `MULTIPLE_FACES` incident.
   - **Contraband Detection**: Ultralytics YOLOv8n evaluates frames for prohibited items (cell phones, laptops, tablets) with bounding box confidence $>0.50$.
3. **Audio Monitoring**: Web Audio API monitors ambient room volume using an `AudioContext` root-mean-square (RMS) detector, flagging sustained speaking or whispers.
4. **Non-Punitive Warning System**: Violations increment a client-side warning counter (up to 3 warnings). Once reached, an automatic submission is enforced. Every infraction captures a base64 image saved to `static/uploads/` and logs a permanent `ProctoringEvent` record for post-exam review.

#### Phase 5: Automated & Hybrid Evaluation
1. **Objective Evaluation**: MCQ questions are scored instantaneously via deterministic equality checks between student selection and the canonical `correct_option`.
2. **Subjective Evaluation Pipeline**: For descriptive answers:
   - The answer is evaluated via the hybrid AI evaluator (`ai/subjective_evaluator.py`).
   - If Cloud LLM is enabled, Gemini compares the student answer against the reference answer and rubric constraints, outputting suggested marks, conceptual reasoning, and a confidence score ($0.0 - 1.0$).
   - If confidence is $\ge 0.70$, `review_status` is marked `COMPLETED`.
   - If confidence is $< 0.70$ or ambiguity exists, `review_status` is marked `NEEDS_REVIEW` and flagged on the teacher dashboard.
   - If the LLM is offline, a local semantic embedding fallback computes vector similarity and marks alignment, ensuring zero downtime.

#### Phase 6: Analytics, Calibration & Teacher Override
1. **Teacher Audit**: The teacher inspects flagged questions, overrides suggested grades, and views proctoring snapshots.
2. **Item Calibration**: `analytics_routes.py` computes the empirical difficulty of each question based on actual student performance:
   $$D_{\text{empirical}} = \left( \frac{\text{Correct Submissions}}{\text{Total Submissions}} \right) \times 100$$
   This highlights calibration mismatches (e.g., questions predicted as "Easy" that $<30\%$ of students answered correctly).

---

### 4. Database Schema & Data Models

The persistence layer uses SQLAlchemy ORM mapping over a relational database.

```mermaid
erDiagram
    User ||--o{ Exam : "creates"
    User ||--o{ ExamAttempt : "undertakes"
    Exam ||--o{ Question : "contains"
    Exam ||--o{ ExamSlot : "schedules"
    Exam ||--o{ ExamAttempt : "has"
    Exam ||--o{ Result : "yields"
    ExamAttempt ||--o{ Answer : "submits"
    ExamAttempt ||--o{ ProctoringEvent : "logs"
    Question ||--o{ Answer : "answered_by"
    CourseDocument ||--o{ DocumentChunk : "chunked_into"

    User {
        int id PK
        string username
        string email
        string role "teacher | student | admin"
        string password_hash
        string enrollment_id
        boolean is_active
    }

    Exam {
        int id PK
        string title
        text description
        int duration_minutes
        string exam_type "Objective | Subjective | Mixed"
        boolean is_published
        string access_password
        text blueprint_json
        int creator_id FK
    }

    Question {
        int id PK
        int exam_id FK
        text text
        string question_type "MCQ | Subjective"
        string topic
        string difficulty "Easy | Medium | Hard"
        string bloom_level "Remember..Create"
        string option_a
        string option_b
        string option_c
        string option_d
        string correct_option
        text reference_answer
        text rubric
        float max_marks
        float ai_quality_score
        string duplicate_status
    }

    ExamAttempt {
        int id PK
        int exam_id FK
        int student_id FK
        datetime start_time
        datetime end_time
        string status "IN_PROGRESS | COMPLETED | TERMINATED"
        int warning_count
    }

    Answer {
        int id PK
        int attempt_id FK
        int question_id FK
        string selected_option
        text answer_text
        boolean is_correct
        float marks_awarded
        float ai_suggested_marks
        float ai_confidence
        text ai_explanation
        string review_status "COMPLETED | NEEDS_REVIEW"
        text teacher_feedback
    }

    ProctoringEvent {
        int id PK
        int attempt_id FK
        string event_type "TAB_SWITCH | PHONE_DETECTED | FACE_MISSING | AUDIO_NOISE"
        datetime timestamp
        string evidence_image_path
        text details
    }

    DocumentChunk {
        int id PK
        int document_id FK
        int chunk_index
        text chunk_text
        text embedding_json
        string model_name
    }
```

---

### 5. Architectural Quality Attributes & Non-Functional Guarantees

| Quality Attribute | Architectural Strategy | Code Implementation |
| :--- | :--- | :--- |
| **Fault Tolerance & Resilience** | Graceful degradation of AI modules. If Gemini API fails or times out (30s watchdog), the system falls back to local SentenceTransformers and heuristic classifiers. | `ai/llm_client.py`, `ai/subjective_evaluator.py`, `ai/bloom_classifier.py` |
| **Low Latency Proctoring** | Image inference is conducted asynchronously on sampled frames; lightweight models (`yolov8n.pt`, Haar cascades) process frames in $<60\text{ ms}$. | `backend/routes/main_routes.py` (`analyze_frame`) |
| **Deterministic Consistency** | Strict JSON schema parsing with regex boundary extraction prevents malformed LLM outputs from crashing backend handlers. | `ai/llm_client.py` (`generate_json`) |
| **Security & Privacy** | AES encryption on question transmission, zero plain-text storage of passwords (salted hashing), and role-based access control (RBAC) across all endpoints. | `auth_middleware.py`, `utils/encryption.js` |
| **Human-in-the-Loop** | AI recommendations and subjective evaluations are suggestions; teachers retain 100% override authority over final marks and proctoring penalties. | `routes/main_routes.py` (`override_grade`) |

---
*Next Document: `docs/02_ai_integration_and_mechanisms.md` for AI Architecture, RAG, and Minimal AI Semantic Search.*

