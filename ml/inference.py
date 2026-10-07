"""
ML Inference Wrapper for QIS.

Architecture:
  Primary: LLM (Gemini) via structured prompt
  Fallback: Keyword/rule-based heuristics when LLM is unavailable

All methods return canonical schema fields (label, confidence, method).
Never return simulated static values.
"""
import re
from typing import Dict, List, Optional

# ─── Controlled Topic Taxonomy ──────────────────────────────────────────────
CS_TOPICS = [
    "Data Structures", "Algorithms", "DBMS", "Operating Systems",
    "Computer Networks", "OOP", "Software Engineering",
    "Computer Architecture", "Compiler Design",
    "Artificial Intelligence", "Machine Learning",
    "Web Development", "Cyber Security", "Cloud Computing",
    "Distributed Systems", "Programming", "General CS"
]

# Keyword maps for heuristic fallback
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "Data Structures": ["array", "linked list", "stack", "queue", "tree", "heap", "graph", "trie", "hash table", "binary tree", "bst"],
    "Algorithms": ["sorting", "searching", "binary search", "time complexity", "big o", "dynamic programming", "greedy", "recursion", "backtracking", "divide and conquer"],
    "DBMS": ["sql", "database", "normalization", "transaction", "acid", "join", "index", "query", "relation", "tuple", "foreign key", "primary key"],
    "Operating Systems": ["process", "thread", "semaphore", "deadlock", "scheduler", "memory management", "paging", "segmentation", "kernel", "context switch"],
    "Computer Networks": ["tcp", "ip", "http", "dns", "osi", "subnet", "routing", "protocol", "bandwidth", "latency", "socket", "network layer"],
    "OOP": ["class", "object", "inheritance", "polymorphism", "encapsulation", "abstraction", "interface", "method overriding", "constructor"],
    "Software Engineering": ["sdlc", "agile", "scrum", "requirement", "testing", "sprint", "design pattern", "uml", "software lifecycle"],
    "Computer Architecture": ["cpu", "cache", "pipeline", "instruction set", "alu", "register", "memory hierarchy", "mips", "risc", "cisc"],
    "Compiler Design": ["lexer", "parser", "token", "grammar", "syntax tree", "ast", "semantic analysis", "code generation", "symbol table"],
    "Artificial Intelligence": ["search algorithm", "heuristic", "a*", "bfs", "dfs", "expert system", "knowledge base", "inference engine"],
    "Machine Learning": ["training", "model", "accuracy", "overfitting", "regression", "classification", "neural network", "gradient descent", "feature"],
    "Web Development": ["html", "css", "javascript", "api", "rest", "json", "frontend", "backend", "http request", "dom"],
    "Cyber Security": ["encryption", "decryption", "firewall", "vulnerability", "authentication", "authorization", "xss", "sql injection", "cipher"],
    "Cloud Computing": ["cloud", "aws", "azure", "saas", "paas", "iaas", "virtual machine", "container", "kubernetes", "docker"],
    "Distributed Systems": ["consistency", "availability", "partition", "cap theorem", "replication", "consensus", "load balancing"],
    "Programming": ["variable", "function", "loop", "condition", "syntax", "runtime error", "compile", "pointer", "memory leak"],
}

BLOOM_KEYWORDS: Dict[str, List[str]] = {
    "Create": ["design", "construct", "develop", "formulate", "compose", "create", "produce", "generate", "propose", "plan", "build"],
    "Evaluate": ["evaluate", "judge", "critique", "justify", "assess", "recommend", "appraise", "defend", "argue", "choose"],
    "Analyze": ["analyze", "compare", "contrast", "differentiate", "examine", "inspect", "investigate", "breakdown", "classify", "distinguish"],
    "Apply": ["apply", "use", "implement", "solve", "calculate", "compute", "demonstrate", "employ", "execute", "operate", "find"],
    "Understand": ["explain", "describe", "summarize", "interpret", "paraphrase", "classify", "discuss", "outline", "illustrate"],
    "Remember": ["define", "list", "recall", "state", "name", "identify", "recognize", "match", "select", "what is", "which"],
}


