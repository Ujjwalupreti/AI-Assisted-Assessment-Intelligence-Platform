# AI-Assisted Suspicious Audio Detection & Evidence System

An AI-powered audio monitoring module for online examinations that detects potentially suspicious audio events, preserves only relevant evidence, and provides teachers with an explainable review interface.

The system is designed around a **Human-in-the-Loop** principle:

> **AI detects and flags anomalies; the teacher reviews the evidence and makes the final decision.**

The system does **not** automatically declare a student guilty based solely on an AI prediction.

---

## 1. Overview

During an online examination, continuous recording of microphone audio can create unnecessary storage requirements, privacy concerns, and a large amount of irrelevant data for teachers to review.

This system solves the problem using a **rolling audio buffer**.

Instead of permanently storing the complete examination audio:

1. Audio is captured from the student's microphone.
2. Audio is continuously maintained in a short-lived rolling buffer.
3. AI analyzes small audio windows for suspicious acoustic events.
4. Normal audio is discarded after leaving the buffer.
5. When a suspicious event is detected, the system preserves:
   - Audio immediately before the event
   - The suspicious event itself
   - Audio immediately after the event
6. The resulting clip is stored as evidence.
7. The teacher reviews the evidence through the examination dashboard.
8. The teacher makes the final conclusion.

### Example

If a suspicious event occurs at:

```text
10:32:40
```

and the system is configured with:

```text
Pre-event buffer  = 15 seconds
Post-event capture = 15 seconds
```

the stored evidence becomes:

```text
10:32:25 ───────── 10:32:40 ───────── 10:32:55
     Previous             Event             After
       15s                                   15s
```

Only this approximately **30-second evidence clip** is permanently stored instead of the entire examination audio.

---

# 2. Problem Statement

Traditional online examination monitoring can generate large amounts of audio/video data.

For example:

```text
100 students
×
2 hour examination
×
continuous audio recording
=
large amount of data
```

Most of that audio is irrelevant.

A teacher may only need to investigate a few events such as:

- Multiple voices detected
- Possible conversation
- Unexpected speech
- Repeated suspicious acoustic activity
- Audio anomaly occurring simultaneously with another suspicious event

Therefore, the objective is:

> **Detect potentially relevant audio events and preserve only the minimum evidence necessary for teacher investigation.**

---

# 3. Key Features

## 3.1 Real-Time Audio Capture

The student's browser captures microphone input using browser audio APIs.

```text
Microphone
    ↓
Browser
    ↓
Audio Stream
```

---

## 3.2 Rolling Audio Buffer

The system continuously maintains a temporary buffer containing only recent audio.

Example:

```text
Rolling Buffer = 15 seconds

Current time: 10:32:40

Buffer:
10:32:25 ───────────────── 10:32:40
```

When new audio arrives:

```text
10:32:41
```

the oldest audio is removed:

```text
10:32:26 ───────────────── 10:32:41
```

Therefore, normal audio does not become permanent evidence.

---

## 3.3 AI Audio Analysis

The audio stream is divided into small processing windows.

Example:

```text
Audio Stream

| 1 sec | 1 sec | 1 sec | 1 sec | 1 sec |
    ↓
    AI
```

The AI system analyzes each window for relevant acoustic characteristics.

Possible classifications include:

- Speech detected
- Multiple speakers detected
- Possible conversation
- Unexpected speech
- Background noise
- Silence
- Other acoustic anomaly

The exact classes depend on the selected audio model.

---

# 4. Suspicious Event Detection

The system should not treat every sound as misconduct.

For example:

```text
Student coughs
       ↓
Normal event
       ↓
No evidence stored
```

Whereas:

```text
Multiple voices detected
       ↓
Potential anomaly
       ↓
Create suspicious event
       ↓
Preserve evidence
```

The AI output should therefore be interpreted as:

> **"This event requires review."**

and not:

> **"The student cheated."**

---

# 5. Evidence Capture Strategy

The core mechanism is **event-triggered evidence capture**.

