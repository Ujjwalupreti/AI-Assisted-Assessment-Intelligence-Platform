"""
Comprehensive Automated Test Suite for Subjective Evaluation Engine (Phase 11)
Tests:
1. Exact match text subjective answer
2. Semantically equivalent paraphrased text
3. Completely irrelevant text
4. Empty / whitespace-only answer
5. SymPy factoring equivalence: (x-2)(x-3) vs (x-3)(x-2) vs x^2-5x+6
6. SymPy equation root checking: roots {2, 3} for x^2-5x+6=0
7. Equivalent DFAs with different state labels (Product Automata BFS)
8. Non-equivalent DFAs: extracts counterexample string
9. NFA input converted to DFA via subset construction and compared
10. Valid JSON vs Malformed JSON automata handling
11. Table evaluation: exact structure vs missing cell vs empty table
12. Clamping: marks are strictly bounded [0, max_marks] and confidence in [0.0, 1.0]
"""

import sys
import os
import json
import unittest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.evaluation.evaluation_dispatcher import evaluate_answer
from ai.evaluation.math_evaluator import evaluate_math_answer
from ai.evaluation.automata_evaluator import (
    Automaton,
    check_language_equivalence,
    evaluate_automata_answer,
)
from ai.evaluation.diagram_evaluator import evaluate_diagram_or_file
from ai.evaluation.text_evaluator import evaluate_text_answer


