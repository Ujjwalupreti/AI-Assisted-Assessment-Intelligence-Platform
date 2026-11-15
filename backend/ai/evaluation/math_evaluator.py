"""
Symbolic Mathematical Answer Evaluator.
Integrates SymPy for safe, deterministic symbolic algebra and equation verification.
Never uses unsafe eval().
"""
import re
from typing import Dict, Any, List, Set
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)

# Constrained safe transformations
SAFE_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor
)

def _safe_parse_math(expr_str: str) -> sp.Expr:
    """
    Safely parses a mathematical expression string using SymPy.
    Strips LaTeX artifacts, dollar signs, and ensures no executable code can run.
    """
    if not expr_str or not str(expr_str).strip():
        return None
        
    cleaned = str(expr_str).strip()
    # Strip LaTeX formatting delimiters
    cleaned = cleaned.replace('$', '').replace('\\(', '').replace('\\)', '').replace('\\[', '').replace('\\]', '')
    cleaned = cleaned.replace('\\cdot', '*').replace('\\times', '*').replace('\\div', '/')
    cleaned = cleaned.replace('\\frac', '')
    cleaned = re.sub(r'\{([^{}]+)\}\{([^{}]+)\}', r'(\1)/(\2)', cleaned)
    cleaned = cleaned.replace('{', '(').replace('}', ')')
    cleaned = cleaned.replace('^', '**')
    
    # Restrict allowed characters to mathematical symbols
    if not re.match(r'^[0-9a-zA-Z\s\+\-\*\/\^\(\)\=\.\,\_]+$', cleaned):
        raise ValueError("Invalid mathematical characters detected")
        
    return parse_expr(cleaned, transformations=SAFE_TRANSFORMATIONS, evaluate=False)

def evaluate_math_answer(
    question_text: str,
    reference_answer: str,
    student_answer: str,
    max_marks: float = 1.0,
    rubric: str = None
) -> Dict[str, Any]:
    """
    Evaluates mathematical expressions, algebraic transformations, and equations.
    """
    max_marks = float(max_marks)
    if not student_answer or str(student_answer).strip() == "":
        return {
            "suggested_marks": 0.0,
            "max_marks": max_marks,
            "explanation": "No mathematical answer provided by the student.",
            "confidence": 1.0,
            "review_status": "COMPLETED",
            "evaluation_method": "SYMBOLIC_MATH",
            "model_name": "sympy-1.14",
            "issues": ["EMPTY_ANSWER"]
        }

    # If reference answer is missing, route to teacher
    if not reference_answer or str(reference_answer).strip() == "":
        return {
            "suggested_marks": 0.0,
            "max_marks": max_marks,
            "explanation": "No reference answer configured. Manual teacher review required.",
            "confidence": 0.0,
            "review_status": "NEEDS_REVIEW",
            "evaluation_method": "SYMBOLIC_MATH",
            "model_name": "sympy-1.14",
            "issues": ["MISSING_REFERENCE_ANSWER"]
        }

    issues = []
    
    # 1. Check for Equation Format (contains '=')
    is_equation = ('=' in str(student_answer) or '=' in str(reference_answer))
    
    try:
        if is_equation:
            return _evaluate_equation(reference_answer, student_answer, max_marks, rubric)
        else:
            return _evaluate_expression(reference_answer, student_answer, max_marks, rubric)
    except Exception as e:
        # Graceful fallback to teacher review on ambiguous or complex parsing
        return {
            "suggested_marks": 0.0,
            "max_marks": max_marks,
            "explanation": f"Complex or unsupported mathematical notation: {str(e)[:100]}. Routed for teacher review.",
            "confidence": 0.30,
            "review_status": "NEEDS_REVIEW",
            "evaluation_method": "SYMBOLIC_MATH",
            "model_name": "sympy-1.14",
            "issues": ["PARSING_ERROR", str(e)]
        }