Assume:

```text
PRE_EVENT_SECONDS  = 15
POST_EVENT_SECONDS = 15
```

When an event occurs:

```text
                Suspicious Event
                       ↓
                       ●
                       │
       ┌───────────────┼───────────────┐
       ↓               ↓               ↓
   Previous          Event           Following
     15 sec          event             15 sec
       │               │               │
       └───────────────┴───────────────┘
                       ↓
                Evidence Clip
```

The final clip is approximately:

```text
30 seconds
```

---

# 6. Complete Architecture

```text
                    STUDENT BROWSER
                         │
                         │ Microphone
                         ▼
                 ┌─────────────────┐
                 │ Audio Capture   │
                 │ MediaRecorder / │
                 │ Web Audio API   │
                 └────────┬────────┘
                          │
                          │ Audio chunks
                          ▼
                 ┌─────────────────┐
                 │ WebSocket /     │
                 │ WebRTC          │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ FastAPI Backend  │
                 └────────┬────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
    ┌─────────────────┐       ┌─────────────────┐
    │ Rolling Buffer  │       │ AI Audio        │
    │                 │       │ Detector        │
    │ Last 15 seconds │       │                 │
    └────────┬────────┘       └────────┬────────┘
             │                         │
             │                         │
             │                  Suspicious Event?
             │                         │
             │                    ┌────┴────┐
             │                    │         │
             │                   NO        YES
             │                    │         │
             │                 Discard      ▼
             │                         Evidence Manager
             │                               │
             │                    ┌──────────┴──────────┐
             │                    │                     │
             │              Previous 15s          Next 15s
             │                    │                     │
             └────────────────────┴─────────────────────┘
                                      │
                                      ▼
                              Evidence Clip
                                      │
                                      ▼
                              Object Storage
                              S3 / MinIO
                                      │
                                      ▼
                              PostgreSQL/MySQL
                              Event Metadata
                                      │
                                      ▼
                              Teacher Dashboard
                                      │
                                      ▼
                              Human Review
                                      │
                                      ▼
                              Final Decision
```

---

# 7. Technology Stack

## Frontend

- React.js
- JavaScript / TypeScript
- Web Audio API
- MediaRecorder API
- WebSocket client
- HTML5 Audio Player

## Backend

- Python
- FastAPI
- WebSocket
- AsyncIO

## AI / Audio Processing

Possible technologies:

- PyTorch
- Hugging Face Transformers
- librosa
- soundfile
- NumPy
- Audio classification models
- Speech-to-text model such as Whisper

The specific model can be changed depending on accuracy, latency, and hardware requirements.

## Storage

### Object Storage

Recommended:

- MinIO for local/self-hosted deployment
- Amazon S3 for cloud deployment

### Database

- PostgreSQL
- MySQL

The database stores metadata rather than unnecessarily storing large audio binaries.

---

# 8. Database Design

## `audio_events`

```sql
CREATE TABLE audio_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    exam_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    confidence FLOAT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    evidence_url TEXT,
    transcript TEXT,
    ai_summary TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Example record

```json
{
  "id": 1042,
  "exam_id": 501,
  "student_id": 1024,
  "event_type": "MULTIPLE_SPEAKERS",
  "confidence": 0.91,
  "start_time": "10:32:40",
  "end_time": "10:32:44",
  "status": "PENDING"
}
```

---

# 9. Event Types

Example event taxonomy:

```text
SPEECH_DETECTED
MULTIPLE_SPEAKERS
POSSIBLE_CONVERSATION
UNEXPECTED_AUDIO
REPEATED_AUDIO_ANOMALY
BACKGROUND_NOISE
```

Not every event should necessarily be treated as suspicious.

For example:

```text
Background Noise
       ↓
Low priority
```

while:

```text
Multiple Speakers
       +
Repeated occurrence
       +
Other suspicious exam signals
       ↓
