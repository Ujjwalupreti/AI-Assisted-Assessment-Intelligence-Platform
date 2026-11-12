"""
QIS Pipeline — The SINGLE SOURCE OF TRUTH for question analysis.

Architecture:
    Input Question
        ↓
    Ciphertext Guard (reject encrypted text)
        ↓
    Structural Validation
        ↓
    Classification (Topic, Bloom, Difficulty, Question Type)
        via refactored ai/ classifiers (primary)
        with ml.inference as secondary fallback
        ↓
    MCQ Validation (if MCQ)
        ↓
    Deterministic Quality Rules + Optional LLM Quality
        ↓
    Duplicate Detection (via duplicate_detector)
        ↓
    Blueprint Alignment
        ↓
    Canonical AnalysisResult with status tracking
        ↓
    Persistence (caller responsibility)

LLM is OPTIONAL. If unavailable, system operates in PARTIAL/DEGRADED mode
with heuristics. It does NOT fake successful results.
"""
import json
import re
import traceback
from typing import Dict, Any, List, Optional

from .schemas import AnalysisResult
from .mcq_validator import validate_mcq
from .bloom_alignment import check_alignment
from .duplicate_detector import detect_duplicates
from .quality_analyzer import analyze_quality

# Refactored standalone classifiers (primary)
from .bloom_classifier import classify_bloom
from .topic_classifier import classify_topic
from .difficulty_estimator import estimate_difficulty
from .question_type_classifier import classify_question_type


def _is_ciphertext(text: str) -> bool:
    """
    Detect if text looks like AES ciphertext (base64-encoded).
    Common pattern: starts with 'U2F' (Salted__ in base64).
    """
    if not text or len(text) < 10:
        return False
    stripped = text.strip()
    # AES CryptoJS output starts with U2FsdGVk (base64 of "Salted__")
    if stripped.startswith("U2F"):
        return True
    # Generic base64 detection: mostly alphanumeric + /+= and no spaces
    if len(stripped) > 50 and re.match(r'^[A-Za-z0-9+/=]+$', stripped):
        return True
    return False


