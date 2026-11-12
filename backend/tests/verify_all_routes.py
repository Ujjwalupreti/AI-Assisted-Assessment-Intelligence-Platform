import os
import sys

# Force offline mode for cached HuggingFace models
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import time
import json
import asyncio
from datetime import datetime, timezone, timedelta

# Set working directory to backend
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

TEST_DB_PATH = os.path.join(BACKEND_DIR, "instance", "test_routes_verification.db")
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "audit-route-verification-key-32chars"

from httpx import ASGITransport, AsyncClient
from database import engine, SessionLocal, Base
from models import User, Exam, Question, QuestionAiAnalysis, ExamAttempt, Answer, ProctoringEvent, Result
from app import create_app

results = []

def record(route_name, method, path, status_code, expected_status, passed, detail=""):
    results.append({
        "route": route_name,
        "method": method,
        "path": path,
        "status_code": status_code,
        "expected": expected_status,
        "passed": passed,
        "detail": detail
    })
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {method:6} {path:45} -> {status_code} ({detail})")

async def run_route_audit():
    print("=" * 80)
    print("STARTING COMPLETE APPLICATION & API ROUTE VERIFICATION AUDIT")
    print("Database:", TEST_DB_PATH)
    print("=" * 80)

    # 0. Setup Clean Schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app = create_app()

    # 1. Seed Initial Users
    db = SessionLocal()
    teacher = User(username="prof_sharma", email="sharma@college.edu", role="teacher", is_active=True)
    teacher.set_password("Teacher123!")
    student = User(username="ujjwal_student", email="student@college.edu", role="student", enrollment_id="STU101", is_active=True)
    student.set_password("Student123!")
    admin = User(username="admin_user", email="admin@college.edu", role="admin", is_active=True)
    admin.set_password("Admin123!")
    db.add_all([teacher, student, admin])
    db.commit()
    teacher_id = teacher.id
    student_id = student.id
    admin_id = admin.id
    db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # -------------------------------------------------------------------------
        # ROUTE GROUP 1: Health & Public Documentation Endpoints
        # -------------------------------------------------------------------------
        print("\n--- 1. Health & Documentation Endpoints ---")
        r = await client.get("/api/ping")
        record("Ping Health Check", "GET", "/api/ping", r.status_code, 200, r.status_code == 200 and r.json().get("status") == "ok", "Server online")

        r = await client.get("/openapi.json")
        record("OpenAPI Specification", "GET", "/openapi.json", r.status_code, 200, r.status_code == 200 and "paths" in r.json(), "OpenAPI schema valid")

        r = await client.get("/docs")
        record("Swagger UI", "GET", "/docs", r.status_code, 200, r.status_code == 200, "HTML docs rendered")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 2: Authentication & RBAC Security
        # -------------------------------------------------------------------------
        print("\n--- 2. Authentication & Authorization Security ---")
        r = await client.post("/api/auth/login", json={"username": "prof_sharma", "password": "Teacher123!"})
        teacher_token = r.json().get("token")
        record("Teacher Login", "POST", "/api/auth/login", r.status_code, 200, r.status_code == 200 and teacher_token is not None, "JWT issued")
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

        r = await client.post("/api/auth/login", json={"username": "ujjwal_student", "password": "Student123!"})
        student_token = r.json().get("token")
        record("Student Login", "POST", "/api/auth/login", r.status_code, 200, r.status_code == 200 and student_token is not None, "JWT issued")
        student_headers = {"Authorization": f"Bearer {student_token}"}

        r = await client.post("/api/auth/login", json={"username": "admin_user", "password": "Admin123!"})
        admin_token = r.json().get("token")
        record("Admin Login", "POST", "/api/auth/login", r.status_code, 200, r.status_code == 200 and admin_token is not None, "JWT issued")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        r = await client.post("/api/auth/login", json={"username": "prof_sharma", "password": "WrongPassword"})
        record("Invalid Credential Rejection", "POST", "/api/auth/login", r.status_code, 401, r.status_code == 401, "Rejected correctly")

        r = await client.get("/api/exams")
        record("Unauthenticated Protection", "GET", "/api/exams", r.status_code, 401, r.status_code == 401, "Bearer challenge")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 3: Exam Management
        # -------------------------------------------------------------------------
        print("\n--- 3. Exam Management Routes ---")
        now_iso = datetime.now(timezone.utc).isoformat()
        end_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        exam_payload = {
            "title": "Data Structures & Algorithms Midterm",
            "duration_minutes": 60,
            "start_date": now_iso,
            "end_date": end_iso,
            "is_visible": True,
            "description": "Comprehensive evaluation of stacks, queues, trees, and graphs."
        }
        r = await client.post("/api/exams", headers=teacher_headers, json=exam_payload)
        exam_data = r.json()
        exam_id = exam_data.get("exam_id") or exam_data.get("id", 1)
        record("Create Exam", "POST", "/api/exams", r.status_code, [200, 201], r.status_code in (200, 201), f"Exam ID={exam_id}")

        r = await client.get("/api/exams", headers=teacher_headers)
        record("List Exams (Teacher)", "GET", "/api/exams", r.status_code, 200, r.status_code == 200 and len(r.json()) >= 1, "Exams returned")

        r = await client.get(f"/api/exams/{exam_id}/details", headers=teacher_headers)
        record("Get Exam Details", "GET", f"/api/exams/{exam_id}/details", r.status_code, 200, r.status_code == 200, "Details fetched")

        r = await client.put(f"/api/exams/{exam_id}/settings", headers=teacher_headers, json={"duration_minutes": 75, "description": "Updated duration"})
        record("Update Exam Settings", "PUT", f"/api/exams/{exam_id}/settings", r.status_code, 200, r.status_code == 200, "Settings saved")

        r = await client.put(f"/api/exams/{exam_id}/toggle_publish", headers=teacher_headers)
        record("Toggle Exam Publish", "PUT", f"/api/exams/{exam_id}/toggle_publish", r.status_code, 200, r.status_code == 200, "Published state toggled")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 4: Question Authoring & Question Bank
        # -------------------------------------------------------------------------
        print("\n--- 4. Question Management & Bank Routes ---")
        q1_payload = {
            "text": "What is the worst-case time complexity of QuickSort?",
            "question_type": "MCQ",
            "option_a": "O(n)",
            "option_b": "O(n log n)",
            "option_c": "O(n^2)",
            "option_d": "O(1)",
            "correct_option": "C",
            "difficulty": "Medium",
            "bloom_level": "Understand",
            "max_marks": 2.0
        }
        r = await client.post(f"/api/exams/{exam_id}/questions", headers=teacher_headers, json=q1_payload)
        record("Add Question (MCQ)", "POST", f"/api/exams/{exam_id}/questions", r.status_code, [200, 201], r.status_code in (200, 201), "MCQ created")

        q2_payload = {
            "text": "Explain Dijkstra algorithm with greedy choice property.",
            "question_type": "SUBJECTIVE",
            "correct_option": "Dijkstra computes shortest paths using priority queue and relaxation.",
            "difficulty": "Hard",
            "bloom_level": "Analyze",
            "max_marks": 5.0
        }
        r = await client.post(f"/api/exams/{exam_id}/questions", headers=teacher_headers, json=q2_payload)
        record("Add Question (Subjective)", "POST", f"/api/exams/{exam_id}/questions", r.status_code, [200, 201], r.status_code in (200, 201), "Subjective created")

        r = await client.get(f"/api/exams/{exam_id}/questions", headers=teacher_headers)
        q_list = r.json()
        q1_id = q_list[0]["id"] if q_list else 1
        q2_id = q_list[1]["id"] if len(q_list) > 1 else 2
        record("List Exam Questions", "GET", f"/api/exams/{exam_id}/questions", r.status_code, 200, r.status_code == 200 and len(q_list) >= 2, f"Found {len(q_list)} questions")

        r = await client.get("/api/exams/bank", headers=teacher_headers)
        record("Fetch Global Question Bank", "GET", "/api/exams/bank", r.status_code, 200, r.status_code == 200, "Bank fetched")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 5: Question Intelligence System (QIS)
        # -------------------------------------------------------------------------
        print("\n--- 5. Question Intelligence System (QIS) Routes ---")
        analyze_payload = {
            "text": "What is the average case time complexity of MergeSort?",
            "options": {"A": "O(n)", "B": "O(n log n)", "C": "O(n^2)", "D": "O(1)"},
            "correct_option": "B",
            "course": "Algorithms"
        }
        r = await client.post("/api/ai/questions/analyze", headers=teacher_headers, json=analyze_payload)
        qis_res = r.json()
        record("QIS Single Question Analysis", "POST", "/api/ai/questions/analyze", r.status_code, 200, r.status_code == 200 and "classification" in qis_res, f"Bloom={qis_res.get('classification', {}).get('bloom', {}).get('label')}")

        # Compatibility Proxy on exam questions
        r = await client.post(f"/api/exams/{exam_id}/questions/analyze", headers=teacher_headers, json=analyze_payload)
        record("QIS Question Analyze Proxy", "POST", f"/api/exams/{exam_id}/questions/analyze", r.status_code, 200, r.status_code == 200, "Proxy route working")

        # Duplicate Detection
        r = await client.get(f"/api/ai/questions/exam/{exam_id}/duplicates", headers=teacher_headers)
        record("Duplicate Group Detection", "GET", f"/api/ai/questions/exam/{exam_id}/duplicates", r.status_code, 200, r.status_code == 200, "Exam duplicates checked")

        # Recommendations
        r = await client.get(f"/api/ai/questions/exam/{exam_id}/recommendations", headers=teacher_headers)
        record("Blueprint Gap Recommendations", "GET", f"/api/ai/questions/exam/{exam_id}/recommendations", r.status_code, 200, r.status_code == 200, "Recommendations engine queried")

        # Teacher Review Decision
        review_payload = {
            "decision": "ACCEPT",
            "adjusted_bloom": "Understand",
            "adjusted_difficulty": "Medium",
            "feedback": "Approved for midterm examination"
        }
        r = await client.post(f"/api/ai/questions/{q1_id}/review", headers=teacher_headers, json=review_payload)
        record("Submit Teacher Review Decision", "POST", f"/api/ai/questions/{q1_id}/review", r.status_code, 200, r.status_code == 200, "Decision ACCEPT stored")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 6: Assessment Assembly & Intelligence
        # -------------------------------------------------------------------------
        print("\n--- 6. Assessment Assembly & Blueprint Routes ---")
        assembly_payload = {
            "topics": {"Data Structures": 50, "Algorithms": 50},
            "difficulty_distribution": {"Easy": 30, "Medium": 40, "Hard": 30},
            "question_count": 2,
            "exam_type": "Objective"
        }
        r = await client.post("/api/intelligence/assemble", headers=teacher_headers, json=assembly_payload)
        record("Blueprint Assembly Engine", "POST", "/api/intelligence/assemble", r.status_code, 200, r.status_code == 200, "Constraint solver assembled paper")

        r = await client.get(f"/api/intelligence/{exam_id}/slots", headers=teacher_headers)
        record("Fetch Exam Slots", "GET", f"/api/intelligence/{exam_id}/slots", r.status_code, 200, r.status_code == 200, "Slots returned")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 7: Student Exam Session Lifecycle
        # -------------------------------------------------------------------------
        print("\n--- 7. Student Exam Session & Proctoring Lifecycle ---")
        r = await client.post(f"/api/exams/{exam_id}/start", headers=student_headers)
        start_data = r.json()
        attempt_id = start_data.get("attempt_id", 1)
        record("Start Exam Attempt", "POST", f"/api/exams/{exam_id}/start", r.status_code, [200, 201], r.status_code in (200, 201), f"Attempt ID={attempt_id}")

        proctor_event = {
            "attempt_id": attempt_id,
            "event_type": "TAB_SWITCH",
            "severity": "LOW",
            "confidence": 1.0,
            "duration_sec": 2
        }
        r = await client.post("/api/exams/proctoring_event", headers=student_headers, json=proctor_event)
        record("Log Proctoring Event", "POST", "/api/exams/proctoring_event", r.status_code, [200, 201], r.status_code in (200, 201), "Tab switch recorded")

        frame_payload = {
            "attempt_id": attempt_id,
            "frame": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
        }
        r = await client.post("/api/exams/analyze_frame", headers=student_headers, json=frame_payload)
        record("Proctoring Frame Analysis", "POST", "/api/exams/analyze_frame", r.status_code, 200, r.status_code == 200, "Frame ingestion processed")

        submit_payload = {
            "answers": {
                str(q1_id): "C",
                str(q2_id): "Dijkstra algorithm utilizes greedy choice by picking the minimum tentative distance node."
            },
            "attempt_id": attempt_id
        }
        r = await client.post(f"/api/exams/{exam_id}/submit", headers=student_headers, json=submit_payload)
        sub_res = r.json()
        record("Submit Exam Responses", "POST", f"/api/exams/{exam_id}/submit", r.status_code, 200, r.status_code == 200, f"Score={sub_res.get('score')}")

        r = await client.get(f"/api/exams/{exam_id}/review", headers=student_headers)
        record("Student Self Review", "GET", f"/api/exams/{exam_id}/review", r.status_code, 200, r.status_code == 200, "Review loaded")

        r = await client.get(f"/api/exams/{exam_id}/review/{student_id}", headers=teacher_headers)
        record("Teacher Student Review", "GET", f"/api/exams/{exam_id}/review/{student_id}", r.status_code, 200, r.status_code == 200, "Detailed answers loaded")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 8: Subjective Evaluation & Teacher Override
        # -------------------------------------------------------------------------
        print("\n--- 8. AI Subjective Evaluation & Teacher Grading ---")
        r = await client.post(f"/api/exams/{exam_id}/evaluate", headers=teacher_headers)
        record("AI Subjective Auto-Evaluation", "POST", f"/api/exams/{exam_id}/evaluate", r.status_code, 200, r.status_code == 200, "Dense semantic evaluation executed")

        db = SessionLocal()
        ans = db.query(Answer).filter_by(attempt_id=attempt_id, question_id=q2_id).first()
        ans_id = ans.id if ans else 1
        db.close()

        override_payload = {
            "marks_awarded": 4.5,
            "feedback": "Clear explanation of priority queue usage."
        }
        r = await client.put(f"/api/exams/answers/{ans_id}/grade", headers=teacher_headers, json=override_payload)
        record("Teacher Manual Grade Override", "PUT", f"/api/exams/answers/{ans_id}/grade", r.status_code, 200, r.status_code == 200, "Overridden to 4.5 marks")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 9: Knowledge Base & RAG Pipeline
        # -------------------------------------------------------------------------
        print("\n--- 9. RAG & Knowledge Base Routes ---")
        doc_payload = {
            "title": "Data Structures Syllabus 2026",
            "course_name": "CS201",
            "content": "Module 1 covers Stacks and Queues. Push and Pop operations execute in O(1) time complexity."
        }
        r = await client.post("/api/rag/documents", headers=teacher_headers, json=doc_payload)
        doc_res = r.json()
        doc_id = doc_res.get("document_id") or doc_res.get("id", 1)
        record("Ingest Syllabus Document", "POST", "/api/rag/documents", r.status_code, [200, 201], r.status_code in (200, 201), f"Doc ID={doc_id}")

        r = await client.get("/api/rag/documents", headers=teacher_headers)
        record("List Syllabus Documents", "GET", "/api/rag/documents", r.status_code, 200, r.status_code == 200 and len(r.json()) >= 1, "Documents listed")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 10: Analytics & Performance Reporting
        # -------------------------------------------------------------------------
        print("\n--- 10. Analytics & Performance Reporting Routes ---")
        r = await client.get(f"/api/analytics/exam/{exam_id}", headers=teacher_headers)
        record("Exam Analytics", "GET", f"/api/analytics/exam/{exam_id}", r.status_code, 200, r.status_code == 200, "Score distribution & pass rate")

        r = await client.get(f"/api/analytics/student/{student_id}", headers=teacher_headers)
        record("Student Analytics", "GET", f"/api/analytics/student/{student_id}", r.status_code, 200, r.status_code == 200, "Performance profile loaded")

        # -------------------------------------------------------------------------
        # ROUTE GROUP 11: Admin & Student Management
        # -------------------------------------------------------------------------
        print("\n--- 11. Admin & Student Management Routes ---")
        r = await client.get("/api/admin/stats", headers=admin_headers)
        record("Admin System Stats", "GET", "/api/admin/stats", r.status_code, 200, r.status_code == 200, "System metrics returned")

        r = await client.get("/api/admin/users", headers=admin_headers)
        record("Admin User Directory", "GET", "/api/admin/users", r.status_code, 200, r.status_code == 200, "Users retrieved")

        r = await client.get("/api/students/list", headers=teacher_headers)
        record("Teacher Student Roster", "GET", "/api/students/list", r.status_code, 200, r.status_code == 200, "Roster loaded")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    total_tested = len(results)
    passed_count = sum(1 for x in results if x["passed"])
    failed_count = total_tested - passed_count

    print("\n" + "=" * 80)
    print(f"AUDIT SUMMARY: {passed_count}/{total_tested} ROUTES PASSED ({passed_count/total_tested*100:.1f}%)")
    print("=" * 80)

    audit_file = os.path.join(BACKEND_DIR, "tests", "all_routes_verification_report.json")
    with open(audit_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tested": total_tested,
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": f"{passed_count/total_tested*100:.1f}%",
            "results": results
        }, f, indent=2)
    print(f"Detailed audit results saved to: {audit_file}")
    
    assert failed_count == 0, f"{failed_count} route(s) failed verification!"

if __name__ == "__main__":
    asyncio.run(run_route_audit())
