"""
Complete End-to-End Subjective Assessment, Multimodal Answer Evaluation,
and AI Integration Test Suite.
Covers:
1. Question Creation across granular types with rubrics & AI assist endpoint.
2. Multimodal Student Answer Submissions (Text, Math, DFA/NFA, Table, File Upload).
3. Specialized AI/Deterministic Evaluation Pipeline (SymPy, Automata BFS, Table, MiniLM, Gemini).
4. Teacher Review & Grade Override with immutable EvaluationReview audit trail.
5. Security, Clamping, Anti-Injection, and Duplicate File Detection.
"""

import sys
import os
import io
import json
import uuid
import unittest
import httpx
from datetime import datetime, timedelta

# Put backend root on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from database import get_db
from models import (
    User, Exam, Question, ExamAttempt, Answer, Result,
    EvaluationReview, AnswerIntegrityEvent, AnswerVersion
)
from services.security_service import create_access_token
from ai.evaluation.evaluation_dispatcher import evaluate_answer
from ai.evaluation.math_evaluator import evaluate_math_answer
from ai.evaluation.automata_evaluator import evaluate_automata_answer
from ai.evaluation.diagram_evaluator import evaluate_diagram_or_file
from ai.evaluation.text_evaluator import evaluate_text_answer


class TestSubjectiveMultimodalSystem(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.app = create_app()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://testserver"
        )
        
        # Open DB session for fixture management
        self.db_gen = get_db()
        self.db = next(self.db_gen)

        # Unique suffix for test isolation
        self.uid = uuid.uuid4().hex[:6]
        
        # 1. Create Teacher
        self.teacher_email = f"prof_{self.uid}@qis.edu"
        self.teacher = User(
            username=f"Prof_{self.uid}",
            email=self.teacher_email,
            role="teacher",
            is_active=True,
            is_verified=True,
            enrollment_id=f"TCH_{self.uid}"
        )
        self.teacher.set_password("TeacherSecurePass123!")
        self.db.add(self.teacher)

        # 2. Create Student 1
        self.student1_email = f"stu1_{self.uid}@qis.edu"
        self.student1 = User(
            username=f"Student1_{self.uid}",
            email=self.student1_email,
            role="student",
            is_active=True,
            is_verified=True,
            enrollment_id=f"STU1_{self.uid}"
        )
        self.student1.set_password("StudentSecurePass123!")
        self.db.add(self.student1)

        # 3. Create Student 2
        self.student2_email = f"stu2_{self.uid}@qis.edu"
        self.student2 = User(
            username=f"Student2_{self.uid}",
            email=self.student2_email,
            role="student",
            is_active=True,
            is_verified=True,
            enrollment_id=f"STU2_{self.uid}"
        )
        self.student2.set_password("StudentSecurePass123!")
        self.db.add(self.student2)

        self.db.commit()

        # Generate tokens
        self.teacher_token = create_access_token(self.teacher)
        self.student1_token = create_access_token(self.student1)
        self.student2_token = create_access_token(self.student2)

        # 4. Create Test Exam
        self.exam = Exam(
            title=f"Advanced Multimodal Exam {self.uid}",
            duration_minutes=60,
            start_date=datetime.utcnow() - timedelta(minutes=10),
            end_date=datetime.utcnow() + timedelta(hours=2),
            creator_id=self.teacher.id,
            is_visible=True
        )
        self.db.add(self.exam)
        self.db.commit()

    async def asyncTearDown(self):
        # Cleanup exam and associated data
        try:
            self.db.query(EvaluationReview).filter(EvaluationReview.teacher_id == self.teacher.id).delete(synchronize_session=False)
            self.db.query(AnswerIntegrityEvent).delete(synchronize_session=False)
            self.db.query(AnswerVersion).delete(synchronize_session=False)
            self.db.query(Answer).delete(synchronize_session=False)
            self.db.query(Result).filter(Result.exam_id == self.exam.id).delete(synchronize_session=False)
            self.db.query(ExamAttempt).filter(ExamAttempt.exam_id == self.exam.id).delete(synchronize_session=False)
            self.db.query(Question).filter(Question.exam_id == self.exam.id).delete(synchronize_session=False)
            self.db.delete(self.exam)
            self.db.delete(self.teacher)
            self.db.delete(self.student1)
            self.db.delete(self.student2)
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()
            try:
                self.db_gen.close()
            except Exception:
                pass
            await self.client.aclose()

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN 1: QUESTION CREATION & TEACHER AI ASSISTANCE
    # ═══════════════════════════════════════════════════════════════════════════

    async def test_01_create_subjective_questions_with_rubrics(self):
        """Verify teacher can create different subjective question types with rubrics."""
        questions_to_create = [
            {
                "text": "Explain the concept of Virtual Memory and Page Faults.",
                "question_type": "SHORT_ANSWER",
                "reference_answer": "Virtual memory maps virtual to physical addresses. Page fault occurs when a requested page is not in RAM.",
                "rubric": "1. Virtual Memory definition (2 marks)\n2. Page fault explanation (3 marks)",
                "max_marks": 5.0,
                "topic": "Operating Systems",
                "difficulty": "Medium",
                "bloom_level": "Understand"
            },
            {
                "text": "Solve for x: x^2 - 7x + 12 = 0. Show the factored form.",
                "question_type": "MATH_PROBLEM",
                "reference_answer": "(x - 3)*(x - 4) = 0, roots: x = 3, 4",
                "rubric": "1. Factoring (3 marks)\n2. Correct roots (2 marks)",
                "max_marks": 5.0,
                "topic": "Algebra",
                "difficulty": "Easy",
                "bloom_level": "Apply"
            },
            {
                "text": "Design a DFA over alphabet {0, 1} that accepts all strings ending with '01'.",
                "question_type": "DFA_NFA",
                "reference_answer": json.dumps({
                    "type": "DFA",
                    "states": ["q0", "q1", "q2"],
                    "alphabet": ["0", "1"],
                    "initial_state": "q0",
                    "final_states": ["q2"],
                    "transitions": [
                        {"from": "q0", "symbol": "0", "to": "q1"},
                        {"from": "q0", "symbol": "1", "to": "q0"},
                        {"from": "q1", "symbol": "0", "to": "q1"},
                        {"from": "q1", "symbol": "1", "to": "q2"},
                        {"from": "q2", "symbol": "0", "to": "q1"},
                        {"from": "q2", "symbol": "1", "to": "q0"}
                    ]
                }),
                "rubric": "1. 5-tuple structure (2 marks)\n2. Correct state transitions (6 marks)\n3. Accepting state (2 marks)",
                "max_marks": 10.0,
                "topic": "Theory of Computation",
                "difficulty": "Hard",
                "bloom_level": "Create"
            },
            {
                "text": "Provide the truth table for a 2-input XOR gate.",
                "question_type": "TABLE",
                "reference_answer": json.dumps({
                    "type": "TABLE",
                    "headers": ["A", "B", "Output"],
                    "rows": [
                        ["0", "0", "0"],
                        ["0", "1", "1"],
                        ["1", "0", "1"],
                        ["1", "1", "0"]
                    ]
                }),
                "rubric": "1. Correct headers (1 mark)\n2. Correct truth rows (4 marks)",
                "max_marks": 5.0,
                "topic": "Digital Logic",
                "difficulty": "Easy",
                "bloom_level": "Remember"
            }
        ]

        created_ids = []
        for q_payload in questions_to_create:
            res = await self.client.post(
                f"/api/exams/{self.exam.id}/questions",
                json=q_payload,
                headers={"Authorization": f"Bearer {self.teacher_token}"}
            )
            self.assertEqual(res.status_code, 201, f"Failed creating {q_payload['question_type']}: {res.text}")
            created_ids.append(res.json()["id"])

        self.assertEqual(len(created_ids), 4)

        # Verify questions are returned with rubric and question_type
        get_res = await self.client.get(
            f"/api/exams/{self.exam.id}/questions",
            headers={"Authorization": f"Bearer {self.teacher_token}"}
        )
        self.assertEqual(get_res.status_code, 200)
        returned = get_res.json()
        self.assertEqual(len(returned), 4)
        
        types_returned = [q["question_type"] for q in returned]
        self.assertIn("SHORT_ANSWER", types_returned)
        self.assertIn("MATH_PROBLEM", types_returned)
        self.assertIn("DFA_NFA", types_returned)
        self.assertIn("TABLE", types_returned)
        
        # Verify rubric is preserved
        math_q = next(q for q in returned if q["question_type"] == "MATH_PROBLEM")
        self.assertIn("Factoring", math_q["rubric"])
        self.assertEqual(math_q["max_marks"], 5.0)

    async def test_02_teacher_ai_assist_endpoint(self):
        """Verify AI question improvement and rubric generation endpoint."""
        payload = {
            "text": "solve for x in quadratic equation x^2-5x+6=0",
            "question_type": "MATH_PROBLEM",
            "topic": "Algebra",
            "max_marks": 5.0
        }
        res = await self.client.post(
            "/api/ai/questions/assist",
            json=payload,
            headers={"Authorization": f"Bearer {self.teacher_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("suggested_version", data)
        self.assertIn("suggested_rubric", data)
        self.assertIn("suggested_bloom", data)
        self.assertIn("suggested_difficulty", data)
        self.assertIsInstance(data["identified_issues"], list)

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN 2: MULTIMODAL STUDENT SUBMISSIONS
    # ═══════════════════════════════════════════════════════════════════════════

    async def test_03_student_multimodal_submission(self):
        """Verify student can submit multimodal answers (text, math, automata, table, file)."""
        # Create a test question
        q = Question(
            exam_id=self.exam.id,
            text="Derive the derivative of f(x) = x^3 - 4x + 7.",
            is_subjective=True,
            question_type="DERIVATION",
            reference_answer="f'(x) = 3*x^2 - 4",
            max_marks=6.0,
            rubric="1. Power rule applied (3 marks)\n2. Final expression 3x^2-4 (3 marks)"
        )
        self.db.add(q)
        self.db.commit()

        # Student starts exam
        start_res = await self.client.post(
            f"/api/exams/{self.exam.id}/start",
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )
        self.assertEqual(start_res.status_code, 201)
        attempt_id = start_res.json()["attempt_id"]

        # Student autosaves draft
        autosave_res = await self.client.post(
            f"/api/exams/{self.exam.id}/answer_autosave",
            json={
                "question_id": q.id,
                "answer_text": "3*x^2 - 4",
                "answer_type": "MATH_EQUATION"
            },
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )
        self.assertEqual(autosave_res.status_code, 200)
        self.assertEqual(autosave_res.json()["version_number"], 1)

        # Student submits exam
        submit_res = await self.client.post(
            f"/api/exams/{self.exam.id}/submit",
            json={
                "answers": {
                    str(q.id): {
                        "answer_type": "MATH_EQUATION",
                        "text": "3*x^2 - 4"
                    }
                },
                "tab_switches": 0,
                "audio_warnings": 0
            },
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )
        self.assertEqual(submit_res.status_code, 200)

        # Verify submission saved to Answer table
        ans = self.db.query(Answer).filter_by(attempt_id=attempt_id, question_id=q.id).first()
        self.assertIsNotNone(ans)
        self.assertEqual(ans.submission_status, "SUBMITTED")
        self.assertEqual(ans.answer_text, "3*x^2 - 4")
        self.assertEqual(ans.answer_type, "MATH_EQUATION")

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN 3: SPECIALIZED EVALUATION ENGINES
    # ═══════════════════════════════════════════════════════════════════════════

    def test_04_sympy_symbolic_math_equivalence(self):
        """Test SymPy evaluation: factoring, commutativity, equivalent forms."""
        # 1. Factoring equivalence: (x-3)(x-2) vs (x-2)(x-3) vs x^2-5x+6
        res1 = evaluate_math_answer(
            question_text="Factor x^2 - 5x + 6",
            reference_answer="(x - 2)*(x - 3)",
            student_answer="(x - 3)*(x - 2)",
            max_marks=5.0
        )
        self.assertEqual(res1["suggested_marks"], 5.0)
        self.assertEqual(res1["confidence"], 1.0)
        self.assertEqual(res1["review_status"], "COMPLETED")

        # 2. Expanded equivalent: x^2 - 5x + 6 matches (x-2)(x-3)
        res2 = evaluate_math_answer(
            question_text="Factor x^2 - 5x + 6",
            reference_answer="(x - 2)*(x - 3)",
            student_answer="x^2 - 5x + 6",
            max_marks=5.0
        )
        self.assertEqual(res2["suggested_marks"], 5.0)

        # 3. Partially correct / wrong coefficients
        res3 = evaluate_math_answer(
            question_text="Factor x^2 - 5x + 6",
            reference_answer="(x - 2)*(x - 3)",
            student_answer="x^2 - 4x + 6",
            max_marks=5.0
        )
        self.assertLess(res3["suggested_marks"], 5.0)
        self.assertGreaterEqual(res3["suggested_marks"], 0.0)

        # 4. Roots set comparison: roots x = 2, 3 in reversed order
        res4 = evaluate_math_answer(
            question_text="Find the roots of x^2 - 5x + 6 = 0",
            reference_answer="x = 2, x = 3",
            student_answer="x = 3, x = 2",
            max_marks=5.0
        )
        self.assertEqual(res4["suggested_marks"], 5.0)

    def test_05_formal_automata_product_bfs(self):
        """Test automata evaluation: language equivalence and counterexample extraction."""
        # Reference DFA: strings ending with '1' over {0, 1}
        ref_dfa = {
            "type": "DFA",
            "states": ["A", "B"],
            "alphabet": ["0", "1"],
            "initial_state": "A",
            "final_states": ["B"],
            "transitions": [
                {"from": "A", "symbol": "0", "to": "A"},
                {"from": "A", "symbol": "1", "to": "B"},
                {"from": "B", "symbol": "0", "to": "A"},
                {"from": "B", "symbol": "1", "to": "B"}
            ]
        }

        # Student DFA with different state names (q0, q1) but identical language
        student_equiv_dfa = {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "initial_state": "q0",
            "final_states": ["q1"],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": "q0"},
                {"from": "q0", "symbol": "1", "to": "q1"},
                {"from": "q1", "symbol": "0", "to": "q0"},
                {"from": "q1", "symbol": "1", "to": "q1"}
            ]
        }

        res_equiv = evaluate_automata_answer(
            question_text="Design a DFA for strings ending with 1",
            reference_data=json.dumps(ref_dfa),
            student_data=json.dumps(student_equiv_dfa),
            max_marks=10.0
        )
        self.assertEqual(res_equiv["suggested_marks"], 10.0)
        self.assertEqual(res_equiv["confidence"], 1.0)
        self.assertEqual(res_equiv["review_status"], "COMPLETED")

        # Non-equivalent DFA: missing transition on '1' from final state
        student_wrong_dfa = {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "initial_state": "q0",
            "final_states": ["q1"],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": "q0"},
                {"from": "q0", "symbol": "1", "to": "q1"},
                {"from": "q1", "symbol": "0", "to": "q0"},
                {"from": "q1", "symbol": "1", "to": "q0"}  # WRONG: leads to q0 instead of q1
            ]
        }
        res_wrong = evaluate_automata_answer(
            question_text="Design a DFA for strings ending with 1",
            reference_data=json.dumps(ref_dfa),
            student_data=json.dumps(student_wrong_dfa),
            max_marks=10.0
        )
        self.assertLess(res_wrong["suggested_marks"], 10.0)
        self.assertIn("counterexample", res_wrong["explanation"].lower())

    def test_06_structured_table_evaluation(self):
        """Test structured table evaluation: exact match vs partial cell match."""
        ref_table = {
            "type": "TABLE",
            "headers": ["Input A", "Input B", "A AND B"],
            "rows": [
                ["0", "0", "0"],
                ["0", "1", "0"],
                ["1", "0", "0"],
                ["1", "1", "1"]
            ]
        }

        # Perfect student match
        stu_perfect = {
            "type": "TABLE",
            "headers": ["Input A", "Input B", "A AND B"],
            "rows": [
                ["0", "0", "0"],
                ["0", "1", "0"],
                ["1", "0", "0"],
                ["1", "1", "1"]
            ]
        }
        res_perfect = evaluate_diagram_or_file(
            question_text="AND truth table",
            reference_answer=json.dumps(ref_table),
            student_answer="[Structured Table]",
            max_marks=4.0,
            structured_answer=json.dumps(stu_perfect)
        )
        self.assertEqual(res_perfect["suggested_marks"], 4.0)
        self.assertEqual(res_perfect["confidence"], 1.0)
        self.assertEqual(res_perfect["review_status"], "COMPLETED")

        # Partial student match (1 cell wrong)
        stu_partial = {
            "type": "TABLE",
            "headers": ["Input A", "Input B", "A AND B"],
            "rows": [
                ["0", "0", "0"],
                ["0", "1", "0"],
                ["1", "0", "0"],
                ["1", "1", "0"]  # Error here: 0 instead of 1
            ]
        }
        res_partial = evaluate_diagram_or_file(
            question_text="AND truth table",
            reference_answer=json.dumps(ref_table),
            student_answer="[Structured Table]",
            max_marks=4.0,
            structured_answer=json.dumps(stu_partial)
        )
        self.assertLess(res_partial["suggested_marks"], 4.0)
        self.assertGreater(res_partial["suggested_marks"], 0.0)
        self.assertEqual(res_partial["review_status"], "NEEDS_REVIEW")

    def test_07_text_evaluation_and_empty_guard(self):
        """Test text evaluation tiers and zero-input protection."""
        # 1. Empty answer must receive 0.0 with confidence 1.0
        res_empty = evaluate_text_answer(
            question_text="What is polymorphism?",
            reference_answer="Polymorphism allows objects to take multiple forms.",
            student_answer="",
            max_marks=5.0
        )
        self.assertEqual(res_empty["suggested_marks"], 0.0)
        self.assertEqual(res_empty["confidence"], 1.0)
        self.assertIn("EMPTY_ANSWER", res_empty["issues"])

        # 2. Strong match via MiniLM or Gemini
        res_strong = evaluate_text_answer(
            question_text="Define polymorphism in OOP.",
            reference_answer="Polymorphism is an object-oriented programming concept where a single interface represents different underlying forms or data types.",
            student_answer="In object-oriented programming, polymorphism allows different classes to implement methods of the same interface with distinct behaviors.",
            max_marks=5.0
        )
        self.assertGreaterEqual(res_strong["suggested_marks"], 3.5)
        self.assertGreaterEqual(res_strong["confidence"], 0.65)

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN 4: TEACHER REVIEW & GRADE OVERRIDE WITH AUDIT TRAIL
    # ═══════════════════════════════════════════════════════════════════════════

    async def test_08_teacher_grade_override_and_audit_history(self):
        """Verify teacher can override marks, record feedback, and generate audit entries."""
        # Create question and attempt
        q = Question(
            exam_id=self.exam.id,
            text="Explain Dijkstra's Algorithm.",
            is_subjective=True,
            question_type="ALGORITHM",
            reference_answer="Dijkstra's algorithm finds shortest paths from source to all vertices in weighted graph with non-negative edge weights.",
            max_marks=10.0,
            rubric="1. Algorithm concept (4 marks)\n2. Non-negative weights constraint (3 marks)\n3. Complexity (3 marks)"
        )
        self.db.add(q)
        self.db.commit()

        # Student submission
        attempt = ExamAttempt(exam_id=self.exam.id, student_id=self.student1.id, status="SUBMITTED")
        self.db.add(attempt)
        self.db.commit()

        ans = Answer(
            attempt_id=attempt.id,
            question_id=q.id,
            answer_type="TEXT",
            answer_text="Dijkstra finds shortest path in a graph using greedy approach.",
            marks_awarded=4.0,
            ai_suggested_marks=4.0,
            ai_confidence=0.75,
            review_status="NEEDS_REVIEW"
        )
        self.db.add(ans)

        res_record = Result(
            exam_id=self.exam.id,
            student_id=self.student1.id,
            score=4.0,
            total_marks=10.0,
            total_questions=1
        )
        self.db.add(res_record)
        self.db.commit()

        # Teacher overrides grade from 4.0 to 8.5 with feedback
        override_res = await self.client.put(
            f"/api/exams/answers/{ans.id}/grade",
            json={
                "marks": 8.5,
                "feedback": "Good greedy explanation, but missed time complexity."
            },
            headers={"Authorization": f"Bearer {self.teacher_token}"}
        )
        self.assertEqual(override_res.status_code, 200)

        # Verify Answer was updated
        self.db.refresh(ans)
        self.assertEqual(ans.marks_awarded, 8.5)
        self.assertEqual(ans.teacher_feedback, "Good greedy explanation, but missed time complexity.")
        self.assertEqual(ans.review_status, "TEACHER_REVIEWED")

        # Verify Result was updated
        self.db.refresh(res_record)
        self.assertEqual(res_record.score, 8.5)

        # Verify EvaluationReview audit record was created!
        review_entry = self.db.query(EvaluationReview).filter_by(answer_id=ans.id).first()
        self.assertIsNotNone(review_entry)
        self.assertEqual(review_entry.teacher_id, self.teacher.id)
        self.assertEqual(review_entry.original_marks, 4.0)
        self.assertEqual(review_entry.new_marks, 8.5)
        self.assertIn("greedy", review_entry.comments)

        # Verify review endpoint for teacher returns review_history and rubric
        teacher_review_res = await self.client.get(
            f"/api/exams/{self.exam.id}/review/{self.student1.id}",
            headers={"Authorization": f"Bearer {self.teacher_token}"}
        )
        self.assertEqual(teacher_review_res.status_code, 200)
        review_body = teacher_review_res.json()
        self.assertEqual(review_body["score"], 8.5)
        
        q_data = review_body["questions"][0]
        self.assertEqual(q_data["max_marks"], 10.0)
        self.assertIn("Algorithm concept", q_data["rubric"])
        self.assertGreaterEqual(len(q_data["review_history"]), 1)
        self.assertEqual(q_data["review_history"][0]["new_marks"], 8.5)

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN 5: SECURITY, CLAMPING & DUPLICATE FILE DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def test_09_marks_clamping_and_bounds_enforcement(self):
        """Verify strict bounding: 0 <= marks <= max_marks."""
        # 1. Dispatcher enforces clamping even if sub-evaluator gives high number
        res = evaluate_answer(
            student_answer="some answer",
            reference_answer="some answer",
            max_marks=4.0,
            question_text="question"
        )
        self.assertGreaterEqual(res["marks_awarded"], 0.0)
        self.assertLessEqual(res["marks_awarded"], 4.0)

    async def test_10_file_upload_security_and_duplicate_detection(self):
        """Verify file upload size limit, allowed extensions, and SHA-256 duplicate detection."""
        # Student 1 starts exam
        s1_start = await self.client.post(
            f"/api/exams/{self.exam.id}/start",
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )
        self.assertEqual(s1_start.status_code, 201)

        # 1. Invalid extension rejected (.exe)
        invalid_file = io.BytesIO(b"malicious executable content")
        res_invalid = await self.client.post(
            f"/api/exams/{self.exam.id}/upload_answer_file",
            files={"file": ("exploit.exe", invalid_file, "application/octet-stream")},
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )
        self.assertEqual(res_invalid.status_code, 400)
        self.assertIn("Invalid file type", res_invalid.json()["message"])

        # 2. Oversized file rejected (>10MB)
        large_file = io.BytesIO(b"0" * (11 * 1024 * 1024))
        res_large = await self.client.post(
            f"/api/exams/{self.exam.id}/upload_answer_file",
            files={"file": ("large_drawing.png", large_file, "image/png")},
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )
        self.assertEqual(res_large.status_code, 400)
        self.assertIn("10 MB", res_large.json()["message"])

        # 3. Valid PDF uploaded by Student 1
        valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        res_valid = await self.client.post(
            f"/api/exams/{self.exam.id}/upload_answer_file",
            files={"file": ("solution.pdf", io.BytesIO(valid_pdf_content), "application/pdf")},
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )
        self.assertEqual(res_valid.status_code, 200)
        upload_data = res_valid.json()
        self.assertIn("file_reference", upload_data)
        self.assertIn("file_hash", upload_data)
        file_hash = upload_data["file_hash"]

        # Student 1 attaches file to their exam answer
        q_file = Question(exam_id=self.exam.id, text="Upload proof", is_subjective=True, question_type="FLOWCHART", reference_answer="None", max_marks=5.0)
        self.db.add(q_file)
        self.db.commit()

        await self.client.post(
            f"/api/exams/{self.exam.id}/submit",
            json={
                "answers": {
                    str(q_file.id): {
                        "answer_type": "PDF_UPLOAD",
                        "file_reference": upload_data["file_reference"],
                        "file_hash": file_hash
                    }
                }
            },
            headers={"Authorization": f"Bearer {self.student1_token}"}
        )

        # 4. Student 2 starts exam and uploads IDENTICAL file (collusion detection)
        s2_start = await self.client.post(
            f"/api/exams/{self.exam.id}/start",
            headers={"Authorization": f"Bearer {self.student2_token}"}
        )
        self.assertEqual(s2_start.status_code, 201)

        res_dup = await self.client.post(
            f"/api/exams/{self.exam.id}/upload_answer_file",
            files={"file": ("copied_solution.pdf", io.BytesIO(valid_pdf_content), "application/pdf")},
            headers={"Authorization": f"Bearer {self.student2_token}"}
        )
        self.assertEqual(res_dup.status_code, 200)
        self.assertTrue(res_dup.json()["duplicate_detected"])

        # Verify integrity event logged in database
        dup_event = self.db.query(AnswerIntegrityEvent).filter_by(event_type="DUPLICATE_FILE_DETECTED").first()
        self.assertIsNotNone(dup_event)
        self.assertEqual(dup_event.severity, "HIGH")
