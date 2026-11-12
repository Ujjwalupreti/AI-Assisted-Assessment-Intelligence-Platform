from typing import Optional, Dict
from .schemas import AlignmentResult

def check_alignment(predicted_topic: str, predicted_bloom: str, predicted_difficulty: str,
                    expected_topic: Optional[str] = None, expected_bloom: Optional[str] = None, expected_difficulty: Optional[str] = None) -> AlignmentResult:
    """
    Compares predicted metadata against expected metadata.
    Returns MATCH or MISMATCH for each dimension.
    """
    
    result: AlignmentResult = {
        "topic": "MATCH",
        "bloom": "MATCH",
        "difficulty": "MATCH"
    }
    
    if expected_topic and expected_topic.strip().lower() != predicted_topic.strip().lower():
        result["topic"] = "MISMATCH"
        
    if expected_bloom and expected_bloom.strip().lower() != predicted_bloom.strip().lower():
        result["bloom"] = "MISMATCH"
        
    if expected_difficulty and expected_difficulty.strip().lower() != predicted_difficulty.strip().lower():
        result["difficulty"] = "MISMATCH"
        
    return result
