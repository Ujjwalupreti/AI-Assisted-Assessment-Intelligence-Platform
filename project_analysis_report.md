# AI Proctoring System: Complete Project Analysis Report

This document provides a deep dive into the architecture, workflows, data flows, and features of the AI Proctoring System. It is designed to serve as a comprehensive guide for future analysis, scaling, and architectural refactoring.

---

## 1. High-Level Architecture
- **Frontend**: React (Vite) utilizing Bootstrap for responsive UI.
- **Backend**: Flask (Python) with SQLAlchemy ORM.
- **Database**: SQLite (local file-based storage).
- **AI/ML Layer**:
  - **Vision**: `ultralytics` YOLOv8 Object Detection (running synchronously on the Flask backend).
  - **Text/Evaluation**: Google Gemini API integration (with `difflib` semantic similarity fallback) via `google.generativeai`.

---

## 2. Core Features & Services

### A. Authentication & Role Management
The system supports three primary roles: `admin`, `teacher`, and `student`.
- **Service**: `auth_routes.py`
- **Data Flow**:
  1. Frontend sends credentials to `POST /api/auth/login`.
  2. Backend hashes the password using `scrypt` and compares it against the DB.
  3. On success, the backend returns the user object. The frontend stores this locally (`localStorage`) and attaches the `user-id` header to all subsequent API calls.
  4. **Constraint**: The system uses a raw HTTP header (`user-id`) instead of cryptographic JWTs. A custom `@auth_required` decorator validates this header against the database.

### B. Exam & Question Management (Teacher Services)
Teachers can create, publish, and manage exams.
- **Service**: `exam_routes.py`, `question_routes.py`
- **Features**: Time-limited exams, Subjective & MCQ support, E2E Encryption, CSV Bulk Upload.
- **Data Flow (E2E Encryption)**:
  1. If an exam requires a password, the frontend uses AES (`CryptoJS`) to encrypt question text and options *in the browser*.
  2. The frontend hashes the correct option using `SHA-256(Option + ExamID)`.
  3. The backend receives and stores *only* the ciphertext and hashes. The database never contains plaintext questions.
  4. During the exam, students input the password to decrypt questions locally in their browser.

### C. Student Exam Engine
A secure, lockdown environment for test-taking.
- **Service**: `StudentDashboard.jsx`
- **Features**: Full-screen enforcement, anti-copy/paste, timer synchronization, session persistence (via `sessionStorage` in case of accidental refresh).
- **Data Flow**:
  1. The student verifies identity by capturing an ID card photo and a Face photo.
  2. The exam is fetched and decrypted locally.
  3. **Auto-Save**: The frontend silently syncs the current state (selected options, text answers) to `sessionStorage`.
  4. On completion, the frontend calculates hashes for MCQ answers, gathers subjective text answers, aggregates all violation metrics (tab switches, audio alerts), and sends a single payload to `POST /api/exams/<exam_id>/submit`.

### D. Multi-Modal AI Proctoring
The system continuously monitors the student via visual and audio channels.
- **Service**: `ai_services.py`, `/api/exams/analyze_frame`
- **Visual Proctoring Flow**:
  1. The React frontend captures a webcam frame via `react-webcam` every 2 seconds.
  2. The frame is converted to Base64 and sent to the backend.
  3. The backend decodes the image and runs YOLOv8. It specifically targets Class 0 (Person), Class 67 (Cell Phone), and Class 73 (Book).
  4. **Logic**:
      - `len(persons) == 0` -> **Missing**
      - `len(persons) > 1` -> **Multiple People**
      - `phone or book detected` -> **Contraband**
      - *Face Orientation*: If the bounding box of the person is significantly off-center, it flags as **Looking Away**.
  5. **Secret Capture**: If a severe violation is detected, the frontend silently captures a high-res "Mid-Exam Photo" and caches it for submission.
- **Audio Proctoring Flow**:
  1. The frontend utilizes the browser's `AudioContext` and `AnalyserNode`.
  2. It constantly calculates the Root Mean Square (RMS) volume of the microphone stream.
  3. Volume spikes above a configured threshold trigger a local warning counter (which is eventually sent to the backend upon submission).

### E. AI-Assisted Subjective Evaluation
Automates the grading of long-form text answers.
- **Service**: `ai_services.py` (`evaluate_subjective_answer`)
- **Data Flow**:
  1. Teacher triggers `POST /api/exams/<exam_id>/evaluate`.
  2. Backend iterates over all un-graded subjective answers for the exam.
  3. The payload (Student Answer + Reference Answer) is sent to Google Gemini with a prompt instructing it to return JSON containing `score` (0.0 to 1.0) and `explanation`.
  4. **Fallback**: If Gemini fails (or no API key is present), the system uses `difflib.SequenceMatcher` to calculate a semantic similarity ratio.
  5. The backend updates the `Answer` records with `ai_suggested_marks` and `ai_explanation`.

### F. Result Analysis & Manual Override (Teacher Dashboard)
- **Service**: `routes.py`, `TeacherDashboard.jsx`
- **Data Flow**:
  1. Teachers fetch results via `GET /api/exams/<exam_id>/results`.
  2. Teachers can view identity verification images (ID, Face, Secret Capture) stored dynamically in the local filesystem (`static/uploads/`).
  3. Teachers can drill down into a student's specific review via `GET /api/exams/<exam_id>/review/<student_id>`.
  4. The teacher can override AI grading by submitting a score and feedback to `PUT /api/exams/answers/<answer_id>/grade`. The backend recalculates the total `Result` score instantly.

---

## 3. Structural Vulnerabilities & Constraints (For Next Analysis)

If this system is moving toward a production environment, several critical architectural flaws must be addressed:

### Security Risks
1. **Header-Based Authentication**: Using `user-id: 1` as an auth mechanism is highly insecure. 
   - **Recommendation**: Implement JWTs (JSON Web Tokens) with short expiration times and HttpOnly cookies.
2. **Client-Side Source of Truth**: The frontend is responsible for counting tab switches and audio warnings, and for calculating the final timestamp. A technical student could use a local proxy (like Burp Suite) to intercept the `POST /submit` payload and modify their warning count to `0`.
   - **Recommendation**: The backend should actively manage state via WebSockets. The server should track the exam timer natively.

### Scalability Bottlenecks
3. **Synchronous Image Processing (YOLOv8)**: Sending Base64 images every 2 seconds from hundreds of concurrent students to a synchronous Flask thread running a heavy YOLO model will cause immediate server exhaustion (Thread Starvation).
   - **Recommendation**: Move object detection to the client browser using `tensorflow.js` (e.g., COCO-SSD) to save massive bandwidth and compute costs. Only send violation metadata to the server.
4. **SQLite Database Locking**: SQLite is a local file database that locks the entire file during a write operation. Concurrent exam submissions will result in `database is locked` errors.
   - **Recommendation**: Migrate to PostgreSQL.
5. **Local Image Storage**: Base64 images are decoded and saved directly to the host server's file system (`static/uploads`). This will quickly consume all disk space and does not scale horizontally.
   - **Recommendation**: Stream uploads directly to an S3-compatible object storage bucket and store only the URL reference in the database.

---
## Summary
The system currently provides an incredibly rich, feature-complete prototype demonstrating advanced E2E encryption, AI-driven visual/audio proctoring, and LLM-assisted subjective grading. It successfully fulfills all logic requirements but requires significant architectural refactoring (JWTs, PostgreSQL, Client-side AI) before being exposed to a live, uncontrolled network.