class QISModelInference:
    def __init__(self):
        self._llm = None
        self._llm_checked = False

    def _get_llm(self):
        """Lazily load LLM client."""
        if not self._llm_checked:
            self._llm_checked = True
            try:
                from ai.services.llm_client import generate_json
                self._llm = generate_json
            except Exception:
                self._llm = None
        return self._llm

    def predict_topic(self, text: str) -> dict:
        """Classify topic using LLM primary → keyword heuristic fallback."""
        llm = self._get_llm()
        if llm:
            prompt = f"""
You are a computer science educator. Classify the topic of this exam question.

ALLOWED TOPICS (pick the best match):
{", ".join(CS_TOPICS)}

Question: {text}

Return ONLY valid JSON:
{{"label": "<topic>", "confidence": <0.0-1.0>, "alternatives": [{{"label": "<topic2>", "confidence": <float>}}]}}
"""
            result = llm(prompt)
            if result and "label" in result:
                label = result["label"]
                # Validate it's in our taxonomy
                if label not in CS_TOPICS:
                    label = "General CS"
                return {
                    "label": label,
                    "confidence": float(result.get("confidence", 0.7)),
                    "alternatives": result.get("alternatives", []),
                    "method": "llm"
                }

        # Heuristic fallback
        return self._heuristic_topic(text)

    def _heuristic_topic(self, text: str) -> dict:
        text_lower = text.lower()
        scores: Dict[str, int] = {}
        for topic, keywords in TOPIC_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[topic] = count

        if scores:
            sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            best_topic, best_count = sorted_topics[0]
            # Confidence is a rough score: more keyword matches = more confidence, capped at 0.65
            confidence = min(0.65, 0.3 + best_count * 0.1)
            alternatives = [
                {"label": t, "confidence": round(min(0.5, 0.2 + c * 0.1), 2)}
                for t, c in sorted_topics[1:3]
            ]
            return {"label": best_topic, "confidence": confidence, "alternatives": alternatives, "method": "heuristic_fallback"}

        return {"label": "General CS", "confidence": 0.2, "alternatives": [], "method": "heuristic_fallback"}

    def predict_bloom(self, text: str) -> dict:
        """Classify Bloom's level using LLM primary → keyword fallback."""
        llm = self._get_llm()
        if llm:
            prompt = f"""
You are an expert in Bloom's Taxonomy for education.

Classify this exam question's cognitive level.
Bloom's levels: Remember, Understand, Apply, Analyze, Evaluate, Create

Question: {text}

Return ONLY valid JSON:
{{"label": "<level>", "confidence": <0.0-1.0>, "evidence": ["<keyword or reason>"]}}
"""
            result = llm(prompt)
            if result and "label" in result:
                label = result["label"]
                if label not in ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]:
                    label = "Remember"
                return {
                    "label": label,
                    "confidence": float(result.get("confidence", 0.7)),
                    "evidence": result.get("evidence", []),
                    "method": "llm"
                }

        return self._heuristic_bloom(text)

    def _heuristic_bloom(self, text: str) -> dict:
        text_lower = text.lower()
        # Evaluate from highest to lowest cognitive level
        for level in ["Create", "Evaluate", "Analyze", "Apply", "Understand", "Remember"]:
            keywords = BLOOM_KEYWORDS.get(level, [])
            matches = [kw for kw in keywords if kw in text_lower]
            if matches:
                return {
                    "label": level,
                    "confidence": 0.4,
                    "evidence": matches[:3],
                    "method": "heuristic_fallback"
                }
        return {"label": "Remember", "confidence": 0.3, "evidence": [], "method": "heuristic_fallback"}

    def predict_difficulty(self, text: str, bloom_label: str = None) -> dict:
        """
        Estimate difficulty. Does NOT simply equate Bloom == Difficulty.
        Considers: question length, technical jargon, multi-step reasoning.
        """
        llm = self._get_llm()
        if llm:
            prompt = f"""
You are an expert exam designer. Estimate the difficulty of this question.

Consider:
- Prerequisite knowledge required
- Reasoning steps involved
- Abstraction level
- Calculation complexity
- Problem complexity
- Bloom's level context: {bloom_label or 'Unknown'}

Question: {text}

Difficulty options: Easy, Medium, Hard

Return ONLY valid JSON:
{{"label": "<difficulty>", "confidence": <0.0-1.0>, "reasoning_factors": ["<factor>"]}}
"""
            result = llm(prompt)
            if result and "label" in result:
                label = result["label"]
                if label not in ["Easy", "Medium", "Hard"]:
                    label = "Medium"
                return {
                    "label": label,
                    "confidence": float(result.get("confidence", 0.65)),
                    "reasoning_factors": result.get("reasoning_factors", []),
                    "method": "llm"
                }

        return self._heuristic_difficulty(text, bloom_label)

    def _heuristic_difficulty(self, text: str, bloom_label: str = None) -> dict:
        """
        Heuristic: uses multiple signals, NOT just Bloom level.
        This is explicitly a fallback — confidence is kept low.
        """
        factors = []
        score = 0

        # Signal 1: Question length (longer often = more complex)
        word_count = len(text.split())
        if word_count > 50:
            score += 2
            factors.append("Long question text implies multiple concepts")
        elif word_count > 25:
            score += 1

        # Signal 2: Technical jargon count
        jargon_words = ["algorithm", "complexity", "proof", "theorem", "optimize", "concurrency", "distributed", "pipeline"]
        jargon_count = sum(1 for w in jargon_words if w in text.lower())
        if jargon_count >= 3:
            score += 2
            factors.append(f"{jargon_count} technical terms detected")
        elif jargon_count >= 1:
            score += 1

        # Signal 3: Multi-step indicators
        multi_step_words = ["calculate", "derive", "prove", "demonstrate", "compare and", "analyze"]
        if any(w in text.lower() for w in multi_step_words):
            score += 1
            factors.append("Multi-step reasoning indicator detected")

        # Bloom as a weak prior, not the sole determiner
        if bloom_label in ["Create", "Evaluate"]:
            score += 1
            factors.append(f"High-order Bloom level ({bloom_label}) suggests complexity")
        elif bloom_label in ["Remember"]:
            score -= 1
            factors.append(f"Low-order Bloom level ({bloom_label}) suggests simplicity")

        if score >= 4:
            label = "Hard"
        elif score >= 1:
            label = "Medium"
        else:
            label = "Easy"

        if not factors:
            factors.append("Rule-based heuristic fallback")

        return {"label": label, "confidence": 0.35, "reasoning_factors": factors, "method": "heuristic_fallback"}

    def predict_question_type(self, text: str, options: dict = None) -> dict:
        """
        Detect question type using structural evidence first, then LLM.
        Structural checks are strong signals - MCQ with 4 options is near-certain.
        """
        # Structural checks FIRST (strongest signal)
        if options:
            filled_options = [v for v in options.values() if v and v.strip()]
            if len(filled_options) >= 3:
                return {"label": "MCQ", "confidence": 0.97, "method": "structural"}

        text_lower = text.lower()
        # True/False structural detection
        if re.search(r'\b(true or false|true/false|state whether)\b', text_lower):
            return {"label": "TRUE_FALSE", "confidence": 0.95, "method": "structural"}

        # Fill in the blank
        if "_____" in text or "____" in text or "___" in text:
            return {"label": "FILL_IN_THE_BLANK", "confidence": 0.95, "method": "structural"}

        # Numerical
        num_keywords = ["calculate", "compute", "find the value", "what is the value", "how many", "how much"]
        if any(kw in text_lower for kw in num_keywords):
            return {"label": "NUMERICAL", "confidence": 0.7, "method": "structural"}

        # Coding
        code_keywords = ["write a program", "implement", "write code", "write an algorithm", "write a function"]
        if any(kw in text_lower for kw in code_keywords):
            return {"label": "CODING", "confidence": 0.85, "method": "structural"}

        # LLM for ambiguous cases
        llm = self._get_llm()
        if llm:
            prompt = f"""
Classify this exam question type.
Types: MCQ, TRUE_FALSE, SHORT_ANSWER, LONG_ANSWER, NUMERICAL, CODING, FILL_IN_THE_BLANK

Question: {text}

Return ONLY valid JSON: {{"label": "<type>", "confidence": <0.0-1.0>}}
"""
            result = llm(prompt)
            if result and "label" in result:
                valid_types = ["MCQ", "TRUE_FALSE", "SHORT_ANSWER", "LONG_ANSWER", "NUMERICAL", "CODING", "FILL_IN_THE_BLANK"]
                label = result["label"] if result["label"] in valid_types else "SHORT_ANSWER"
                return {"label": label, "confidence": float(result.get("confidence", 0.6)), "method": "llm"}

        return {"label": "SHORT_ANSWER", "confidence": 0.3, "method": "heuristic_fallback"}


# Global singleton instance
qis_inference = QISModelInference()