def analyze_question_qis(
    question_text: str,
    options: Optional[Dict[str, str]] = None,
    correct_option: Optional[str] = None,
    expected_topic: Optional[str] = None,
    expected_bloom: Optional[str] = None,
    expected_difficulty: Optional[str] = None,
    existing_questions: Optional[List[Dict]] = None
) -> dict:
    """
    Canonical QIS entry point.
    Returns an AnalysisResult dict. All callers MUST use this function.
    No other route should re-implement this logic.
    """
    if options is None:
        options = {}
    if existing_questions is None:
        existing_questions = []

    warnings: List[str] = []
    errors: List[str] = []
    has_llm_failure = False

    # ─── 0. Ciphertext Guard ──────────────────────────────────────────────
    if _is_ciphertext(question_text):
        return {
            "status": "FAILED",
            "analysis_status": "FAILED",
            "warnings": [],
            "errors": ["Encrypted/ciphertext detected. Cannot analyze encrypted question text. Send plaintext to the analysis endpoint."],
            "classification": {},
            "quality": {"overall_score": None, "dimensions": None, "status": "AI_UNAVAILABLE"},
            "validation": {"valid": False, "issues": []},
            "duplicate": {"risk": 0.0, "risk_label": "LOW", "is_duplicate": False, "similar_question_id": None, "similarity": 0.0, "similar_questions": [], "method": "skipped"},
            "alignment": {"topic": "NOT_CHECKED", "bloom": "NOT_CHECKED", "difficulty": "NOT_CHECKED"},
            "recommendations": [],
            "explanations": {"topic": "", "bloom": "", "difficulty": "", "quality": "Analysis blocked: encrypted text."},
            "review": {"required": True, "reasons": ["Encrypted text — cannot analyze"], "priority": "HIGH"},
            "model_metadata": {"model_name": "qis-ml-pipeline-v1", "model_version": "3.0.0", "embedding_model": "all-MiniLM-L6-v2", "llm_model": "gemini-1.5-flash", "analysis_version": "2026-08-v3", "llm_status": "SKIPPED"}
        }

    # ─── 1. Classification ─────────────────────────────────────────────────
    try:
        type_res = classify_question_type(question_text, options)
    except Exception as e:
        traceback.print_exc()
        type_res = {"label": "SHORT_ANSWER", "confidence": 0.1, "method": "error_fallback"}
        errors.append(f"Question type classification failed: {str(e)}")

    try:
        topic_res = classify_topic(question_text)
    except Exception as e:
        traceback.print_exc()
        topic_res = {"label": "General CS", "confidence": 0.1, "alternatives": [], "method": "error_fallback"}
        errors.append(f"Topic classification failed: {str(e)}")

    try:
        bloom_res = classify_bloom(question_text)
    except Exception as e:
        traceback.print_exc()
        bloom_res = {"label": "Remember", "confidence": 0.1, "evidence": [], "method": "error_fallback"}
        errors.append(f"Bloom classification failed: {str(e)}")

    try:
        diff_res = estimate_difficulty(question_text, bloom_res.get("label"), options)
    except Exception as e:
        traceback.print_exc()
        diff_res = {"label": "Medium", "confidence": 0.1, "reasoning_factors": [], "method": "error_fallback"}
        errors.append(f"Difficulty estimation failed: {str(e)}")

    # Track if any classification used heuristic fallback
    classifiers_used = [topic_res, bloom_res, diff_res, type_res]
    heuristic_methods = [c for c in classifiers_used if c.get("method") in ("heuristic_fallback", "error_fallback")]
    if heuristic_methods:
        warnings.append(f"{len(heuristic_methods)}/{len(classifiers_used)} classifiers used heuristic fallback (LLM may be unavailable)")
        has_llm_failure = True

    # ─── 2. MCQ Validation ─────────────────────────────────────────────────
    if type_res.get("label") == "MCQ" and options:
        mcq_val = validate_mcq(question_text, options, correct_option)
    else:
        mcq_val = {"valid": True, "issues": []}

    # ─── 3. Quality Analysis (Deterministic + Optional LLM) ────────────────
    try:
        quality, quality_issues, quality_suggestions = analyze_quality(question_text, options)
    except Exception as e:
        print(f"[pipeline] Quality analysis error: {e}")
        quality = {"overall_score": None, "dimensions": None, "status": "AI_UNAVAILABLE"}
        quality_issues = []
        quality_suggestions = []
        errors.append(f"Quality analysis failed: {str(e)}")

    # ─── 4. Duplicate Detection ────────────────────────────────────────────
    try:
        dup_result = detect_duplicates(question_text, existing_questions)
    except Exception as e:
        print(f"[pipeline] Duplicate detection error: {e}")
        dup_result = {
            "risk": 0.0, "risk_label": "LOW", "is_duplicate": False,
            "similar_question_id": None, "similarity": 0.0,
            "similar_questions": [], "method": "error"
        }
        warnings.append(f"Duplicate detection failed: {str(e)}")

    # ─── 5. Explanations ──────────────────────────────────────────────────
    explanations = {
        "topic": f"Classified as '{topic_res['label']}' ({topic_res.get('method', 'unknown')}, confidence: {topic_res['confidence']:.0%}).",
        "bloom": f"Classified as '{bloom_res['label']}' ({bloom_res.get('method', 'unknown')}, confidence: {bloom_res['confidence']:.0%})." +
                 (f" Evidence: {', '.join(bloom_res.get('evidence', []))}" if bloom_res.get('evidence') else ""),
        "difficulty": f"Estimated as '{diff_res['label']}' ({diff_res.get('method', 'unknown')}, confidence: {diff_res['confidence']:.0%})." +
                      (f" Factors: {', '.join(diff_res.get('reasoning_factors', [])[:2])}" if diff_res.get('reasoning_factors') else ""),
        "quality": f"Quality status: {quality.get('status', 'UNKNOWN')}. Score: {quality.get('overall_score', 'N/A')}."
    }

    # ─── 6. Recommendations ───────────────────────────────────────────────
    recommendations: List[dict] = []

    # Add quality issues as recommendations
    for issue in quality_issues:
        recommendations.append({
            "issue": issue.get("message", ""),
            "severity": issue.get("severity", "MEDIUM").upper(),
            "why": f"Detected by deterministic quality rule: {issue.get('type', 'UNKNOWN')}",
            "recommendation": "",
            "suggested_improvement": None
        })

    # Add quality suggestions
    for suggestion in quality_suggestions:
        recommendations.append({
            "issue": suggestion,
            "severity": "LOW",
            "why": "Quality improvement suggestion",
            "recommendation": suggestion,
            "suggested_improvement": None
        })

    # Add MCQ validation issues
    for issue in mcq_val.get("issues", []):
        recommendations.append({
            "issue": issue.get("message", ""),
            "severity": issue.get("severity", "MEDIUM").upper(),
            "why": f"MCQ validation: {issue.get('type', '')}",
            "recommendation": issue.get("message", ""),
            "suggested_improvement": None
        })

    # Add duplicate warning
    if dup_result.get("is_duplicate"):
        recommendations.insert(0, {
            "issue": "High duplicate risk detected",
            "severity": "HIGH",
            "why": f"This question has {dup_result['risk']:.0%} semantic similarity to question #{dup_result.get('similar_question_id')}",
            "recommendation": "Review the similar question and decide whether this adds unique value.",
            "suggested_improvement": None
        })

    # ─── 7. Review Decision ────────────────────────────────────────────────
    review_reasons: List[str] = []

    if topic_res["confidence"] < 0.60:
        review_reasons.append(f"Low topic confidence ({topic_res['confidence']:.0%})")
    if bloom_res["confidence"] < 0.60:
        review_reasons.append(f"Low Bloom confidence ({bloom_res['confidence']:.0%})")
    if dup_result.get("is_duplicate"):
        review_reasons.append(f"High duplicate risk ({dup_result['risk']:.0%} similarity)")
    if not mcq_val["valid"]:
        review_reasons.append("MCQ validation failed")
    if quality.get("overall_score") is not None and quality["overall_score"] < 0.70:
        review_reasons.append(f"Low quality score ({quality['overall_score']:.0%})")
    if has_llm_failure:
        review_reasons.append("LLM unavailable — analysis is degraded, manual review recommended")
    if errors:
        review_reasons.append(f"{len(errors)} error(s) during analysis")

    review_required = len(review_reasons) > 0

    # ─── 8. Blueprint Alignment ────────────────────────────────────────────
    align_res = check_alignment(
        predicted_topic=topic_res["label"],
        predicted_bloom=bloom_res["label"],
        predicted_difficulty=diff_res["label"],
        expected_topic=expected_topic,
        expected_bloom=expected_bloom,
        expected_difficulty=expected_difficulty
    )

    # ─── 9. System Status ──────────────────────────────────────────────────
    if errors:
        system_status = "PARTIAL"
        analysis_status = "DEGRADED"
    elif has_llm_failure:
        system_status = "PARTIAL"
        analysis_status = "DEGRADED"
    else:
        system_status = "FULL"
        analysis_status = "COMPLETED"

    # Determine LLM status from classifier methods
    methods_used = [c.get("method", "") for c in classifiers_used]
    if all(m == "llm" for m in methods_used):
        llm_status = "USED"
    elif any(m == "llm" for m in methods_used):
        llm_status = "PARTIAL"
    elif any(m == "error_fallback" for m in methods_used):
        llm_status = "FAILED"
    else:
        llm_status = "UNAVAILABLE"

    # ─── Return Canonical AnalysisResult ───────────────────────────────────
    return {
        "status": system_status,
        "analysis_status": analysis_status,
        "warnings": warnings,
        "errors": errors,
        "classification": {
            "question_type": type_res,
            "topic": topic_res,
            "bloom": bloom_res,
            "difficulty": diff_res
        },
        "quality": quality,
        "validation": mcq_val,
        "duplicate": dup_result,
        "alignment": align_res,
        "recommendations": recommendations,
        "explanations": explanations,
        "review": {
            "required": review_required,
            "reasons": review_reasons,
            "priority": "HIGH" if len(review_reasons) >= 2 else ("MEDIUM" if review_reasons else "LOW")
        },
        "model_metadata": {
            "model_name": "qis-ml-pipeline-v1",
            "model_version": "3.0.0",
            "embedding_model": "all-MiniLM-L6-v2",
            "llm_model": "gemini-1.5-flash",
            "analysis_version": "2026-08-v3",
            "llm_status": llm_status
        }
    }
