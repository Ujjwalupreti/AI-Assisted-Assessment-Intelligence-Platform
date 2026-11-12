from typing import List, Dict, Optional
import re
from ai.core.schemas import MCQValidationResult, QualityIssue

def normalize_option(text: str) -> str:
    if not text: return ""
    text = text.strip().lower()
    # Remove leading numbering if accidentally included (e.g., "A) ", "1. ")
    text = re.sub(r'^[a-d1-4][\.\)]\s*', '', text)
    # Remove trailing periods
    text = re.sub(r'\.$', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def validate_mcq(question_text: str, options: Dict[str, str], correct_option: Optional[str] = None) -> MCQValidationResult:
    issues: List[QualityIssue] = []
    valid = True

    # Check for empty options
    empty_count = 0
    option_values = []
    for key, val in options.items():
        if not val or val.strip() == "":
            empty_count += 1
            issues.append({"severity": "high", "type": "empty_option", "message": f"Option {key} is empty.", "option": key})
            valid = False
        else:
            option_values.append(normalize_option(val))

    if empty_count > 0:
        return {"valid": valid, "issues": issues}

    # Check for duplicate options
    if len(set(option_values)) != len(option_values):
        issues.append({"severity": "high", "type": "duplicate_options", "message": "Duplicate options detected.", "option": None})
        valid = False
        
    # Heuristic for "All of the above"
    for key, val in options.items():
        if val and "all of the above" in val.lower():
            issues.append({"severity": "medium", "type": "all_of_the_above", "message": "Consider avoiding 'All of the above'.", "option": key})
            
    # Check correct option exists
    if correct_option and correct_option not in options:
        issues.append({"severity": "high", "type": "invalid_correct_option", "message": f"Correct option {correct_option} is not one of the provided options.", "option": None})
        valid = False

    return {"valid": valid, "issues": issues}