def _evaluate_expression(ref_str: str, stu_str: str, max_marks: float, rubric: str) -> Dict[str, Any]:
    """Evaluates algebraic expressions (e.g. polynomials, expressions)."""
    ref_expr = _safe_parse_math(ref_str)
    stu_expr = _safe_parse_math(stu_str)
    
    # Algebraic Equivalence Check: simplify(student - reference) == 0
    diff = sp.simplify(stu_expr - ref_expr)
    if diff == 0:
        return {
            "suggested_marks": max_marks,
            "max_marks": max_marks,
            "explanation": "Mathematically identical and equivalent to the reference expression.",
            "confidence": 1.0,
            "review_status": "COMPLETED",
            "evaluation_method": "SYMBOLIC_MATH",
            "model_name": "sympy-1.14",
            "issues": []
        }
        
    # Check if student's answer is an expanded or factored equivalent
    ref_factored = sp.factor(ref_expr)
    stu_factored = sp.factor(stu_expr)
    if sp.simplify(stu_factored - ref_factored) == 0:
        return {
            "suggested_marks": max_marks,
            "max_marks": max_marks,
            "explanation": "Mathematically equivalent expression (valid factored or expanded form).",
            "confidence": 1.0,
            "review_status": "COMPLETED",
            "evaluation_method": "SYMBOLIC_MATH",
            "model_name": "sympy-1.14",
            "issues": []
        }

    # Partial Credit Check using Rubric or Sub-expression matching
    issues = ["EXPRESSION_MISMATCH"]
    partial_score = 0.0
    explanation = f"Expression does not match reference. Difference: {str(diff)[:80]}."
    
    # Check degree or terms similarity
    try:
        ref_symbols = ref_expr.free_symbols
        stu_symbols = stu_expr.free_symbols
        if ref_symbols == stu_symbols and len(ref_symbols) == 1:
            sym = list(ref_symbols)[0]
            ref_poly = sp.Poly(ref_expr, sym)
            stu_poly = sp.Poly(stu_expr, sym)
            if ref_poly.degree() == stu_poly.degree():
                partial_score = round(max_marks * 0.40, 2)
                explanation += " Same polynomial degree, but coefficients or constant terms differ."
                issues.append("CORRECT_DEGREE_WRONG_COEFFICIENTS")
    except Exception:
        pass

    return {
        "suggested_marks": partial_score,
        "max_marks": max_marks,
        "explanation": explanation,
        "confidence": 0.85 if partial_score == 0.0 else 0.65,
        "review_status": "COMPLETED" if partial_score == 0.0 else "NEEDS_REVIEW",
        "evaluation_method": "SYMBOLIC_MATH",
        "model_name": "sympy-1.14",
        "issues": issues
    }