Higher priority for teacher review
```

---

# 10. Suspicion Scoring

A simple scoring system can prioritize cases.

Example:

```text
Audio anomaly             20 points
Multiple speakers         30 points
Repeated occurrence       20 points
Possible conversation     30 points
```

Example:

```text
Total Score = 80 / 100
```

The UI can categorize:

```text
0–30      LOW
31–60     MEDIUM
61–80     HIGH
81–100    CRITICAL
```

However, the score should be treated as a **review-prioritization score**, not a probability of cheating or a final disciplinary judgment.

---

# 11. Multi-Signal Suspicion

Audio should not be analyzed independently.

The examination platform can combine multiple signals:

```text
Audio
  │
  ├── Multiple speakers
  ├── Speech
  └── Repeated audio
          │
          ▼
     AI Risk Engine
          ▲
          │
  ┌───────┼────────┐
  │       │        │
Tab     Answer   Timing
Events  Similarity Anomaly
  │       │        │
  └───────┴────────┘
          │
          ▼
   Combined Risk Score
```

Example:

```text
Audio anomaly              +25
Tab switching              +15
High answer similarity     +35
Unusual timing             +10

Risk Score = 85
```

This provides a much stronger basis for **teacher review** than relying on one signal.

---

# 12. Teacher Dashboard

The teacher sees suspicious events instead of thousands of hours of raw audio.

Example:

```text
┌──────────────────────────────────────────────────────┐
│ AUDIO MONITORING                                     │
├──────────┬────────────┬──────────────┬───────────────┤
│ Time     │ Student    │ Event        │ Priority      │
├──────────┼────────────┼──────────────┼───────────────┤
│ 10:32:40 │ Rahul      │ 2 Speakers   │ 🔴 HIGH       │
│ 10:47:12 │ Priya      │ Speech       │ 🟡 MEDIUM     │
│ 11:02:31 │ Aman       │ Noise        │ 🟢 LOW        │
└──────────┴────────────┴──────────────┴───────────────┘
```

---

# 13. Evidence Review Screen

When a teacher opens a case:

```text
┌─────────────────────────────────────────────────────┐
│ STUDENT INVESTIGATION                               │
├─────────────────────────────────────────────────────┤
│ Student: Rahul Kumar                                │
│ Exam: Data Structures                               │
│                                                     │
│ Suspicion Level: HIGH                               │
│ Review Status: PENDING                              │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │                                                 │ │
│ │             AUDIO PLAYER                       │ │
│ │                                                 │ │
│ │ ▶ ────────────────●────────────── 00:30         │ │
│ │                                                 │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ AI Detection                                        │
│                                                     │
│ Event: Multiple Speakers                            │
│ Confidence: 91%                                    │
│ Duration: 4.2 seconds                               │
│                                                     │
│ AI Explanation                                      │
│ "Multiple voice patterns were detected during the   │
│ examination. Teacher verification is required."     │
│                                                     │
│ Related Signals                                     │
│ ✓ Multiple speakers                                 │
│ ✓ Tab switch                                        │
│ ✗ Answer similarity                                 │
│                                                     │
│ [Play Evidence] [View Transcript]                  │
│                                                     │
│ Teacher Decision                                    │
│                                                     │
│ ○ No Issue                                          │
│ ○ Requires Further Investigation                    │
│ ○ Warning                                           │
│ ○ Confirm Violation                                 │
│                                                     │
│ Teacher Notes:                                      │
│ [_______________________________________________]   │
│                                                     │
│              [Submit Final Decision]                │
└─────────────────────────────────────────────────────┘
```

---

# 14. AI Explanation

The system should follow an explainable-AI approach.

Instead of:

```text
Suspicion = 91%
```

display:

```text
Why was this event flagged?

✓ Multiple voice patterns detected
✓ Event lasted approximately 4 seconds
✓ Similar event occurred twice earlier
✓ Tab switch occurred within the same period

AI Recommendation:
Review Required
```

This allows the teacher to understand why the system generated the alert.

---

# 15. Human-in-the-Loop Decision

The AI must not make the final disciplinary decision.

```text
AI
 │
 ▼
