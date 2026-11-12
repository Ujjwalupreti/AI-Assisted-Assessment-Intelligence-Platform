"""
Quality Analyzer.

Architecture:
    Layer 1: Deterministic quality rules (always runs, no LLM needed)
    Layer 2: LLM semantic analysis (optional, enhances with nuanced feedback)

Returns canonical QualityResult schema: {overall_score, dimensions, status}
Also returns quality_issues and quality_suggestions lists for recommendations.
"""
import re
from typing import List, Dict, Optional, Tuple
from .llm_client import generate_json
from .schemas import QualityResult


def analyze_quality(question_text: str, options: dict = None) -> Tuple[QualityResult, List[dict], List[str]]:
    """
    Analyze question quality.
    
    Returns:
        (quality_result, issues_list, suggestions_list)
        
    quality_result conforms to QualityResult schema.
    issues_list: list of {type, severity, message}
    suggestions_list: list of string suggestions
    """
    # ── Layer 1: Deterministic Rules (always runs) ──
    det_issues, det_suggestions, det_dimensions = _deterministic_rules(question_text, options)
    
    # Calculate deterministic score from dimensions
    dim_values = list(det_dimensions.values())
    det_score = sum(dim_values) / len(dim_values) if dim_values else 0.5

    # ── Layer 2: LLM Enhancement (optional) ──
    try:
        options_str = ""
        if options:
            filled = {k: v for k, v in options.items() if v and v.strip()}
            if filled:
                options_str = "\n".join(f"  {k}: {v}" for k, v in filled.items())

        prompt = f"""
Analyze the quality of this exam question. Evaluate grammar, clarity, ambiguity, completeness, and specificity.

Question: {question_text}
{"Options:" + chr(10) + options_str if options_str else ""}

Return ONLY valid JSON:
{{
    "overall_score": <float 0.0-1.0>,
    "dimensions": {{
        "clarity": <float 0.0-1.0>,
        "completeness": <float 0.0-1.0>,
        "specificity": <float 0.0-1.0>,
        "grammar": <float 0.0-1.0>,
        "ambiguity": <float 0.0-1.0, higher=less ambiguous=better>
    }},
    "status": "GOOD" | "WARNING" | "POOR",
    "issues": [
        {{"type": "<AMBIGUITY|GRAMMAR|INCOMPLETE|POOR_DISTRACTOR|TOO_SHORT|TOO_LONG>", "severity": "<low|medium|high>", "message": "<specific issue>"}}
    ],
    "suggestions": ["<specific improvement suggestion>"]
}}
"""
        result = generate_json(prompt)
        if result and "overall_score" in result:
            # Merge LLM issues with deterministic issues
            llm_issues = result.get("issues", [])
            llm_suggestions = result.get("suggestions", [])
            
            all_issues = det_issues + [i for i in llm_issues if isinstance(i, dict)]
            all_suggestions = det_suggestions + [s for s in llm_suggestions if isinstance(s, str)]
            
            dimensions = result.get("dimensions", det_dimensions)
            score = float(result.get("overall_score", det_score))
            
            status = "GOOD"
            if score < 0.5:
                status = "POOR"
            elif score < 0.75:
                status = "WARNING"
            
            quality: QualityResult = {
                "overall_score": score,
                "dimensions": dimensions,
                "status": result.get("status", status)
            }
            return quality, all_issues, all_suggestions

    except Exception as e:
        print(f"[quality_analyzer] LLM error: {e}")

    # ── Fallback: deterministic only ──
    status = "GOOD"
    if det_score < 0.5:
        status = "POOR"
    elif det_score < 0.75:
        status = "WARNING"
    
    # If we have issues but no LLM, flag as degraded via score adjustment
    if det_issues:
        status = "WARNING"

    quality: QualityResult = {
        "overall_score": round(det_score, 3),
        "dimensions": det_dimensions,
        "status": status
    }
    return quality, det_issues, det_suggestions


