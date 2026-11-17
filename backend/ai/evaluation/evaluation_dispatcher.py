"""
Central Multi-Format Subjective Evaluation Dispatcher.
Routes answers to specialized evaluators:
1. Math Evaluator (SymPy symbolic algebra, factoring, equation equivalence)
2. Automata Evaluator (DFA/NFA 5-tuple, string simulation, Hopcroft equivalence)
3. Diagram & File Evaluator (Structured table, digital PDF extraction, scanned image routing)
4. Text Evaluator (LLM + SentenceTransformers + Rubric)
"""
import json
import re
from typing import Dict, Any, Optional

from ai.evaluation.math_evaluator import evaluate_math_answer
from ai.evaluation.automata_evaluator import evaluate_automata_answer
from ai.evaluation.diagram_evaluator import evaluate_diagram_or_file
from ai.evaluation.text_evaluator import evaluate_text_answer

def evaluate_answer(
    question_text: str,
    student_answer: Any,
    reference_answer: str = None,
    max_marks: float = 1.0,
    rubric: str = None,
    answer_type: str = None,
    structured_answer: str = None,
    file_reference: str = None,
    use_rag: bool = False,
    course_name: str = None
) -> Dict[str, Any]:
    """
    Central evaluation dispatcher enforcing unified output schema.
    """
    max_marks = float(max_marks) if max_marks else 1.0
    
    # 1. Infer answer_type if not provided
    inferred_type = str(answer_type or "").upper()
    
    if not inferred_type or inferred_type in ("TEXT", "SUBJECTIVE", "NONE"):
        # Auto-detect if structured_answer contains automata JSON
        if structured_answer:
            try:
                parsed = json.loads(structured_answer) if isinstance(structured_answer, str) else structured_answer
                if isinstance(parsed, dict) and ("type" in parsed and parsed.get("type") in ("DFA", "NFA") or "transitions" in parsed):
                    inferred_type = "AUTOMATA_GRAPH"
                elif isinstance(parsed, dict) and ("table" in parsed or "rows" in parsed or parsed.get("type") == "TABLE"):
                    inferred_type = "TABLE"
            except Exception:
                pass

        # Auto-detect if student answer or reference contains mathematical equation/symbols
        if inferred_type not in ("AUTOMATA_GRAPH", "TABLE", "IMAGE_UPLOAD", "PDF_UPLOAD"):
            math_indicators = ["\\frac", "\\int", "\\sum", "x^2", "x**2", "= 0", "lim_", "\\sqrt", "\\times", "(x", "(y", "x-", "x+", "y-", "y+", "z-", "z+"]
            test_content = (str(student_answer or "") + " " + str(reference_answer or "")).lower()
            if any(ind in test_content for ind in math_indicators) or (re.search(r'\([a-z]\s*[\+\-\*\/]\s*\d+\)', test_content)) or (re.search(r'\b[a-zA-Z]\s*[\^\*]\s*\d', test_content)):
                inferred_type = "MATH_EQUATION"
            elif file_reference:
                if str(file_reference).lower().endswith('.pdf'):
                    inferred_type = "PDF_UPLOAD"
                else:
                    inferred_type = "IMAGE_UPLOAD"
            else:
                inferred_type = "TEXT"

    # 2. Dispatch to specialized engine
    result = None
    if inferred_type in ("AUTOMATA_GRAPH", "DFA", "NFA"):
        # Use structured_answer or student_answer
        auto_data = structured_answer or student_answer
        result = evaluate_automata_answer(
            question_text=question_text,
            reference_data=reference_answer,
            student_data=auto_data,
            max_marks=max_marks,
            rubric=rubric
        )
    elif inferred_type in ("MATH_EQUATION", "MATH"):
        result = evaluate_math_answer(
            question_text=question_text,
            reference_answer=reference_answer,
            student_answer=str(student_answer or ""),
            max_marks=max_marks,
            rubric=rubric
        )
    elif inferred_type in ("PDF_UPLOAD", "IMAGE_UPLOAD", "TABLE", "DIAGRAM"):
        result = evaluate_diagram_or_file(
            question_text=question_text,
            reference_answer=reference_answer,
            student_answer=str(student_answer or ""),
            max_marks=max_marks,
            rubric=rubric,
            file_reference=file_reference,
            structured_answer=structured_answer
        )
    else:
        # Standard descriptive text
        result = evaluate_text_answer(
            question_text=question_text,
            reference_answer=reference_answer,
            student_answer=str(student_answer or ""),
            max_marks=max_marks,
            rubric=rubric,
            use_rag=use_rag,
            course_name=course_name
        )

    # 3. Enforce Server-Side Clamping & Unified Schema
    s_marks = float(result.get("suggested_marks", 0.0))
    clamped_marks = round(max(0.0, min(s_marks, max_marks)), 2)
    result["suggested_marks"] = clamped_marks
    result["marks_awarded"] = clamped_marks
    result["max_marks"] = max_marks
    if "issues" not in result:
        result["issues"] = []
    if "confidence" not in result:
        result["confidence"] = 0.50
    if "review_status" not in result:
        result["review_status"] = "NEEDS_REVIEW" if result["confidence"] < 0.70 else "COMPLETED"
    result["needs_review"] = (result["review_status"] == "NEEDS_REVIEW")
    result["feedback"] = result.get("explanation", "")
    result["evaluation_tier"] = result.get("evaluation_method", "UNKNOWN")

    return result