Detect anomaly
 │
 ▼
Generate explanation
 │
 ▼
Preserve evidence
 │
 ▼
Teacher review
 │
 ▼
Teacher decision
 │
 ├── No Issue
 ├── Further Investigation
 ├── Warning
 └── Confirmed Violation
```

The teacher's decision becomes the authoritative final conclusion.

---

# 16. API Design

## Start Audio Monitoring

```http
POST /api/exams/{exam_id}/audio/start
```

## Send Audio

```text
WebSocket

/ws/exams/{exam_id}/students/{student_id}/audio
```

## Get Suspicious Events

```http
GET /api/exams/{exam_id}/audio/events
```

## Get Student Events

```http
GET /api/students/{student_id}/audio/events
```

## Get Evidence

```http
GET /api/audio-events/{event_id}/evidence
```

## Submit Teacher Decision

```http
POST /api/audio-events/{event_id}/review
```

Example:

```json
{
  "decision": "NO_VIOLATION",
  "teacher_comment": "Audio appears to be background noise.",
  "reviewed_by": 17
}
```

---

# 17. WebSocket Data Flow

Example:

```text
Browser
   │
   │ Audio Chunk
   ▼
WebSocket
   │
   ▼
FastAPI
   │
   ├── Rolling Buffer
   │
   └── AI Detector
          │
          ▼
       Event?
       /    \
     NO      YES
     │        │
  discard     ▼
          Evidence
          Manager
```

---

# 18. Project Structure

```text
suspicious-audio-detection/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AudioRecorder.jsx
│   │   │   ├── AudioEventList.jsx
│   │   │   ├── EvidencePlayer.jsx
│   │   │   └── TeacherReview.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── ExamMonitoring.jsx
│   │   │   └── Investigation.jsx
│   │   │
│   │   ├── services/
│   │   │   └── websocket.js
│   │   │
│   │   └── App.jsx
│   │
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── audio.py
│   │   │   ├── exams.py
│   │   │   └── reviews.py
│   │   │
│   │   ├── audio/
│   │   │   ├── recorder.py
│   │   │   ├── buffer.py
│   │   │   ├── detector.py
│   │   │   └── evidence.py
│   │   │
│   │   ├── models/
│   │   │   ├── audio_model.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   └── models.py
│   │   │
│   │   └── storage/
│   │       └── object_storage.py
│   │
│   └── requirements.txt
│
├── models/
│   └── audio_classifier/
│
├── tests/
│   ├── test_buffer.py
│   ├── test_detector.py
│   └── test_evidence.py
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# 19. Configuration

Example `.env`:

```env
DATABASE_URL=mysql+pymysql://user:password@localhost/exam_db

OBJECT_STORAGE_ENDPOINT=http://localhost:9000
OBJECT_STORAGE_ACCESS_KEY=minioadmin
OBJECT_STORAGE_SECRET_KEY=minioadmin

PRE_EVENT_SECONDS=15
POST_EVENT_SECONDS=15

AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_SECONDS=1

AI_CONFIDENCE_THRESHOLD=0.75
```

---

# 20. Installation

## Clone Repository

```bash
git clone https://github.com/your-username/suspicious-audio-detection.git

cd suspicious-audio-detection
```

## Backend

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run FastAPI:

```bash
uvicorn backend.app.main:app --reload
```

API documentation:

```text
http://localhost:8000/docs
```

---

# 21. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

---

# 22. Docker

The complete system can be deployed using:

```bash
docker compose up --build
```

Possible services:

```text
┌─────────────────────┐
│ React Frontend      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ FastAPI Backend     │
└──────┬───────┬──────┘
       │       │
       ▼       ▼
   Database   MinIO
       │
       ▼
    Metadata
```

---

# 23. Security

The system should implement:

- HTTPS/TLS
- JWT/OAuth authentication
- Role-based access control
- Encrypted evidence storage
- Signed/private evidence URLs
- Access logging
- Audit logs
- Secure WebSocket connections
- Input validation
- Rate limiting
- Database access controls

