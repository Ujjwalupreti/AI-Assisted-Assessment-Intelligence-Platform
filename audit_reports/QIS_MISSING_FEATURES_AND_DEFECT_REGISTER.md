# QIS — Missing Features and Defect Register

**Document Reference**: `audit_reports/QIS_MISSING_FEATURES_AND_DEFECT_REGISTER.md`  
**Project**: Question Intelligence System (QIS)  
**Team Leader**: Ujjwal Upreti | **Members**: Vishal Singh, Ujjwal Upreti, Vaibhav Joshi  
**Date**: 12 November 2026  
**Audit Standard**: Master Verification Specification — Part II Section 20, 21 & 22

---

## 1. Prioritization Framework

Defects and missing features are classified into four severity tiers:

- **P0 — Critical**: Security breach, data loss, database corruption, or complete application crash.
- **P1 — High**: Core user workflow failure, broken primary integration, or materially incorrect grading output.
- **P2 — Medium**: Significant feature limitation, missing sub-workflow, or unstable model loading.
- **P3 — Low**: Usability inconsistency, non-critical code duplication, or cosmetic UI defect.

---

## 2. Category A — Completely Missing Features

| Item ID | Feature Name | Priority | Evidence | Current Behavior | Expected Behavior | User Impact | Recommended Remediation | Complexity |
|---|---|---|---|---|---|---|---|---|
| `GAP-01` | True Eye-Gaze & 3D Head Pose | **P2** | [`main_routes.py#L888`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/routes/main_routes.py#L888) | Bounding box center check ($w/4$ to $3w/4$). | Genuine 3D head-pose estimation (yaw, pitch, roll) or iris gaze tracking. | Overstated in documentation; cannot detect peripheral looking away. | Clarify documentation as "Face Position Heuristic" or integrate MediaPipe FaceMesh. | Medium |
| `GAP-02` | Active Audio DSP Monitoring | **P2** | [`models.py#L125`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/models.py#L125) | `audio_warnings` column exists in DB, but no audio streaming or DSP model in code. | Real-time audio stream analysis detecting background speech or whispering. | Candidates cannot be monitored for verbal collusion. | Integrate Web Audio API streaming with WebRTC or Silero VAD. | High |
| `GAP-03` | OS-Level Secure Browser Lock | **P2** | [`StudentDashboard.jsx#L390`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/src/pages/StudentDashboard.jsx#L390) | JavaScript window `blur` listener counts tab switches. | OS-level application lockdown (blocking secondary monitors, alt-tab, screenshots). | Tech-savvy candidates can bypass browser-only focus checks. | Support Safe Exam Browser (SEB) configuration headers. | High |
| `GAP-04` | ChromaDB Vector Database | **P3** | 0 occurrences in repository. | SQLite table `document_chunk` stores vector JSON arrays. | Standalone ChromaDB vector database service. | Discrepancy with original design specifications. | Update architectural documentation to endorse SQLite + NumPy vector search. | Low |

---

## 3. Category B — Partially Implemented Features

| Item ID | Feature Name | Priority | Evidence | Current Behavior | Expected Behavior | User Impact | Recommended Remediation | Complexity |
|---|---|---|---|---|---|---|---|---|
| `GAP-05` | Generative Question Creation | **P1** | [`question_generator.py#L3`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/ai/question_generator.py#L3) | Calls Gemini via deprecated SDK; returns HTTP 404 on `v1beta`. | Generates novel MCQs grounded in uploaded RAG syllabus chunks. | Teachers cannot generate new candidate questions automatically. | Migrate `llm_client.py` to `google-genai` SDK and `gemini-2.0-flash`. | Medium |
| `GAP-06` | Question Versioning History | **P3** | [`models.py#L75`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/models.py#L75) | Question model tracks `status` and `source`, but overwrites text on update. | Granular revision history (`QuestionRevision` table) tracking edits over time. | Inability to audit prior question variations after modification. | Implement `QuestionRevision` audit table capturing diffs and author ID. | Medium |
| `GAP-07` | Empirical Item Difficulty | **P2** | [`difficulty_estimator.py#L65`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/ai/difficulty_estimator.py#L65) | Difficulty is calculated statically using the 5-signal NLP heuristic. | Difficulty dynamically recalibrates using correct-response proportions ($p$-value). | Item difficulty does not adapt as cohorts take exams. | Add post-exam analytics hook updating difficulty based on pass rates. | Medium |

---

## 4. Category C — Implemented but Defective Features (Defect Register)

### Defect `DEF-01` (Priority: P1 — High)
- **Feature**: Real-Time Question Intelligence Analysis in Question Bank UI
- **File Reference**: [`frontend/src/components/AddQuestionForm.jsx#L57`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/src/components/AddQuestionForm.jsx#L57) & [`frontend/src/services/questionService.js#L21`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/src/services/questionService.js#L21)
- **Evidence**:
  ```javascript
  const res = await fetch(`${API_BASE_URL}/exams/${examId}/questions/analyze`, { ... });
  ```
- **Current Behavior**: Request returns HTTP 404 Not Found.
- **Expected Behavior**: Calls the registered backend route `POST /api/ai/questions/analyze` and returns Bloom, difficulty, and quality scores.
- **User Impact**: Teachers authoring questions in the UI cannot use the "✨ AI Analyze" button.
- **Recommended Fix**: Update frontend URL to `${API_BASE_URL}/ai/questions/analyze` and add compatibility proxy route in `question_routes.py`.
- **Complexity**: Low.

---

### Defect `DEF-02` (Priority: P1 — High)
- **Feature**: Cloud AI Generative LLM Wrapper
- **File Reference**: [`backend/ai/llm_client.py#L22`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/ai/llm_client.py#L22)
- **Evidence**:
  ```text
  LLM Generation Error: 404 models/gemini-1.5-flash is not found for API version v1beta
  ```
- **Current Behavior**: Gemini calls fail with HTTP 404.
- **Expected Behavior**: Initializes official Google GenAI client and completes structured JSON generation.
- **User Impact**: Question generation from syllabus is blocked; subjective grading must rely on local fallback.
- **Recommended Fix**: Update requirements to `google-genai` and switch to `gemini-2.0-flash`.
- **Complexity**: Medium.

---

### Defect `DEF-03` (Priority: P2 — Medium)
- **Feature**: Proctoring Log API Service
- **File Reference**: [`frontend/src/services/proctoringService.js#L7`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/src/services/proctoringService.js#L7)
- **Evidence**:
  ```javascript
  getProctorLogs: (examId, studentId) => apiFetch(`/proctoring/exam/${examId}/student/${studentId}`);
  ```
- **Current Behavior**: Request returns HTTP 404 because no `/api/proctoring` router exists in `app.py`.
- **Expected Behavior**: Points to the working backend route `/api/exams/{exam_id}/review/{student_id}`.
- **User Impact**: Standalone proctoring incident log calls fail if invoked outside the main teacher dashboard.
- **Recommended Fix**: Remap URL to `/exams/${examId}/review/${studentId}`.
- **Complexity**: Low.

---

### Defect `DEF-04` (Priority: P2 — Medium)
- **Feature**: YOLOv8 Model Weights Relative Pathing
- **File Reference**: [`backend/routes/main_routes.py#L27`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/backend/routes/main_routes.py#L27)
- **Evidence**:
  ```python
  model = YOLO('yolov8n.pt')
  ```
- **Current Behavior**: Looks for `yolov8n.pt` in current working directory. If launched from root `ai_project_copy/`, it downloads a duplicate 6.55 MB weight file.
- **Expected Behavior**: Resolves path relative to backend directory (`backend/yolov8n.pt`).
- **User Impact**: Unnecessary network download and disk clutter during startup.
- **Recommended Fix**: `YOLO(os.path.join(os.path.dirname(__file__), '..', 'yolov8n.pt'))`.
- **Complexity**: Low.

---

### Defect `DEF-05` (Priority: P3 — Low)
- **Feature**: Frontend Bundle Size & Code-Splitting
- **File Reference**: [`frontend/package.json`](file:///c:/Users/Hp/Downloads/PRoject/ai_project_copy/frontend/package.json)
- **Evidence**: Vite production build took 24.88 seconds; outputs large single chunk for Lucide icons and Recharts.
- **Current Behavior**: Monolithic bundle loaded on initial page visit.
- **Expected Behavior**: Route-level dynamic chunking via `React.lazy()`.
- **User Impact**: Initial load time on mobile or throttled connections is slightly higher than optimal.
- **Recommended Fix**: Implement `React.lazy()` for Analytics and Proctoring review routes.
- **Complexity**: Low.

