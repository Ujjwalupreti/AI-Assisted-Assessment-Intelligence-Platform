import sys
import os

print("[DEBUG] Starting test script...", flush=True)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("[DEBUG] Importing math_evaluator...", flush=True)
from ai.evaluation.math_evaluator import evaluate_math_answer

print("[DEBUG] Importing automata_evaluator...", flush=True)
from ai.evaluation.automata_evaluator import evaluate_automata_answer

print("[DEBUG] Importing evaluation_dispatcher...", flush=True)
from ai.evaluation.evaluation_dispatcher import evaluate_answer


def run_tests():
    print("--- 1. MATH TEST: Factoring Equivalence ---")
    res_math = evaluate_math_answer(
        question_text='Factorize x^2 - 5x + 6',
        reference_answer='(x - 2)*(x - 3)',
        student_answer='(x - 3)*(x - 2)',
        max_marks=4.0
    )
    print("Math Test 1 Result:", res_math["suggested_marks"], res_math["explanation"])
    assert res_math["suggested_marks"] == 4.0, f"Expected 4.0, got {res_math['suggested_marks']}"

    print("\n--- 2. MATH TEST: Equation Solving ---")
    res_eq = evaluate_math_answer(
        question_text='Solve x^2 - 5x + 6 = 0',
        reference_answer='x^2 - 5x + 6 = 0',
        student_answer='(x - 2)*(x - 3) = 0',
        max_marks=5.0
    )
    print("Math Test 2 Result:", res_eq["suggested_marks"], res_eq["explanation"])
    assert res_eq["suggested_marks"] == 5.0, f"Expected 5.0, got {res_eq['suggested_marks']}"

    print("\n--- 3. AUTOMATA TEST: DFA Formal Language Equivalence ---")
    dfa_ref = {
        'type': 'DFA',
        'states': ['q0', 'q1'],
        'alphabet': ['0', '1'],
        'initial_state': 'q0',
        'final_states': ['q1'],
        'transitions': [
            {'from': 'q0', 'symbol': '0', 'to': 'q0'},
            {'from': 'q0', 'symbol': '1', 'to': 'q1'},
            {'from': 'q1', 'symbol': '0', 'to': 'q1'},
            {'from': 'q1', 'symbol': '1', 'to': 'q1'}
        ]
    }
    dfa_student = {
        'type': 'DFA',
        'states': ['A', 'B'],
        'alphabet': ['0', '1'],
        'initial_state': 'A',
        'final_states': ['B'],
        'transitions': [
            {'from': 'A', 'symbol': '0', 'to': 'A'},
            {'from': 'A', 'symbol': '1', 'to': 'B'},
            {'from': 'B', 'symbol': '0', 'to': 'B'},
            {'from': 'B', 'symbol': '1', 'to': 'B'}
        ]
    }
    res_auto = evaluate_automata_answer('DFA accepting strings with at least one 1', dfa_ref, dfa_student, max_marks=5.0)
    print("Automata Test 1 Result:", res_auto["suggested_marks"], res_auto["explanation"])
    assert res_auto["suggested_marks"] == 5.0, f"Expected 5.0, got {res_auto['suggested_marks']}"

    print("\n--- 4. AUTOMATA TEST: Counterexample on Non-Equivalent DFA ---")
    dfa_bad = {
        'type': 'DFA',
        'states': ['A', 'B'],
        'alphabet': ['0', '1'],
        'initial_state': 'A',
        'final_states': ['B'],
        'transitions': [
            {'from': 'A', 'symbol': '0', 'to': 'A'},
            {'from': 'A', 'symbol': '1', 'to': 'A'}, # Missing transition to B!
            {'from': 'B', 'symbol': '0', 'to': 'B'},
            {'from': 'B', 'symbol': '1', 'to': 'B'}
        ]
    }
    res_bad = evaluate_automata_answer('DFA accepting strings with at least one 1', dfa_ref, dfa_bad, max_marks=5.0)
    print("Automata Test 2 (Counterexample):", res_bad["suggested_marks"], res_bad["explanation"])
    assert res_bad["suggested_marks"] < 5.0, "Should have penalized non-equivalent DFA"
    assert "Counterexample" in res_bad["explanation"] or "counterexample" in res_bad["explanation"].lower()

    print("\n--- 5. DISPATCHER TEST: Auto-Routing to Math and Automata ---")
    disp_math = evaluate_answer("Find roots", "(x-2)(x-3)", "(x-3)(x-2)", max_marks=3.0)
    assert disp_math["evaluation_method"] == "SYMBOLIC_MATH"
    assert disp_math["suggested_marks"] == 3.0
    print("Dispatcher Math Routing: OK")

    print("\n==========================================")
    print("ALL SPECIALIZED EVALUATOR TESTS PASSED 100%")
    print("==========================================")

if __name__ == '__main__':
    run_tests()