### Roles

```text
Student
   │
   └── Submit exam / provide microphone permission

Teacher
   │
   ├── View suspicious events
   ├── Play evidence
   ├── Add notes
   └── Submit final decision

Administrator
   │
   ├── Manage exams
   ├── Manage users
   ├── Configure retention
   └── View audit logs
```

---

# 24. Privacy & Data Retention

Privacy is a core design consideration.

The system follows a **data minimization** approach.

### Normal audio

```text
Captured
   ↓
Temporary rolling buffer
   ↓
No suspicious event
   ↓
Discard
```

### Suspicious audio

```text
Captured
   ↓
Suspicious event
   ↓
Relevant clip extracted
   ↓
Encrypted storage
   ↓
Teacher review
   ↓
Retention policy
   ↓
Automatic deletion
```

The system should clearly communicate:

- Why microphone access is required
- What is analyzed
- What is permanently stored
- How long evidence is retained
- Who can access evidence
- How evidence is deleted

Retention periods should be configurable according to the institution's policies and applicable privacy requirements.

---

# 25. Limitations

AI audio detection is not perfect.

Possible false positives include:

- Nearby conversations
- Teacher instructions
- Environmental noise
- TV/radio sounds
- Family members speaking
- Pets
- Keyboard or mechanical noise
- Poor microphone quality
- Network/audio compression artifacts

Therefore:

> **AI-generated alerts should be treated as evidence requiring review, not automatic proof of misconduct.**

---

# 26. Future Improvements

Potential improvements include:

### Multimodal Proctoring

Combine:

```text
Audio
+
Camera
+
Screen Activity
+
Tab Switching
+
Answer Similarity
+
Timing Patterns
```

to create a unified examination-risk engine.

### Advanced Audio Analysis

Future versions can include:

- Speaker diarization
- Noise classification
- Speech-to-text
- Acoustic event detection
- Voice activity detection
- Temporal anomaly detection

### Evidence Correlation

Example:

```text
10:32:40  Multiple speakers
10:32:42  Tab switched
10:32:44  Student submitted answer
10:32:46  Another voice detected
```

The system can group these into one **investigation case** rather than creating four unrelated alerts.

---

# 27. Example Investigation Case

```text
CASE #EXAM-2026-1042

Student:
Rahul Kumar

Exam:
Data Structures

Risk Level:
HIGH

Events:
────────────────────────────────────────

10:32:40
Multiple speakers detected

10:32:42
Browser tab switch detected

10:32:44
Answer submitted

10:32:46
Second audio event detected

────────────────────────────────────────

AI Summary:

"Multiple audio events were detected during
the examination. A browser tab switch occurred
during the same period. The events have been
grouped for teacher review."

────────────────────────────────────────

Teacher Decision:

[ ] No Violation
[ ] Further Investigation
[ ] Warning
[ ] Confirmed Violation
```

---

# 28. Design Principle

The most important design principle of this project is:

```text
                AI
                 │
        Detect + Explain
                 │
                 ▼
              Evidence
                 │
                 ▼
             Teacher
                 │
         Review + Context
                 │
                 ▼
        Final Conclusion
```

### AI is an assistant, not the judge.

This makes the system more explainable, reduces unnecessary data storage, reduces teacher workload, and allows suspicious examination events to be investigated using concrete evidence.

---

# 29. Project Goals

The system aims to:

- Reduce unnecessary continuous audio storage
- Detect potentially suspicious audio events
- Preserve contextual evidence around detected events
- Reduce the teacher's review workload
- Provide explainable AI-generated alerts
- Correlate audio with other examination signals
- Maintain an auditable teacher decision process
- Follow data minimization and privacy-aware principles

---

# 30. License

This project is intended for educational and research purposes.

Add an appropriate open-source license before public distribution, such as MIT, Apache-2.0, or another license selected by the project owners.
