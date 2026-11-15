# QIS — Complete Existing Codebase Audit Report (Phase 1 Baseline)

**Document Version:** 1.0.0  
**Audit Date:** 14 November 2026  
**Auditor:** Senior Full-Stack AI Engineer & Security Auditor  
**Scope:** Subjective Answer Evaluation, Multi-Format Processing, AI Proctoring & Examination Integrity  
**Repository Working Directory:** `c:\Users\Hp\Downloads\PRoject\ai_project_copy`

---

## 1. Executive Summary & Verification Taxonomy

This audit establishes the ground-truth technical baseline of the QIS (AI-Assisted Assessment Intelligence Platform) repository. Every claim, path, function, endpoint, and database schema has been verified against actual repository files and executed test scripts.

### Status Classification Key:
- `IMPLEMENTED_AND_VERIFIED`: Exists in code, executed, and verified working.
- `IMPLEMENTED_BUT_BROKEN`: Exists in code, but fails during execution or contains critical defects.
- `PARTIALLY_IMPLEMENTED`: Core logic exists but lacks critical capabilities (e.g., text-only, no math/automata).
- `NOT_IMPLEMENTED`: Architectural component does not exist in the codebase.
- `NOT_TESTED`: Exists in code but lacks automated test verification.
- `BLOCKED`: Cannot execute due to external environment or missing credentials.

---

## 2. Component-by-Component Baseline Audit

### A. Subjective Evaluation Subsystem

| Feature / Component | Source File & Function | Endpoint / Table | Status | Audit Findings & Technical Evidence |
|---|---|---|---|---|
| **Subjective Evaluation Dispatcher** | `backend/ai/evaluation/subjective_evaluator.py`<br/>`evaluate_subjective_answer()` | `POST /exams/{exam_id}/evaluate` (in `main_routes.py` L988) | `PARTIALLY_IMPLEMENTED` | Supports text answers with LLM, SentenceTransformers, and difflib. Lacks specialized math (SymPy) and automata (DFA/NFA) evaluators. |
| **Tier 1: LLM + Rubric + RAG** | `backend/ai/evaluation/subjective_evaluator.py` L5-L68 | `ai/core/llm_client.py`<br/>`generate_json()` | `IMPLEMENTED_AND_VERIFIED` | Correctly passes question text, reference answer, and rubric into constrained prompt. Verified fallback on 404/timeout. |
| **Tier 2: Dense Semantic Vector Matching** | `backend/ai/evaluation/subjective_evaluator.py` L70-L136 | `SentenceTransformers`<br/>`all-MiniLM-L6-v2` | `IMPLEMENTED_AND_VERIFIED` | Encodes student text and reference text into 384-dim embeddings. Computes 60% cosine similarity + 40% rubric clause matrix. Verified in test suite. |
| **Tier 3: Heuristic String Fallback** | `backend/ai/evaluation/subjective_evaluator.py` L140-L161 | `difflib.SequenceMatcher` | `IMPLEMENTED_AND_VERIFIED` | Executes when ST or PyTorch is unavailable. Clamps score and forces `review_status = "NEEDS_REVIEW"`. |
| **Symbolic Mathematics Evaluation** | N/A | N/A | `NOT_IMPLEMENTED` | Math expressions are treated solely as raw text strings. No algebraic equivalence or step verification using SymPy exists. |
| **Automata (DFA/NFA) Formal Evaluation** | N/A | N/A | `NOT_IMPLEMENTED` | No formal 5-tuple verification, string simulation, or language equivalence engine exists in the current evaluator. |
| **Confidence & Review Routing** | `subjective_evaluator.py` L62, L117 | `Answer.review_status` | `IMPLEMENTED_AND_VERIFIED` | Sets `review_status = "NEEDS_REVIEW"` whenever confidence $< 0.70$. |
| **Teacher Grade Override** | `backend/routes/main_routes.py` L1062-L1096 | `PUT /answers/{answer_id}/grade` | `IMPLEMENTED_AND_VERIFIED` | Allows teacher to override `marks_awarded`, supply feedback, and automatically recalculates student attempt `Result.score`. |

---

### B. Answer Submission & Multi-Format Support

| Feature / Component | Source File & Function | Endpoint / Table | Status | Audit Findings & Technical Evidence |
|---|---|---|---|---|
| **Text Answer Submission** | `frontend/src/pages/StudentDashboard.jsx`<br/>`backend/routes/main_routes.py` L550 | `POST /exams/{exam_id}/submit` | `IMPLEMENTED_AND_VERIFIED` | Student submits dictionary of answers. Text answers persist to `Answer.answer_text`. |
| **Mathematical Equation Editor** | `frontend/src/pages/StudentDashboard.jsx` | N/A | `NOT_IMPLEMENTED` | Student UI only renders a plain `<textarea>` for subjective questions. No LaTeX input or equation preview. |
| **Handwritten Math Upload** | N/A | N/A | `NOT_IMPLEMENTED` | No image upload pipeline for student answers exists. |
| **DFA/NFA Diagram Editor** | N/A | N/A | `NOT_IMPLEMENTED` | No visual or structured automata builder exists in the student exam interface. |
| **PDF Answer Sheet Upload** | N/A | N/A | `NOT_IMPLEMENTED` | No PDF upload, page limit validation, or text extraction exists for student submissions. |
| **Answer Autosave & Drafts** | N/A | N/A | `NOT_IMPLEMENTED` | Exam answers are only submitted all-at-once on clicking "Submit Exam". If page refreshes, draft progress is lost. |
| **Answer Version History** | N/A | `Answer` table only | `NOT_IMPLEMENTED` | `Answer` table holds only the final submission. Previous revisions or drafts are not tracked. |

