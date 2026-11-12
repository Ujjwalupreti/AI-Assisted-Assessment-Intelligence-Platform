"""
Difficulty Estimator.

Architecture:
    Primary: LLM (Gemini) via structured prompt
    Fallback: Multi-signal heuristic (text length, jargon, options complexity, Bloom prior)

Returns canonical DifficultyResult schema: {label, confidence, reasoning_factors, method}
"""
from ai.core.llm_client import generate_json
from ai.core.schemas import DifficultyResult


DIFFICULTY_LLM_THRESHOLD = 0.65

def estimate_difficulty(question_text: str, bloom_level: str = None, options: dict = None) -> DifficultyResult:
    """
    Estimate difficulty of a question.
    Primary: Multi-signal heuristic (DETERMINISTIC/HYBRID).
    Fallback: LLM only if confidence is low.
    """
    # 1. Deterministic heuristic
    result = _heuristic_difficulty(question_text, bloom_level, options)
    
    # 2. LLM fallback if confidence is below threshold
    if result["confidence"] < DIFFICULTY_LLM_THRESHOLD:
        try:
            options_str = ""
            if options:
                filled = {k: v for k, v in options.items() if v and v.strip()}
                if filled:
                    options_str = "\n".join(f"  {k}: {v}" for k, v in filled.items())

            prompt = f"""
You are an expert exam designer. Estimate the difficulty of this question.

Consider:
- Prerequisite knowledge required
- Reasoning steps involved
- Abstraction level
- Calculation complexity
- Problem complexity
- Bloom's level context: {bloom_level or 'Unknown'}

Question: {question_text}
{"Options:" + chr(10) + options_str if options_str else ""}

Difficulty options: Easy, Medium, Hard

Return ONLY valid JSON:
{{"label": "<difficulty>", "confidence": <0.0-1.0>, "reasoning_factors": ["<factor>"]}}
"""
            llm_result = generate_json(prompt)
            if llm_result and "label" in llm_result:
                label = llm_result.get("label", "Medium")
                if "level" in llm_result and "label" not in llm_result:
                    label = llm_result["level"]
                if label not in ["Easy", "Medium", "Hard"]:
                    label = "Medium"
                
                llm_conf = float(llm_result.get("confidence", 0.65))
                if llm_conf > result["confidence"]:
                    return {
                        "label": label,
                        "confidence": llm_conf,
                        "reasoning_factors": llm_result.get("reasoning_factors", []),
                        "method": "LLM"
                    }
        except Exception as e:
            print(f"[difficulty_estimator] LLM fallback error: {e}")

    # Return heuristic if LLM fails or heuristic was sufficient
    return result

def _heuristic_difficulty(text: str, bloom_level: str = None, options: dict = None) -> DifficultyResult:
    """
    Multi-signal heuristic. Does NOT simply equate Bloom == Difficulty.
    """
    factors = []
    score = 0
    confidence = 0.50 # Base confidence

    # Signal 1: Question length
    word_count = len(text.split())
    if word_count > 60:
        score += 2
        factors.append(f"Long question ({word_count} words)")
        confidence += 0.05
    elif word_count > 30:
        score += 1
        factors.append(f"Moderate length")

    # Signal 2: Technical jargon
    jargon_words = [
        "algorithm", "complexity", "proof", "theorem", "optimize",
        "concurrency", "distributed", "pipeline", "asymptotic",
        "recurrence", "amortized", "polynomial", "nondeterministic"
    ]
    jargon_count = sum(1 for w in jargon_words if w in text.lower())
    if jargon_count >= 3:
        score += 2
        factors.append(f"{jargon_count} technical terms")
        confidence += 0.1
    elif jargon_count >= 1:
        score += 1

    # Signal 3: Multi-step reasoning indicators
    multi_step_words = ["calculate", "derive", "prove", "demonstrate", "compare and", "analyze", "step by step"]
    multi_matches = [w for w in multi_step_words if w in text.lower()]
    if multi_matches:
        score += 1
        factors.append("Multi-step reasoning")
        confidence += 0.1

    # Signal 4: Option complexity (if MCQ)
    if options:
        filled_options = [v for v in options.values() if v and v.strip()]
        avg_option_len = sum(len(o.split()) for o in filled_options) / max(len(filled_options), 1)
        if avg_option_len > 12:
            score += 1
            factors.append("Complex options")
            confidence += 0.05

    # Signal 5: Bloom as a weak prior
    if bloom_level in ["Create", "Evaluate"]:
        score += 1
        factors.append(f"Bloom {bloom_level}")
        confidence += 0.05
    elif bloom_level == "Remember":
        score -= 1
        factors.append("Bloom Remember")
        confidence += 0.05

    if score >= 4:
        label = "Hard"
    elif score >= 1:
        label = "Medium"
    else:
        label = "Easy"

    if not factors:
        factors.append("Default heuristic")
        confidence = 0.30 # Low confidence, trigger LLM

    return {
        "label": label,
        "confidence": min(0.85, confidence),
        "reasoning_factors": factors[:3],
        "method": "HYBRID" # It combines text metrics and Bloom
    }