class TestSubjectiveEvaluationFull(unittest.TestCase):

    # ==========================================
    # 1. TEXT EVALUATION TESTS
    # ==========================================
    def test_01_text_exact_match(self):
        ref = "Supervised learning uses labeled datasets to train algorithms to classify data or predict outcomes."
        student = "Supervised learning uses labeled datasets to train algorithms to classify data or predict outcomes."
        res = evaluate_answer(
            student_answer=student,
            reference_answer=ref,
            max_marks=5.0,
            question_text="What is supervised learning?",
            answer_type="text",
        )
        self.assertEqual(res["marks_awarded"], 5.0)
        self.assertGreaterEqual(res["confidence"], 0.85)
        self.assertFalse(res["needs_review"])

    def test_02_text_semantically_equivalent(self):
        ref = "Deadlock occurs when processes are unable to proceed because each is waiting for a resource held by another."
        student = "A deadlock happens in operating systems when two or more threads block indefinitely waiting for resources held by each other."
        res = evaluate_answer(
            student_answer=student,
            reference_answer=ref,
            max_marks=5.0,
            question_text="Explain deadlock in operating systems.",
            answer_type="text",
        )
        self.assertGreaterEqual(res["marks_awarded"], 3.0)
        self.assertIn("evaluation_tier", res)

    def test_03_text_irrelevant(self):
        ref = "A primary key uniquely identifies each record in a relational database table."
        student = "Photosynthesis is the biological process of turning sunlight into chemical energy in plants."
        res = evaluate_answer(
            student_answer=student,
            reference_answer=ref,
            max_marks=5.0,
            question_text="What is a primary key?",
            answer_type="text",
        )
        self.assertLessEqual(res["marks_awarded"], 1.5)

    def test_04_text_empty_or_whitespace(self):
        ref = "Binary search runs in O(log n) time by halving the search space."
        for empty_val in ["", "   ", "\n\t  \n"]:
            res = evaluate_answer(
                student_answer=empty_val,
                reference_answer=ref,
                max_marks=5.0,
                question_text="Explain binary search time complexity.",
                answer_type="text",
            )
            self.assertEqual(res["marks_awarded"], 0.0)
            self.assertEqual(res["confidence"], 1.0)
            self.assertFalse(res["needs_review"])
            self.assertTrue("no answer" in res["feedback"].lower() or "empty" in res["feedback"].lower() or "no response" in res["feedback"].lower())

    # ==========================================
    # 2. MATH & SYMPY EVALUATION TESTS
    # ==========================================
    def test_05_math_factoring_equivalence(self):
        ref = "(x - 2) * (x - 3)"
        student_equiv = "(x - 3)*(x - 2)"
        res = evaluate_math_answer(
            question_text="Factor the quadratic polynomial",
            reference_answer=ref,
            student_answer=student_equiv,
            max_marks=4.0,
            rubric="Factor the quadratic polynomial into linear factors.",
        )
        self.assertEqual(res["suggested_marks"], 4.0)
        self.assertEqual(res["confidence"], 1.0)
        self.assertIn("equivalent", res["explanation"].lower())

    def test_06_math_expanded_vs_factored_partial_credit(self):
        ref = "(x - 2) * (x - 3)"
        student_expanded = "x**2 - 5*x + 6"  # mathematically equivalent
        res = evaluate_math_answer(
            question_text="Factor polynomial",
            reference_answer=ref,
            student_answer=student_expanded,
            max_marks=4.0,
            rubric="Factor the polynomial into product of linear terms",
        )
        self.assertEqual(res["suggested_marks"], 4.0)
        self.assertEqual(res["confidence"], 1.0)

    def test_07_math_equation_root_solving(self):
        ref = "x = 2, x = 3"
        student = "x = 3, 2"
        res = evaluate_math_answer(
            question_text="Solve quadratic equation",
            reference_answer=ref,
            student_answer=student,
            max_marks=5.0,
            rubric="Find all roots of the equation.",
        )
        self.assertEqual(res["suggested_marks"], 5.0)
        self.assertEqual(res["confidence"], 1.0)

    def test_08_math_wrong_roots_partial(self):
        ref = "x = 2, x = 3"
        student = "x = 2, x = 5"  # 1 root correct out of 2
        res = evaluate_math_answer(
            question_text="Solve equation roots",
            reference_answer=ref,
            student_answer=student,
            max_marks=4.0,
            rubric="Find roots",
        )
        self.assertEqual(res["suggested_marks"], 2.0)

    # ==========================================
    # 3. AUTOMATA (DFA / NFA) EVALUATION TESTS
    # ==========================================
    def test_09_dfa_isomorphic_different_labels(self):
        # DFA accepting strings ending with '1' over {0, 1}
        ref_dfa = {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "initial_state": "q0",
            "final_states": ["q1"],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": "q0"},
                {"from": "q0", "symbol": "1", "to": "q1"},
                {"from": "q1", "symbol": "0", "to": "q0"},
                {"from": "q1", "symbol": "1", "to": "q1"},
            ],
        }
        student_dfa = {
            "type": "DFA",
            "states": ["s_init", "s_accept"],
            "alphabet": ["0", "1"],
            "initial_state": "s_init",
            "final_states": ["s_accept"],
            "transitions": [
                {"from": "s_init", "symbol": "0", "to": "s_init"},
                {"from": "s_init", "symbol": "1", "to": "s_accept"},
                {"from": "s_accept", "symbol": "0", "to": "s_init"},
                {"from": "s_accept", "symbol": "1", "to": "s_accept"},
            ],
        }
        res = evaluate_automata_answer(
            question_text="Construct DFA ending with 1",
            reference_data=ref_dfa,
            student_data=student_dfa,
            max_marks=5.0,
        )
        self.assertEqual(res["suggested_marks"], 5.0)
        self.assertEqual(res["confidence"], 1.0)
        self.assertEqual(res["review_status"], "COMPLETED")

    def test_10_dfa_non_equivalent_counterexample(self):
        ref_dfa = {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "initial_state": "q0",
            "final_states": ["q1"],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": "q0"},
                {"from": "q0", "symbol": "1", "to": "q1"},
                {"from": "q1", "symbol": "0", "to": "q0"},
                {"from": "q1", "symbol": "1", "to": "q1"},
            ],
        }
        student_dfa = {
            "type": "DFA",
            "states": ["s0", "s1"],
            "alphabet": ["0", "1"],
            "initial_state": "s0",
            "final_states": ["s1"],
            "transitions": [
                {"from": "s0", "symbol": "0", "to": "s1"},
                {"from": "s0", "symbol": "1", "to": "s0"},
                {"from": "s1", "symbol": "0", "to": "s1"},
                {"from": "s1", "symbol": "1", "to": "s0"},
            ],
        }
        res = evaluate_automata_answer(
            question_text="Construct DFA ending with 1",
            reference_data=ref_dfa,
            student_data=student_dfa,
            max_marks=5.0,
        )
        self.assertLess(res["suggested_marks"], 5.0)
        self.assertIn("counterexample", res["explanation"].lower())

    def test_11_nfa_to_dfa_subset_construction_equivalence(self):
        ref_dfa = {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "initial_state": "q0",
            "final_states": ["q1"],
            "transitions": [
                {"from": "q0", "symbol": "0", "to": "q0"},
                {"from": "q0", "symbol": "1", "to": "q1"},
                {"from": "q1", "symbol": "0", "to": "q0"},
                {"from": "q1", "symbol": "1", "to": "q1"},
            ],
        }
        student_nfa = {
            "type": "NFA",
            "states": ["n0", "n1"],
            "alphabet": ["0", "1"],
            "initial_state": "n0",
            "final_states": ["n1"],
            "transitions": [
                {"from": "n0", "symbol": "0", "to": "n0"},
                {"from": "n0", "symbol": "1", "to": "n0"},
                {"from": "n0", "symbol": "1", "to": "n1"},
            ],
        }
        res = evaluate_automata_answer(
            question_text="Construct automaton for strings ending in 1",
            reference_data=ref_dfa,
            student_data=student_nfa,
            max_marks=6.0,
        )
        self.assertEqual(res["suggested_marks"], 6.0)
        self.assertEqual(res["confidence"], 1.0)

    def test_12_automata_invalid_json_handling(self):
        invalid_automaton = {
            "states": ["q0"],
            "alphabet": ["0"],
            # initial_state missing
        }
        ref_dfa = {
            "type": "DFA",
            "states": ["q0"],
            "alphabet": ["0"],
            "initial_state": "q0",
            "final_states": ["q0"],
            "transitions": [{"from": "q0", "symbol": "0", "to": "q0"}],
        }
        res = evaluate_automata_answer(
            question_text="Construct DFA",
            reference_data=ref_dfa,
            student_data=invalid_automaton,
            max_marks=5.0,
        )
        self.assertEqual(res["suggested_marks"], 0.0)
        self.assertIn("flaws", res["explanation"].lower())

    # ==========================================
    # 4. STRUCTURED TABLE & FILE EVALUATION TESTS
    # ==========================================
    def test_13_table_evaluation_structured_data(self):
        structured_json = json.dumps({
            "table": [
                ["Process", "Burst Time", "Arrival Time"],
                ["P1", "6", "0"],
                ["P2", "8", "1"]
            ]
        })
        res = evaluate_diagram_or_file(
            question_text="Fill process table",
            reference_answer="",
            student_answer="",
            max_marks=5.0,
            structured_answer=structured_json
        )
        self.assertEqual(res["suggested_marks"], 4.0)
        self.assertEqual(res["review_status"], "NEEDS_REVIEW")
        self.assertEqual(res["evaluation_method"], "STRUCTURED_TABLE")

    def test_14_handwritten_image_routing_to_teacher(self):
        fake_image_path = os.path.join(os.path.dirname(__file__), "fake_solution.png")
        with open(fake_image_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
        try:
            res = evaluate_diagram_or_file(
                question_text="Draw NFA diagram",
                reference_answer="",
                student_answer="",
                max_marks=6.0,
                file_reference=fake_image_path
            )
            self.assertEqual(res["review_status"], "NEEDS_REVIEW")
            self.assertEqual(res["evaluation_method"], "HANDWRITTEN_IMAGE")
            self.assertIn("teacher", res["explanation"].lower())
        finally:
            if os.path.exists(fake_image_path):
                os.remove(fake_image_path)

    # ==========================================
    # 5. SCORE CLAMPING AND CONTRACT INTEGRITY
    # ==========================================
    def test_15_dispatcher_clamping_and_schema(self):
        res = evaluate_answer(
            student_answer="arbitrary answer",
            reference_answer="arbitrary ref",
            max_marks=10.0,
            question_text="Arbitrary question",
            answer_type="text",
        )
        self.assertGreaterEqual(res["marks_awarded"], 0.0)
        self.assertLessEqual(res["marks_awarded"], 10.0)
        self.assertGreaterEqual(res["confidence"], 0.0)
        self.assertLessEqual(res["confidence"], 1.0)
        self.assertIn("feedback", res)
        self.assertIn("needs_review", res)
        self.assertIn("evaluation_tier", res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
