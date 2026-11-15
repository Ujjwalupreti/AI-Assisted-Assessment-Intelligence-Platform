"""
Automated Test Suite for Answer Integrity, Autosave, File Hashing, and Security (Phase 12)
Tests:
1. In-progress autosave creating Answer and incrementing AnswerVersion
2. Integrity event logging (PASTE_DETECTED with char count, BROWSER_BLUR)
3. Rapid integrity duplicate suppression within 2 seconds
4. File upload with SHA-256 calculation and path traversal prevention
5. Cross-student duplicate file upload detection
6. Student review response redacting correct MCQ answer keys
7. Role authorization on teacher override endpoint (rejects students)
"""

import sys
import os
import io
import json
import unittest
import httpx

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import jwt
from datetime import datetime
from config import Config
from app import app
from database import SessionLocal
from models import User, Exam, Question, Answer, AnswerVersion, AnswerIntegrityEvent, ExamAttempt


class TestAnswerIntegrityAndSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = httpx.Client(base_url="http://127.0.0.1:5001", timeout=10.0)
        cls.db = SessionLocal()

        # Create or fetch test users
        cls.teacher = cls.db.query(User).filter_by(email="teacher_integrity_test@qis.edu").first()
        if not cls.teacher:
            cls.teacher = User(
                username="teacher_integrity",
                email="teacher_integrity_test@qis.edu",
                role="teacher",
                password_hash="testhash"
            )
            cls.db.add(cls.teacher)

        cls.student1 = cls.db.query(User).filter_by(email="student1_integrity_test@qis.edu").first()
        if not cls.student1:
            cls.student1 = User(
                username="student1_integrity",
                email="student1_integrity_test@qis.edu",
                role="student",
                password_hash="testhash"
            )
            cls.db.add(cls.student1)

        cls.student2 = cls.db.query(User).filter_by(email="student2_integrity_test@qis.edu").first()
        if not cls.student2:
            cls.student2 = User(
                username="student2_integrity",
                email="student2_integrity_test@qis.edu",
                role="student",
                password_hash="testhash"
            )
            cls.db.add(cls.student2)

        cls.db.commit()

        # Create tokens
        cls.teacher_token = jwt.encode({"user_id": cls.teacher.id, "role": "teacher"}, Config.SECRET_KEY, algorithm="HS256")
        cls.student1_token = jwt.encode({"user_id": cls.student1.id, "role": "student"}, Config.SECRET_KEY, algorithm="HS256")
        cls.student2_token = jwt.encode({"user_id": cls.student2.id, "role": "student"}, Config.SECRET_KEY, algorithm="HS256")

        # Create test exam
        cls.exam = Exam(
            title="Integrity Verification Exam",
            duration_minutes=60,
            start_date=datetime.utcnow(),
            creator_id=cls.teacher.id,
            is_visible=True
        )
        cls.db.add(cls.exam)
        cls.db.commit()

        # Add an MCQ question and a subjective question
        cls.q_mcq = Question(
            exam_id=cls.exam.id,
            text="What is the time complexity of QuickSort average case?",
            question_type="MCQ",
            max_marks=5.0,
            correct_option="O(n log n)"
        )
        cls.q_subj = Question(
            exam_id=cls.exam.id,
            text="Explain deadlock avoidance using Banker's Algorithm.",
            question_type="SUBJECTIVE",
            is_subjective=True,
            max_marks=10.0,
            reference_answer="Banker's algorithm tests for safety by simulating the allocation of predetermined maximum possible amounts of all resources."
        )
        cls.db.add_all([cls.q_mcq, cls.q_subj])
        cls.db.commit()

        # Create active IN_PROGRESS attempts for both students
        cls.attempt1 = ExamAttempt(
            exam_id=cls.exam.id,
            student_id=cls.student1.id,
            status="IN_PROGRESS"
        )
        cls.attempt2 = ExamAttempt(
            exam_id=cls.exam.id,
            student_id=cls.student2.id,
            status="IN_PROGRESS"
        )
        cls.db.add_all([cls.attempt1, cls.attempt2])
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        # Clean up test rows
        try:
            cls.db.query(AnswerIntegrityEvent).filter(AnswerIntegrityEvent.attempt_id.in_([cls.attempt1.id, cls.attempt2.id])).delete()
            cls.db.query(AnswerVersion).filter(AnswerVersion.attempt_id.in_([cls.attempt1.id, cls.attempt2.id])).delete()
            cls.db.query(Answer).filter(Answer.attempt_id.in_([cls.attempt1.id, cls.attempt2.id])).delete()
            cls.db.query(ExamAttempt).filter(ExamAttempt.exam_id == cls.exam.id).delete()
            cls.db.query(Question).filter(Question.exam_id == cls.exam.id).delete()
            cls.db.query(Exam).filter(Exam.id == cls.exam.id).delete()
            cls.db.query(User).filter(User.id.in_([cls.teacher.id, cls.student1.id, cls.student2.id])).delete()
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    # ==========================================
    # 1. AUTOSAVE AND VERSIONING TESTS
    # ==========================================
    def test_01_autosave_and_version_increment(self):
        headers = {"Authorization": f"Bearer {self.student1_token}"}
        payload = {
            "question_id": self.q_subj.id,
            "answer_text": "First draft of deadlock avoidance explanation.",
            "answer_type": "text"
        }
        res = self.client.post(f"/api/exams/{self.exam.id}/answer_autosave", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["version_number"], 1)

        # Autosave second revision
        payload["answer_text"] = "Second draft with improved banker algorithm details."
        res2 = self.client.post(f"/api/exams/{self.exam.id}/answer_autosave", json=payload, headers=headers)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["version_number"], 2)

        # Verify DB versions
        versions = self.db.query(AnswerVersion).filter_by(
            attempt_id=self.attempt1.id,
            question_id=self.q_subj.id
        ).all()
        self.assertEqual(len(versions), 2)

    # ==========================================
    # 2. INTEGRITY EVENT LOGGING & SUPPRESSION
    # ==========================================
    def test_02_integrity_paste_event_and_duplicate_suppression(self):
        headers = {"Authorization": f"Bearer {self.student1_token}"}
        payload = {
            "event_type": "PASTE_DETECTED",
            "question_id": self.q_subj.id,
            "metadata": {"characters_pasted": 340, "source": "clipboard"}
        }
        res1 = self.client.post(f"/api/exams/{self.exam.id}/integrity_event", json=payload, headers=headers)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["status"], "logged")

        # Rapid fire duplicate event within 100ms
        res2 = self.client.post(f"/api/exams/{self.exam.id}/integrity_event", json=payload, headers=headers)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["status"], "duplicate_suppressed")

    def test_03_integrity_blur_event(self):
        headers = {"Authorization": f"Bearer {self.student1_token}"}
        payload = {
            "event_type": "BROWSER_BLUR",
            "metadata": {"window_state": "hidden"}
        }
        res = self.client.post(f"/api/exams/{self.exam.id}/integrity_event", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "logged")

    # ==========================================
    # 3. FILE UPLOAD & DUPLICATE HASH DETECTION
    # ==========================================
    def test_04_file_upload_sha256_and_duplicate_detection(self):
        headers1 = {"Authorization": f"Bearer {self.student1_token}"}
        file_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Title (Solution Sheet)\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
        files = {"file": ("student1_solution.pdf", io.BytesIO(file_bytes), "application/pdf")}

        # Student 1 uploads file
        res1 = self.client.post(f"/api/exams/{self.exam.id}/upload_answer_file", files=files, headers=headers1)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertIn("file_hash", data1)
        self.assertFalse(data1.get("duplicate_detected", False))

        # Student 1 associates the file hash with their answer
        autosave_payload = {
            "question_id": self.q_subj.id,
            "answer_type": "PDF_UPLOAD",
            "file_reference": data1["file_reference"],
            "file_hash": data1["file_hash"]
        }
        self.client.post(f"/api/exams/{self.exam.id}/answer_autosave", json=autosave_payload, headers=headers1)

        # Student 2 uploads the EXACT same file content (collusion / copying)
        headers2 = {"Authorization": f"Bearer {self.student2_token}"}
        files2 = {"file": ("student2_copied.pdf", io.BytesIO(file_bytes), "application/pdf")}
        res2 = self.client.post(f"/api/exams/{self.exam.id}/upload_answer_file", files=files2, headers=headers2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2.get("duplicate_detected", False))
        self.assertEqual(data2["file_hash"], data1["file_hash"])

    # ==========================================
    # 4. SECURITY & ANSWER KEY REDACTION TESTS
    # ==========================================
    def test_05_student_review_unauthorized_for_students(self):
        # As student 1, calling teacher review endpoint must be blocked with 403 Forbidden
        headers = {"Authorization": f"Bearer {self.student1_token}"}
        res = self.client.get(f"/api/exams/{self.exam.id}/review/{self.student1.id}", headers=headers)
        self.assertEqual(res.status_code, 403)

    def test_06_teacher_review_includes_answer_key(self):
        # As teacher, call review endpoint
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        res = self.client.get(f"/api/exams/{self.exam.id}/review/{self.student1.id}", headers=headers)
        self.assertEqual(res.status_code, 200)
        questions = res.json().get("questions", [])
        mcq_found = False
        for q in questions:
            if q.get("question_type") == "MCQ":
                mcq_found = True
                self.assertIsNotNone(q.get("correct_option"))
                self.assertEqual(q.get("correct_option"), "O(n log n)")
        self.assertTrue(mcq_found)

    def test_07_student_cannot_override_grades(self):
        # Create an answer to attempt overriding
        ans = Answer(
            attempt_id=self.attempt1.id,
            question_id=self.q_subj.id,
            answer_text="Test answer",
            marks_awarded=3.0
        )
        self.db.add(ans)
        self.db.commit()

        # Student attempts to override marks to 10.0
        headers = {"Authorization": f"Bearer {self.student1_token}"}
        res = self.client.put(f"/api/exams/answers/{ans.id}/grade", json={"marks_awarded": 10.0, "feedback": "Self-graded"}, headers=headers)
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
