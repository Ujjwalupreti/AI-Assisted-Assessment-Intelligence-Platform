"""
Topic Classifier.

Architecture:
    Primary: LLM (Gemini) via structured prompt
    Fallback: Keyword-based heuristic using CS_TOPICS taxonomy

Returns canonical TopicResult schema: {label, confidence, alternatives, method}
"""
from ai.core.llm_client import generate_json
from ai.core.schemas import TopicResult

# Controlled taxonomy — must match ml/inference.py CS_TOPICS
CS_TOPICS = [
    "Data Structures", "Algorithms", "DBMS", "Operating Systems",
    "Computer Networks", "OOP", "Software Engineering",
    "Computer Architecture", "Compiler Design",
    "Artificial Intelligence", "Machine Learning",
    "Web Development", "Cyber Security", "Cloud Computing",
    "Distributed Systems", "Programming", "General CS"
]

TOPIC_KEYWORDS = {
    "Data Structures": ["array", "linked list", "stack", "queue", "tree", "heap", "graph", "trie", "hash table", "binary tree", "bst", "avl", "red-black", "b-tree", "priority queue", "deque"],
    "Algorithms": ["sorting", "searching", "binary search", "time complexity", "big o", "dynamic programming", "greedy", "recursion", "backtracking", "divide and conquer", "algorithm", "asymptotic", "brute force", "memoization"],
    "DBMS": ["sql", "database", "normalization", "transaction", "acid", "join", "index", "query", "relation", "tuple", "foreign key", "primary key", "schema", "er diagram", "nosql", "relational"],
    "Operating Systems": ["process", "thread", "semaphore", "deadlock", "scheduler", "memory management", "paging", "segmentation", "kernel", "context switch", "virtual memory", "file system", "mutex", "ipc"],
    "Computer Networks": ["tcp", "ip", "http", "dns", "osi", "subnet", "routing", "protocol", "bandwidth", "latency", "socket", "network layer", "firewall", "packet", "ethernet", "udp"],
    "OOP": ["class", "object", "inheritance", "polymorphism", "encapsulation", "abstraction", "interface", "method overriding", "constructor", "destructor", "overloading", "composition", "aggregation"],
    "Software Engineering": ["sdlc", "agile", "scrum", "requirement", "testing", "sprint", "design pattern", "uml", "software lifecycle", "waterfall", "use case", "functional requirement", "non-functional"],
    "Computer Architecture": ["cpu", "cache", "pipeline", "instruction set", "alu", "register", "memory hierarchy", "mips", "risc", "cisc", "von neumann", "harvard architecture", "bus"],
    "Compiler Design": ["lexer", "parser", "token", "grammar", "syntax tree", "ast", "semantic analysis", "code generation", "symbol table", "regular expression", "finite automata", "cfg"],
    "Artificial Intelligence": ["search algorithm", "heuristic", "a*", "bfs", "dfs", "expert system", "knowledge base", "inference engine", "planning", "agent", "minimax", "constraint satisfaction"],
    "Machine Learning": ["training", "model", "accuracy", "overfitting", "regression", "classification", "neural network", "gradient descent", "feature", "supervised", "unsupervised", "reinforcement", "deep learning", "cnn", "rnn"],
    "Web Development": ["html", "css", "javascript", "api", "rest", "json", "frontend", "backend", "http request", "dom", "react", "node", "express", "flask", "django"],
    "Cyber Security": ["encryption", "decryption", "firewall", "vulnerability", "authentication", "authorization", "xss", "sql injection", "cipher", "cryptography", "ssl", "tls", "penetration testing"],
    "Cloud Computing": ["cloud", "aws", "azure", "saas", "paas", "iaas", "virtual machine", "container", "kubernetes", "docker", "serverless", "microservice"],
    "Distributed Systems": ["consistency", "availability", "partition", "cap theorem", "replication", "consensus", "load balancing", "fault tolerance", "distributed"],
    "Programming": ["variable", "function", "loop", "condition", "syntax", "runtime error", "compile", "pointer", "memory leak", "data type", "string", "integer", "boolean", "recursion"],
}


def classify_topic(question_text: str) -> TopicResult:
    """
    Classify topic of a question.
    Primary: LLM. Fallback: keyword heuristic.
    """
    try:
        prompt = f"""
You are a computer science educator. Classify the topic of this exam question.

ALLOWED TOPICS (pick the best match):
{", ".join(CS_TOPICS)}

Question: {question_text}

Return ONLY valid JSON:
{{"label": "<topic>", "confidence": <0.0-1.0>, "alternatives": [{{"label": "<topic2>", "confidence": <float>}}]}}
"""
        result = generate_json(prompt)
        if result and "label" in result:
            label = result.get("label", "General CS")
            # Also handle old "topic" key for backward compat with older LLM responses
            if "topic" in result and "label" not in result:
                label = result["topic"]
            if label not in CS_TOPICS:
                label = "General CS"
            return {
                "label": label,
                "confidence": float(result.get("confidence", 0.7)),
                "alternatives": result.get("alternatives", []),
                "method": "llm"
            }
    except Exception as e:
        print(f"[topic_classifier] LLM error: {e}")

    return _heuristic_topic(question_text)


def _heuristic_topic(text: str) -> TopicResult:
    """
    Keyword-based topic classification.
    Scores each topic by number of keyword hits.
    """
    text_lower = text.lower()
    scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[topic] = count

    if scores:
        sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_topic, best_count = sorted_topics[0]
        confidence = min(0.55, 0.25 + best_count * 0.08)
        alternatives = [
            {"label": t, "confidence": round(min(0.4, 0.15 + c * 0.08), 2)}
            for t, c in sorted_topics[1:3]
        ]
        return {
            "label": best_topic,
            "confidence": confidence,
            "alternatives": alternatives,
            "method": "heuristic_fallback"
        }

    return {
        "label": "General CS",
        "confidence": 0.15,
        "alternatives": [],
        "method": "heuristic_fallback"
    }