---

### C. Examination Monitoring & Proctoring

| Feature / Component | Source File & Function | Endpoint / Table | Status | Audit Findings & Technical Evidence |
|---|---|---|---|---|
| **Client Edge Browser Listeners** | `frontend/src/pages/StudentDashboard.jsx` | `window.onblur`, `visibilitychange` | `IMPLEMENTED_AND_VERIFIED` | Increments `tab_switches` locally and submits count with final payload. |
| **Webcam Frame Capture** | `frontend/src/pages/StudentDashboard.jsx`<br/>`backend/camera.py` | `POST /analyze_frame` | `IMPLEMENTED_AND_VERIFIED` | Periodically sends base64 frame to backend proctoring endpoint. |
| **Computer Vision Engine** | `backend/ai/proctoring/proctoring_core.py` | `ProctoringEvent` table | `IMPLEMENTED_AND_VERIFIED` | OpenCV Haar Cascade (`face_count`) and YOLOv8 (`phone`, `book`). Temporal state prevents 1-frame false alarms. |
| **Paste Activity Monitoring** | N/A | N/A | `NOT_IMPLEMENTED` | Paste events in subjective input fields are not intercepted or tracked. |
| **Answer Revision Tracking** | N/A | N/A | `NOT_IMPLEMENTED` | No character delta or typing timeline is recorded for subjective text. |
| **File Submission Integrity** | N/A | N/A | `NOT_IMPLEMENTED` | No SHA-256 file hashing or duplicate file cross-matching exists. |
| **Answer Similarity Analysis** | N/A | N/A | `NOT_IMPLEMENTED` | Cross-student answer similarity detection is not implemented. |

---

### D. Security, Authorization & Data Integrity

| Security Requirement | Implementation in Code | Verification Status | Critical Findings |
|---|---|---|---|
| **Authentication & RBAC** | `backend/auth_middleware.py`<br/>`get_current_user()`, `get_teacher_user()` | `IMPLEMENTED_AND_VERIFIED` | Validates JWT tokens, extracts user roles, and rejects expired or spoofed bearer headers. |
| **Student Answer Isolation** | `backend/routes/main_routes.py` L569 | `IMPLEMENTED_AND_VERIFIED` | Attempts are scoped to `current_user.id`. Students cannot write to another student's session. |
| **MCQ Correct Answer Exposure** | `backend/routes/main_routes.py` L773 | `IMPLEMENTED_BUT_BROKEN` | `GET /exams/{exam_id}/review` sends `correct_option` to students in review data! Must be hidden until exam is closed. |
| **Marks Tampering Prevention** | `backend/routes/main_routes.py` L1062 | `IMPLEMENTED_AND_VERIFIED` | Only users with `role == 'teacher'` can call `PUT /answers/{answer_id}/grade`. |
| **File Path Traversal** | `main_routes.py` `save_base64_image()` | `IMPLEMENTED_AND_VERIFIED` | Uses generated `uuid4().hex` filenames, preventing directory traversal via malicious filenames. |

---

## 3. Implementation Roadmap & Gap Resolution Matrix

Based on this verified audit, the following engineering tasks are required:

1. **Database Schema Expansion (Phase 3 & 6)**:
   - Extend `Answer` model with `answer_type`, `structured_answer`, `file_reference`, `file_hash`, `version_number`, `submission_status`, `updated_at`.
   - Create `AnswerVersion` model for immutable revision tracking.
   - Create `AnswerIntegrityEvent` model for paste, blur, and rapid-edit tracking.
2. **Specialized Subjective Evaluation Engine (Phase 4)**:
   - Create `backend/ai/evaluation/evaluation_dispatcher.py` to route to:
     - `text_evaluator.py`: Enhanced LLM + SentenceTransformers + Rubric.
     - `math_evaluator.py`: SymPy symbolic parser, algebraic equivalence, step checking, partial credit.
     - `automata_evaluator.py`: DFA/NFA 5-tuple verification, string simulation, Hopcroft language equivalence, subset construction.
     - `diagram_evaluator.py`: Structured graph analysis.
3. **Multi-Format Student Answer Interface & Autosave (Phase 2 & 8)**:
   - Add LaTeX equation editor with rendered preview in `StudentDashboard.jsx`.
   - Add DFA/NFA structured builder (states, alphabet, delta table, initial/accept states) generating valid JSON.
   - Add PDF and image upload with client-side validation.
   - Implement periodic autosave (`POST /exams/{exam_id}/answer_autosave`) with save status indicator.
4. **Answer Integrity Monitoring (Phase 5 & 8)**:
   - Intercept paste events (`onPaste`) and log character count and timestamp.
   - Intercept browser focus/blur and fullscreen changes.
   - Add SHA-256 file hashing and duplicate detection on uploaded answer sheets.
5. **Teacher Dashboard Multi-Format Review (Phase 8)**:
   - Update `TeacherDashboard.jsx` to render math equations, automata graphs, PDF attachments, and paste integrity flags.
6. **Security Hardening (Phase 10)**:
   - Redact `correct_option` in student review endpoints.