def _evaluate_equation(ref_str: str, stu_str: str, max_marks: float, rubric: str) -> Dict[str, Any]:
    """Evaluates mathematical equations (e.g. x^2 - 5x + 6 = 0 or root lists x = 2, 3)."""
    # 0. Check for comma-separated root lists (e.g. x = 2, x = 3 or x = 3, 2)
    def extract_root_set(s: str) -> Set[Any]:
        # Extract numerical roots or simple algebraic constants
        raw_tokens = [tok.strip() for tok in re.split(r'[,;]', str(s)) if tok.strip()]
        roots = set()
        for tok in raw_tokens:
            if '=' in tok:
                tok = tok.split('=')[-1].strip()
            parsed = _safe_parse_math(tok)
            if parsed is not None:
                roots.add(sp.simplify(parsed))
        return roots

    # Check if either string is a comma-separated root list
    if ',' in ref_str or ',' in stu_str:
        ref_roots = extract_root_set(ref_str)
        stu_roots = extract_root_set(stu_str)
        if ref_roots:
            if ref_roots == stu_roots:
                return {
                    "suggested_marks": max_marks,
                    "max_marks": max_marks,
                    "explanation": f"Equation solution roots match perfectly: {ref_roots}.",
                    "confidence": 1.0,
                    "review_status": "COMPLETED",
                    "evaluation_method": "SYMBOLIC_MATH",
                    "model_name": "sympy-1.14",
                    "issues": []
                }
            intersection = ref_roots.intersection(stu_roots)
            if intersection:
                partial_marks = round(max_marks * (len(intersection) / len(ref_roots)), 2)
                return {
                    "suggested_marks": partial_marks,
                    "max_marks": max_marks,
                    "explanation": f"Partial roots correct: {intersection} of {ref_roots}.",
                    "confidence": 0.85,
                    "review_status": "NEEDS_REVIEW",
                    "evaluation_method": "SYMBOLIC_MATH",
                    "model_name": "sympy-1.14",
                    "issues": ["PARTIAL_SOLUTION_ROOTS"]
                }

    # Split LHS and RHS
    def parse_eq(eq_str):
        parts = eq_str.split('=')
        if len(parts) == 2:
            lhs = _safe_parse_math(parts[0])
            rhs = _safe_parse_math(parts[1])
            return sp.Eq(lhs, rhs)
        return _safe_parse_math(eq_str)

    ref_eq = parse_eq(ref_str)
    stu_eq = parse_eq(stu_str)
    
    # 1. Check direct equation equivalence: (lhs1 - rhs1) == c * (lhs2 - rhs2)
    if isinstance(ref_eq, sp.Equality) and isinstance(stu_eq, sp.Equality):
        ref_norm = sp.simplify(ref_eq.lhs - ref_eq.rhs)
        stu_norm = sp.simplify(stu_eq.lhs - stu_eq.rhs)
        
        diff = sp.simplify(stu_norm - ref_norm)
        if diff == 0:
            return {
                "suggested_marks": max_marks,
                "max_marks": max_marks,
                "explanation": "Equation is algebraically identical and verified.",
                "confidence": 1.0,
                "review_status": "COMPLETED",
                "evaluation_method": "SYMBOLIC_MATH",
                "model_name": "sympy-1.14",
                "issues": []
            }
            
        # Check proportional equivalence (e.g. 2x = 4 vs x = 2)
        ratio = sp.simplify(stu_norm / ref_norm)
        if ratio.is_number and ratio != 0:
            return {
                "suggested_marks": max_marks,
                "max_marks": max_marks,
                "explanation": "Equation is scalar equivalent to the reference equation.",
                "confidence": 1.0,
                "review_status": "COMPLETED",
                "evaluation_method": "SYMBOLIC_MATH",
                "model_name": "sympy-1.14",
                "issues": []
            }

    # 2. Check solution set equivalence (roots)
    try:
        ref_symbols = list(ref_eq.free_symbols) if hasattr(ref_eq, 'free_symbols') else []
        stu_symbols = list(stu_eq.free_symbols) if hasattr(stu_eq, 'free_symbols') else []
        
        if ref_symbols and stu_symbols:
            sym = ref_symbols[0]
            ref_sol = set(sp.solve(ref_eq, sym))
            stu_sol = set(sp.solve(stu_eq, sym))
            
            if ref_sol and stu_sol:
                if ref_sol == stu_sol:
                    return {
                        "suggested_marks": max_marks,
                        "max_marks": max_marks,
                        "explanation": f"Equation has identical solution roots: {ref_sol}.",
                        "confidence": 0.95,
                        "review_status": "COMPLETED",
                        "evaluation_method": "SYMBOLIC_MATH",
                        "model_name": "sympy-1.14",
                        "issues": []
                    }
                # Partial roots match
                intersection = ref_sol.intersection(stu_sol)
                if intersection:
                    partial_marks = round(max_marks * (len(intersection) / len(ref_sol)), 2)
                    return {
                        "suggested_marks": partial_marks,
                        "max_marks": max_marks,
                        "explanation": f"Partial roots correct: {intersection} of {ref_sol}.",
                        "confidence": 0.80,
                        "review_status": "NEEDS_REVIEW",
                        "evaluation_method": "SYMBOLIC_MATH",
                        "model_name": "sympy-1.14",
                        "issues": ["PARTIAL_SOLUTION_ROOTS"]
                    }
    except Exception:
        pass

    return {
        "suggested_marks": 0.0,
        "max_marks": max_marks,
        "explanation": "Equation does not match reference solution. Independent manual review suggested.",
        "confidence": 0.70,
        "review_status": "NEEDS_REVIEW",
        "evaluation_method": "SYMBOLIC_MATH",
        "model_name": "sympy-1.14",
        "issues": ["EQUATION_MISMATCH"]
    }
