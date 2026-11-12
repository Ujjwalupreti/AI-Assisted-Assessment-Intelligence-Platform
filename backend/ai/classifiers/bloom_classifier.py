"""
Bloom Taxonomy Classifier.

Architecture:
    Primary: LLM (Gemini) via structured prompt
    Fallback: Synonym-group heuristic (stemmed keyword families)

Returns canonical BloomResult schema: {label, confidence, evidence, method}
"""
import re
from ai.core.llm_client import generate_json
from ai.core.schemas import BloomResult

# Synonym groups — each entry contains word stems and phrases that map to a Bloom level.
# Order matters: higher cognitive levels checked first to avoid under-classification.
BLOOM_SYNONYM_GROUPS = {
    "Create": [
        "design", "construct", "develop", "formulate", "compose", "create",
        "produce", "generate", "propose", "plan", "build", "devise",
        "invent", "author", "synthesize", "assemble", "write a program",
        "implement a solution", "draft", "model"
    ],
    "Evaluate": [
        "evaluate", "judge", "critique", "justify", "assess", "recommend",
        "appraise", "defend", "argue", "choose the best", "determine the validity",
        "prioritize", "rate", "rank", "support", "validate", "criticize",
        "decide", "select the most appropriate"
    ],
    "Analyze": [
        "analyze", "compare", "contrast", "differentiate", "examine",
        "inspect", "investigate", "breakdown", "classify", "distinguish",
        "categorize", "deconstruct", "dissect", "organize", "relate",
        "separate", "attribute", "deduce", "infer from", "what is the relationship",
        "how does .* differ", "what are the differences"
    ],
    "Apply": [
        "apply", "use", "implement", "solve", "calculate", "compute",
        "demonstrate", "employ", "execute", "operate", "find the value",
        "determine", "show how", "carry out", "perform", "utilize",
        "sketch", "draw", "simulate", "practice", "modify"
    ],
    "Understand": [
        "explain", "describe", "summarize", "interpret", "paraphrase",
        "discuss", "outline", "illustrate", "elaborate", "express",
        "give an example", "in your own words", "what does .* mean",
        "restate", "translate", "predict", "estimate", "extend",
        "generalize", "convert"
    ],
    "Remember": [
        "define", "list", "recall", "state", "name", "identify",
        "recognize", "match", "select", "what is", "which of the following",
        "who", "when", "where", "true or false", "enumerate",
        "label", "memorize", "repeat", "reproduce", "quote"
    ],
}

VALID_BLOOM_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]


BLOOM_LLM_THRESHOLD = 0.65

def classify_bloom(question_text: str) -> BloomResult:
    """
    Classify Bloom's Taxonomy level.
    Primary: Synonym-group heuristic (DETERMINISTIC).
    Fallback: LLM only if confidence is low.
    """
    # 1. Deterministic heuristic
    result = _heuristic_bloom(question_text)
    
    # 2. LLM fallback if confidence is below threshold
    if result["confidence"] < BLOOM_LLM_THRESHOLD:
        llm = generate_json
        try:
            prompt = f"""
You are an expert in Bloom's Taxonomy for educational assessment.
Classify the cognitive level of this exam question.

Bloom's levels (lowest to highest):
Remember, Understand, Apply, Analyze, Evaluate, Create

Question: {question_text}

Return ONLY valid JSON:
{{"label": "<level>", "confidence": <0.0-1.0>, "evidence": ["<keyword or reasoning>"]}}
"""
            llm_result = llm(prompt)
            if llm_result and "label" in llm_result:
                label = llm_result["label"]
                if label not in VALID_BLOOM_LEVELS:
                    label = "Remember"
                # If LLM confidence is better, use it
                llm_conf = float(llm_result.get("confidence", 0.7))
                if llm_conf > result["confidence"]:
                    return {
                        "label": label,
                        "confidence": llm_conf,
                        "evidence": llm_result.get("evidence", []),
                        "method": "LLM"
                    }
        except Exception as e:
            print(f"[bloom_classifier] LLM fallback error: {e}")
            
    # Return heuristic if LLM fails or heuristic was sufficient
    return result

def _heuristic_bloom(text: str) -> BloomResult:
    """
    Synonym-group heuristic. Evaluates from highest cognitive level down.
    """
    text_lower = text.lower()

    for level in ["Create", "Evaluate", "Analyze", "Apply", "Understand", "Remember"]:
        keywords = BLOOM_SYNONYM_GROUPS.get(level, [])
        matches = []
        for kw in keywords:
            try:
                if re.search(r'\b' + kw.replace(".*", ".*") + r'\b', text_lower) if ".*" in kw else kw in text_lower:
                    matches.append(kw)
            except re.error:
                if kw in text_lower:
                    matches.append(kw)

        if matches:
            # We scale heuristic confidence to be a bit higher so it can pass threshold if strong
            # Base confidence 0.5 + 0.1 per match, max 0.85
            confidence = min(0.85, 0.50 + len(matches) * 0.10)
            return {
                "label": level,
                "confidence": confidence,
                "evidence": matches[:3],
                "method": "DETERMINISTIC"
            }

    return {
        "label": "Remember",
        "confidence": 0.3, # Low confidence, will trigger LLM fallback
        "evidence": ["No clear Bloom keywords found"],
        "method": "DETERMINISTIC"
    }

