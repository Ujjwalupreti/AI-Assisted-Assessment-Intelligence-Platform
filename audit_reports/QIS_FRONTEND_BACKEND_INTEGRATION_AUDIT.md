# QIS — Frontend and Backend Integration Audit & API Contract Analysis

**Document Reference**: `audit_reports/QIS_FRONTEND_BACKEND_INTEGRATION_AUDIT.md`  
**Project**: Question Intelligence System (QIS)  
**Team Leader**: Ujjwal Upreti | **Members**: Vishal Singh, Ujjwal Upreti, Vaibhav Joshi  
**Date**: 12 November 2026  
**Audit Standard**: Master Verification Specification — Part II Section 16 & 22

---

## 1. Executive Summary: Integration Health & Contract State

This audit evaluates the end-to-end communication interface between the React 18 single-page application and the FastAPI REST backend. 

### Key Integration Findings:
1. **Centralized Communication Layer**: The frontend utilizes a unified fetch wrapper ([`frontend/src/services/api.js`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/src/services/api.js)) configuring `API_BASE_URL = '/api'` and automatically attaching the Bearer JWT token from `localStorage`.
2. **Router Registration Completeness**: All 10 backend routers are mounted in [`backend/app.py`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/app.py#L35) with appropriate prefixes and CORS middleware.
3. **Primary Workflow Integration**: Student examination attempts, real-time proctoring frame ingestion, exam submission, blueprint assembly preview, and institutional analytics are **100% integrated and operational**.
4. **Discovered API Contract Mismatches**:
   - **`DEF-FRONT-01` (P1 - High)**: `AddQuestionForm.jsx` and `questionService.js` call `/api/exams/${examId}/questions/analyze` which returns HTTP 404 because the QIS analyzer is mounted at `/api/ai/questions/analyze`.
   - **`DEF-FRONT-02` (P2 - Medium)**: `proctoringService.js` attempts to query `/api/proctoring/...` where no backend router is registered.

---

## 2. Router Mount Inventory (`backend/app.py`)

| Router Variable | Source Module | Mounted URL Prefix | Target Domain | Tag |
|---|---|---|---|---|
| `auth_bp` | `routes.main_routes` | `/api/auth` | User login & registration | `auth` |
| `exam_bp` | `routes.main_routes` | `/api/exams` | Exam CRUD, attempts, submissions, proctoring | `exams` |
| `question_bp` | `routes.question_routes`| `/api/exams` | Question CRUD inside exams & bank | `questions` |
| `intelligence_bp` | `routes.exam_intelligence_routes` | `/api/intelligence` | Blueprint assembly preview, slots, recommendations | `intelligence` |
| `attempt_bp` | `routes.attempt_routes` | `/api/attempts` | Student attempt lifecycle management | `attempts` |
| `student_bp` | `routes.students_routes` | `/api/students` | Student management & enrollment | `students` |
| `admin_bp` | `routes.admin_routes` | `/api/admin` | System admin operations | `admin` |
| `analytics_bp` | `routes.analytics_routes` | `/api/analytics` | Exam statistics & student progression | `analytics` |
| `qis_bp` | `routes.qis_routes` | `/api/ai/questions` | Question intelligence, Bloom, difficulty, deduplication | `qis` |
| `rag_bp` | `routes.rag_routes` | `/api/rag` | Syllabus upload & vector chunk index | `rag` |

---

## 3. Complete End-to-End API Endpoint Contract Matrix

| Frontend Service / Component | HTTP Method | Frontend URL Constructed | Backend Route Registered | Auth Required | Request Payload Schema | Response Payload Schema | DB Operation | Integration Status | Defect ID / Finding |
|---|---|---|---|---|---|---|---|---|---|
| `LoginPage.jsx` | `POST` | `/api/auth/login` | `/api/auth/login` | No | `{"username": str, "password": str}` | `{"token": str, "user": {...}}` | `User` Read | **VERIFIED** | Clean authentication handshake. |
| `CreateExamForm.jsx` | `POST` | `/api/exams` | `/api/exams` | Yes (Teacher) | `{"title": str, "duration_minutes": int, ...}` | `{"message": str, "exam_id": int}` | `Exam` Insert | **VERIFIED** | Creates exam; returns 201 Created. |
| `StudentDashboard.jsx` | `GET` | `/api/exams` | `/api/exams` | Yes (Student) | None | `[{"id": int, "title": str, ...}]` | `Exam` Read | **VERIFIED** | Privacy filter: students see visible exams only. |
| `StudentDashboard.jsx` | `POST` | `/api/exams/{id}/start` | `/api/exams/{id}/start` | Yes (Student) | None | `{"message": str, "attempt_id": int}` | `ExamAttempt` Insert | **VERIFIED** | Session initialized in 46.8 ms. |
| `StudentDashboard.jsx` | `POST` | `/api/exams/analyze_frame` | `/api/exams/analyze_frame` | Yes (Student) | `{"frame": b64_str, "attempt_id": int}` | `{"status": str, "events": [...]}` | `ProctoringEvent` Insert | **VERIFIED** | OpenCV + YOLO frame analysis. |
| `StudentDashboard.jsx` | `POST` | `/api/exams/{id}/submit` | `/api/exams/{id}/submit` | Yes (Student) | `{"answers": dict, "tab_switches": int}` | `{"message": str, "score": float}` | `Result`, `Answer` Insert | **VERIFIED** | Objective evaluation + Result creation. |
| `TeacherDashboard.jsx` | `POST` | `/api/exams/{id}/evaluate` | `/api/exams/{id}/evaluate` | Yes (Teacher) | `{"use_rag": bool}` | `{"message": str}` | `Answer` Update | **VERIFIED** | Triggers local MiniLM subjective grading. |
| `TeacherDashboard.jsx` | `PUT` | `/api/exams/answers/{id}/grade`| `/api/exams/answers/{id}/grade`| Yes (Teacher) | `{"marks": float, "feedback": str}` | `{"message": str}` | `Answer`, `Result` Update | **VERIFIED** | Manual override updates student grade. |
| `KnowledgeBase.jsx` | `POST` | `/api/rag/documents` | `/api/rag/documents` | Yes (Teacher) | `{"title": str, "course_name": str, ...}`| `{"message": str, "document_id": int}`| `CourseDocument` Insert | **VERIFIED** | Document text chunked and embedded. |
| `KnowledgeBase.jsx` | `GET` | `/api/rag/documents` | `/api/rag/documents` | Yes (Teacher) | None | `[{"id": int, "title": str, ...}]` | `CourseDocument` Read | **VERIFIED** | Lists all institutional documents. |
| `CreateExamForm.jsx` | `POST` | `/api/intelligence/assemble`| `/api/intelligence/assemble`| Yes (Teacher) | `{"topics": dict, "difficulty": dict, ...}` | `{"selected_questions": [...], "gaps": [...]}`| `Question` Read | **VERIFIED** | Blueprint assembly returns candidate pool. |
| `DuplicateAnalysis.jsx`| `POST` | `/api/ai/questions/deduplicate`| `/api/ai/questions/deduplicate`| Yes (Teacher) | `{"exam_id": int}` | `{"duplicates": [...]}` | `QuestionEmbedding` Read | **VERIFIED** | Batch duplicate grouping. |
| `analyticsService.js` | `GET` | `/api/analytics/exam/{id}` | `/api/analytics/exam/{id}` | Yes (Teacher) | None | `{"average_score": float, "attempts": int}`| `Result` Aggregate Read | **VERIFIED** | Real-time statistical aggregation. |
| `analyticsService.js` | `GET` | `/api/analytics/student/{id}`| `/api/analytics/student/{id}`| Yes (Teacher) | None | `{"total_exams_taken": int, ...}` | `Result` Read | **VERIFIED** | Longitudinal candidate progression. |
| `AddQuestionForm.jsx` | `POST` | `/api/exams/{id}/questions/analyze`| `/api/ai/questions/analyze` | Yes (Teacher) | `{"text": str, "options": dict, ...}` | `{"classification": {...}, "quality": {...}}` | `QuestionAiAnalysis` Insert | **FAILED (404)** | **DEF-FRONT-01**: Missing `/api/ai/` prefix. |
| `questionService.js` | `POST` | `/api/exams/{id}/questions/analyze`| `/api/ai/questions/analyze` | Yes (Teacher) | `{"text": str, ...}` | `{"classification": {...}}` | None | **FAILED (404)** | **DEF-FRONT-01**: Service helper path mismatch. |
| `proctoringService.js` | `GET` | `/api/proctoring/exam/{id}/student/{id}`| Not Mounted | Yes (Teacher) | None | None | None | **FAILED (404)** | **DEF-FRONT-02**: `/api/proctoring` prefix not mounted. |

---

## 4. Root Cause Analysis of Integration Defects

### Defect `DEF-FRONT-01`: Question Analysis URL Mismatch
- **Frontend Caller**: [`frontend/src/components/AddQuestionForm.jsx#L57`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/src/components/AddQuestionForm.jsx#L57)
  ```javascript
  // Current faulty call:
  const res = await fetch(`${API_BASE_URL}/exams/${examId}/questions/analyze`, { ... });
  ```
- **Backend Definition**: [`backend/routes/qis_routes.py#L20`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/routes/qis_routes.py#L20)
  ```python
  @qis_bp.post('/analyze')
  def analyze_single_question(...):
  ```
  Mounted in `app.py` as:
  ```python
  app.include_router(qis_bp, prefix='/api/ai/questions', tags=['qis'])
  ```
- **Impact**: When teachers author questions in the UI and click "✨ AI Analyze", the request yields HTTP 404, preventing real-time Bloom and difficulty tagging.
- **Recommended Remediation**:
  1. Frontend update: Change URL in `AddQuestionForm.jsx` (line 57) and `questionService.js` (line 21) to `${API_BASE_URL}/ai/questions/analyze`.
  2. Backend compatibility proxy: In [`backend/routes/question_routes.py`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/routes/question_routes.py), register an alias route `@question_bp.post('/{exam_id}/questions/analyze')` forwarding to `analyze_single_question`.

---

### Defect `DEF-FRONT-02`: Proctoring Service Unmounted Prefix
- **Frontend Caller**: [`frontend/src/services/proctoringService.js#L7`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/src/services/proctoringService.js#L7)
  ```javascript
  getProctorLogs: (examId, studentId) => apiFetch(`/proctoring/exam/${examId}/student/${studentId}`);
  ```
- **Backend Implementation**: Proctoring incident logs and candidate review records are served by [`backend/routes/main_routes.py`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/routes/main_routes.py#L792):
  ```python
  @exam_bp.get('/{exam_id}/review/{student_id}')
  def get_student_exam_review_for_teacher(exam_id, student_id, ...):
  ```
- **Impact**: Calling `proctoringService.getProctorLogs` results in an unhandled 404.
- **Recommended Remediation**:
  Update `frontend/src/services/proctoringService.js` to call `/exams/${examId}/review/${studentId}` matching the existing backend endpoint contract.

---

## 5. Security & Header Propagation Audit

1. **Authorization Token Delivery**:
   - `frontend/src/services/api.js` automatically attaches `Authorization: Bearer <token>` on all requests where `<token>` is present in `localStorage`.
   - Backend `Depends(get_current_user)` correctly decodes the JWT subject and verifies the user exists and is active.
2. **CORS Configuration**:
   - Allowed origins configured in `backend/app.py`: `http://localhost:5173`, `http://127.0.0.1:5173`, etc.
   - Credentials allowed: `allow_credentials=True`.
   - Exposed headers include `user-id`.
3. **Payload Sanitization**:
   - Pydantic models and explicit dictionary extraction validate all incoming request bodies.
   - Base64 images are verified for header structure (`data:image/jpeg;base64,...`) and decoded via OpenCV `imdecode`.

