"""
Question Type Classifier.

Architecture:
    Primary: Structural detection (strongest signal for MCQ, True/False, etc.)
    Secondary: LLM for ambiguous cases
    Fallback: Heuristic

Returns canonical QuestionTypeResult schema: {label, confidence, method}
"""
import re
from .llm_client import generate_json
from .schemas import QuestionTypeResult

VALID_TYPES = ["MCQ", "TRUE_FALSE", "SHORT_ANSWER", "LONG_ANSWER", "NUMERICAL", "CODING", "FILL_IN_THE_BLANK"]


def classify_question_type(question_text: str, options: dict = None) -> QuestionTypeResult:
    """
    Detect question type using structural evidence first, then LLM.
    Structural checks are strong signals — MCQ with 4 options is near-certain.
    """
    # ── Structural checks FIRST (strongest signal) ──
    if options:
        filled_options = [v for v in options.values() if v and v.strip()]
        if len(filled_options) >= 3:
            return {"label": "MCQ", "confidence": 0.97, "method": "structural"}

    text_lower = question_text.lower()

    # True/False structural detection
    if re.search(r'\b(true or false|true/false|state whether|is it true)\b', text_lower):
        return {"label": "TRUE_FALSE", "confidence": 0.95, "method": "structural"}

    # Fill in the blank
    if "_____" in question_text or "____" in question_text or "___" in question_text:
        return {"label": "FILL_IN_THE_BLANK", "confidence": 0.95, "method": "structural"}

    # Numerical
    num_keywords = ["calculate", "compute", "find the value", "what is the value", "how many", "how much", "evaluate the expression"]
    if any(kw in text_lower for kw in num_keywords):
        return {"label": "NUMERICAL", "confidence": 0.70, "method": "structural"}

    # Coding
    code_keywords = ["write a program", "implement", "write code", "write an algorithm", "write a function", "write pseudocode"]
    if any(kw in text_lower for kw in code_keywords):
        return {"label": "CODING", "confidence": 0.85, "method": "structural"}

    # ── LLM for ambiguous cases ──
    try:
        prompt = f"""
Classify this exam question type.
Types: MCQ, TRUE_FALSE, SHORT_ANSWER, LONG_ANSWER, NUMERICAL, CODING, FILL_IN_THE_BLANK

Question: {question_text}

Return ONLY valid JSON: {{"label": "<type>", "confidence": <0.0-1.0>}}
"""
        result = generate_json(prompt)
        if result and "label" in result:
            label = result.get("label", "SHORT_ANSWER")
            # Handle old "question_type" key
            if "question_type" in result and "label" not in result:
                label = result["question_type"]
            if label not in VALID_TYPES:
                label = "SHORT_ANSWER"
            return {
                "label": label,
                "confidence": float(result.get("confidence", 0.6)),
                "method": "llm"
            }
    except Exception as e:
        print(f"[question_type_classifier] LLM error: {e}")

    # ── Heuristic fallback ──
    # Long questions with "explain" / "discuss" / "describe" → LONG_ANSWER
    long_keywords = ["explain", "discuss", "elaborate", "describe in detail", "write an essay"]
    if any(kw in text_lower for kw in long_keywords) and len(question_text.split()) > 15:
        return {"label": "LONG_ANSWER", "confidence": 0.35, "method": "heuristic_fallback"}

    return {"label": "SHORT_ANSWER", "confidence": 0.25, "method": "heuristic_fallback"}