def _deterministic_rules(text: str, options: dict = None) -> Tuple[List[dict], List[str], dict]:
    """
    Deterministic quality rules. Always produce useful feedback without LLM.
    
    Returns:
        (issues, suggestions, dimensions_dict)
    """
    issues = []
    suggestions = []
    
    # Start with baseline dimension scores
    clarity = 0.8
    completeness = 0.8
    specificity = 0.7
    grammar = 0.9
    ambiguity = 0.8  # higher = less ambiguous = better

    # ── Rule 1: Question too short ──
    word_count = len(text.split())
    if word_count < 5:
        issues.append({"type": "TOO_SHORT", "severity": "high", "message": f"Question is very short ({word_count} words). May lack context."})
        suggestions.append("Expand the question with additional context or specifics.")
        clarity -= 0.3
        completeness -= 0.4
    elif word_count < 10:
        issues.append({"type": "TOO_SHORT", "severity": "medium", "message": f"Question is short ({word_count} words). Consider adding context."})
        suggestions.append("Consider adding more context to reduce ambiguity.")
        completeness -= 0.2

    # ── Rule 2: Question too long ──
    if word_count > 100:
        issues.append({"type": "TOO_LONG", "severity": "medium", "message": f"Question is very long ({word_count} words). May confuse students."})
        suggestions.append("Consider breaking into sub-questions or simplifying the phrasing.")
        clarity -= 0.2

    # ── Rule 3: Missing question mark ──
    stripped = text.strip()
    if not stripped.endswith("?") and not stripped.endswith(":") and not stripped.endswith("."):
        issues.append({"type": "GRAMMAR", "severity": "low", "message": "Question does not end with a question mark, colon, or period."})
        suggestions.append("End the question with proper punctuation (? or :).")
        grammar -= 0.15

    # ── Rule 4: All caps ──
    if text == text.upper() and len(text) > 10:
        issues.append({"type": "GRAMMAR", "severity": "medium", "message": "Question is entirely in UPPERCASE."})
        suggestions.append("Use proper sentence case for readability.")
        grammar -= 0.2

    # ── Rule 5: Ambiguous pronouns ──
    ambiguous_words = ["it", "this", "that", "they", "these", "those"]
    text_lower = text.lower()
    found_ambiguous = [w for w in ambiguous_words if re.search(r'\b' + w + r'\b', text_lower)]
    if len(found_ambiguous) >= 2:
        issues.append({"type": "AMBIGUITY", "severity": "low", "message": f"Multiple ambiguous pronouns detected: {', '.join(found_ambiguous)}. Consider using specific nouns."})
        ambiguity -= 0.15

    # ── Rule 6: Negation without emphasis ──
    negation_patterns = [r'\bnot\b', r'\bexcept\b', r'\bwithout\b', r'\bnone\b']
    neg_found = [p for p in negation_patterns if re.search(p, text_lower)]
    if neg_found:
        # Check if negation is emphasized (bold, caps, underline)
        has_emphasis = any(w in text for w in ["NOT", "EXCEPT", "NONE"])
        if not has_emphasis:
            issues.append({"type": "AMBIGUITY", "severity": "medium", "message": "Negation words detected without emphasis. Students may miss them."})
            suggestions.append("Emphasize negation words (e.g., use UPPERCASE: 'Which is NOT...')")
            ambiguity -= 0.1

    # ── Rule 7: MCQ option analysis ──
    if options:
        filled_count = 0
        filled_values = []
        for k, v in options.items():
            if v and v.strip():
                filled_count += 1
                filled_values.append(v.strip().lower())
        
        # Missing options
        if filled_count < 4:
            issues.append({"type": "MISSING_OPTIONS", "severity": "high", "message": f"Only {filled_count} out of 4 options are provided."})
            suggestions.append("Provide all 4 options for a standard MCQ.")
            completeness -= 0.3
            
        # Duplicate options
        if len(set(filled_values)) < filled_count:
            issues.append({"type": "DUPLICATE_OPTIONS", "severity": "high", "message": "Multiple options have the exact same text."})
            suggestions.append("Ensure all multiple-choice options are unique.")
            clarity -= 0.4
            
        if filled_count > 0:
            option_lengths = [len(v.split()) for v in filled_values]
            max_len = max(option_lengths)
            min_len = min(option_lengths)
            
            # Drastically unequal option lengths
            if max_len > 0 and min_len > 0 and max_len / min_len > 4:
                issues.append({"type": "POOR_DISTRACTOR", "severity": "medium", "message": f"Option lengths vary widely ({min_len}–{max_len} words). Longest option may be the obvious answer."})
                suggestions.append("Balance option lengths so no single answer stands out by length.")
                specificity -= 0.15

    # Clamp dimensions
    dimensions = {
        "clarity": max(0.0, min(1.0, round(clarity, 3))),
        "completeness": max(0.0, min(1.0, round(completeness, 3))),
        "specificity": max(0.0, min(1.0, round(specificity, 3))),
        "grammar": max(0.0, min(1.0, round(grammar, 3))),
        "ambiguity": max(0.0, min(1.0, round(ambiguity, 3)))
    }

    return issues, suggestions, dimensions
