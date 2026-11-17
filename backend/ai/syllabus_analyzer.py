"""
Syllabus & JD Intelligence Engine for QIS.
Provides automated curriculum analysis, topic extraction, weightage calculation,
and assessment question generation grounded in syllabus documents.
Ensures clean, concise 2-4 word topic tags and professional academic questions.
"""

import re
import math
import random
from typing import Dict, List, Any, Optional
from ai.core.llm_client import generate_json

BLOOM_TAXONOMY_LEVELS = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]

def _clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def _clean_topic_name(name: str) -> str:
    """
    Cleans extracted topic name into a short, concise academic tag (2-4 words, max 30 chars).
    Never outputs full sentences, run-on phrases, or introductory fluff.
    """
    if not name:
        return "Core Concepts"
    # Remove leading numbering or labels like 'Unit 1:', 'Module 2 -', 'Chapter 3.', '1. ', '• '
    name = re.sub(r'^[•\*\-\d\.\)]+\s*', '', name).strip()
    name = re.sub(r'^(?:unit|module|chapter|part|section|week)\s*(?:[0-9]+|[ivx]+)?\s*[:\-\.]?\s*', '', name, flags=re.IGNORECASE).strip()
    # Strip after punctuation that begins a sentence or details (. ; : ( [ - – —)
    name = re.split(r'[\.\;\:\(\)\[\]\–\—]', name)[0].strip()
    # Strip inline clauses like "including ...", "such as ...", "e.g. ..."
    name = re.split(r'\b(?:including|such as|like|e\.g\.)\b', name, flags=re.IGNORECASE)[0].strip()
    # Strip phrases like 'Introduction to', 'Overview of', 'Basics of', 'We will learn about'
    name = re.sub(r'^(?:introduction\s+to|overview\s+of|fundamentals\s+of|basics\s+of|principles\s+of|study\s+of|we\s+will\s+learn\s+about)\s+', '', name, flags=re.IGNORECASE).strip()
    if ',' in name:
        name = name.split(',')[0].strip()
    # Split words
    words = [w for w in name.split() if w.strip()]
    if len(words) > 4:
        words = words[:4]
    # Drop trailing conjunctions, prepositions, or filler words
    while words and words[-1].lower() in ('and', '&', 'or', 'with', 'for', 'in', 'of', 'to', 'the', 'a', 'an', 'including', 'such', 'as', 'like', 'etc'):
        words.pop()
    name = ' '.join(words).title().strip()
    name = re.sub(r'^[^\w]+|[^\w]+$', '', name).strip()
    return name if len(name) >= 3 else "Core Concepts"

def _clean_concept(concept: str) -> str:
    """Clean sub-concept keywords to 1-3 words."""
    if not concept:
        return "Core Principles"
    concept = re.split(r'[\.\;\:\(\)\[\]]', concept)[0].strip()
    concept = re.sub(r'^(?:e\.g\.|such as|including|like|we will learn about)\s*', '', concept, flags=re.IGNORECASE).strip()
    words = [w for w in concept.split() if w.strip()]
    if len(words) > 3:
        words = words[:3]
    while words and words[-1].lower() in ('and', '&', 'or', 'with', 'for', 'in', 'of', 'to', 'the'):
        words.pop()
    res = ' '.join(words).title().strip()
    return res if len(res) >= 2 else "Core Principles"

def _deterministic_topic_fallback(content_text: str, course_name: str = "") -> Dict[str, Any]:
    """
    Robust fallback NLP parser that reliably extracts structured modules and topics
    from syllabus text even if offline or if external LLM is unreachable.
    """
    lines = [line.strip() for line in content_text.splitlines() if line.strip()]
    
    # 1. Regex to find Unit/Module/Chapter headers
    header_pattern = re.compile(
        r'^(?:unit|module|chapter|part|section|week)\s*([0-9ivx]+|\b[a-z]\b)?\s*[:\-\.]?\s*(.*)$',
        re.IGNORECASE
    )
    
    extracted_modules = []
    current_module = None
    
    for line in lines:
        match = header_pattern.match(line)
        if match:
            mod_num = match.group(1) or str(len(extracted_modules) + 1)
            raw_title = match.group(2)
            cleaned_title = _clean_topic_name(raw_title)
            if len(cleaned_title) >= 3:
                current_module = {
                    "module": f"Module {mod_num}",
                    "name": cleaned_title,
                    "concepts": []
                }
                extracted_modules.append(current_module)
        elif current_module and len(current_module["concepts"]) < 6:
            # Subtopics or bullet lines
            sub_clean = re.sub(r'^[•\-\*\d\.\)]+\s*', '', line).strip()
            clean_c = _clean_concept(sub_clean)
            if clean_c and clean_c not in current_module["concepts"]:
                current_module["concepts"].append(clean_c)

    # 2. If no formal headers were found, perform heuristic sentence/paragraph segmentation
    if len(extracted_modules) < 2:
        extracted_modules = []
        chunks = [c.strip() for c in re.split(r'\n\s*\n', content_text) if len(c.strip()) > 30]
        if not chunks:
            chunks = [content_text[:300], content_text[300:600], content_text[600:900]]
            chunks = [c for c in chunks if c.strip()]
            
        for i, chunk in enumerate(chunks[:5]):
            first_line = chunk.splitlines()[0].strip()
            topic_name = _clean_topic_name(first_line)
            if not topic_name or topic_name == "Core Concepts":
                topic_name = f"Module {i+1} Foundations"
            words = [w for w in re.findall(r'[a-zA-Z]{4,}', chunk) if w.lower() not in ('this', 'that', 'with', 'from', 'have', 'more', 'about', 'will', 'learn')]
            concepts = [_clean_concept(w) for w in dict.fromkeys(words[:4])]
            extracted_modules.append({
                "module": f"Unit {i+1}",
                "name": topic_name,
                "concepts": concepts or ["Core Principles", "Operations"]
            })

    # Ensure at least 3 topics
    if len(extracted_modules) < 3:
        default_names = ["Foundational Principles", "Core Operations", "Advanced Applications"]
        for j in range(len(extracted_modules), 3):
            extracted_modules.append({
                "module": f"Unit {j+1}",
                "name": default_names[j],
                "concepts": ["Theory", "Implementation", "Analysis"]
            })

    # Cap at 6 topics
    selected_modules = extracted_modules[:6]
    n_topics = len(selected_modules)
    
    # 3. Calculate balanced weightages summing to 100%
    base_weight = math.floor(100 / n_topics)
    remainder = 100 - (base_weight * n_topics)
    
    topics = []
    bloom_sequence = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    diff_sequence = ["Easy", "Medium", "Medium", "Hard", "Medium", "Hard"]
    
    for idx, mod in enumerate(selected_modules):
        weight = base_weight + (1 if idx < remainder else 0)
        q_count = max(1, round((weight / 100.0) * 10))
        bloom = bloom_sequence[idx % len(bloom_sequence)]
        diff = diff_sequence[idx % len(diff_sequence)]
        
        topics.append({
            "id": f"topic_{idx + 1}",
            "name": _clean_topic_name(mod["name"]),
            "module": mod["module"],
            "importance": "Critical" if weight >= 25 else "High",
            "description": f"Core assessment topic covering foundational knowledge and practical competence in {mod['name']}.",
            "key_concepts": [_clean_concept(c) for c in (mod["concepts"] or ["Core Principles", "Analysis"])],
            "weight_percentage": weight,
            "suggested_questions": q_count,
            "recommended_bloom": bloom,
            "recommended_difficulty": diff
        })

    return {
        "course_summary": f"Curriculum analysis for {course_name or 'Course Syllabus'}. Extracted {len(topics)} prioritized modules aligned with Bloom's Taxonomy standards.",
        "topics": topics,
        "difficulty_distribution": {"Easy": 30, "Medium": 50, "Hard": 20},
        "bloom_distribution": {"Remember": 25, "Understand": 30, "Apply": 25, "Analyze": 20}
    }


def analyze_syllabus_text(content_text: str, title: str = "", course_name: str = "") -> Dict[str, Any]:
    """
    Main syllabus analyzer entrypoint. Uses Google Gemini LLM when available,
    falling back seamlessly to high-precision deterministic educational parser.
    """
    if not content_text or len(content_text.strip()) < 10:
        raise ValueError("Syllabus content is too short for meaningful analysis.")

    prompt = f"""
    You are an expert Educational Psychometrician and University Assessment Intelligence Engine.
    Analyze the following course syllabus, curriculum outline, or Job Description (JD):

    Course Name: {course_name or 'General Course'}
    Document Title: {title or 'Syllabus'}

    --- SYLLABUS CONTENT ---
    {content_text[:4000]}
    ------------------------

    CRITICAL INSTRUCTIONS FOR TOPICS:
    1. Extract 3 to 6 distinct, high-impact assessment topics/modules.
    2. 'name' MUST BE A SHORT, CRISP ACADEMIC TITLE OF 2 TO 4 WORDS ONLY (e.g. "Data Structures", "Binary Search Trees", "Dynamic Programming", "Graph Algorithms", "Finite Automata").
       DO NOT USE FULL SENTENCES, DO NOT USE RUN-ON DESCRIPTIONS, DO NOT INCLUDE VERBS LIKE "We will learn".
    3. 'key_concepts' MUST each be a concise 1-3 word keyword (e.g. "Arrays", "Recursion", "Stack Frames").
    4. Recommend an optimal weightage percentage for each topic based on depth and importance.
       CRITICAL REQUIREMENT: The sum of all 'weight_percentage' values MUST equal exactly 100.
    5. Suggest recommended Bloom's taxonomy cognitive level and difficulty.

    Return ONLY a JSON object matching this schema:
    {{
        "course_summary": "Two sentence overview of curriculum scope and assessment focus.",
        "topics": [
            {{
                "id": "topic_1",
                "name": "Short Topic Title",
                "module": "Module 1",
                "importance": "Critical",
                "description": "Essential topic covering core principles and problem solving.",
                "key_concepts": ["concept1", "concept2", "concept3"],
                "weight_percentage": 25,
                "suggested_questions": 3,
                "recommended_bloom": "Apply",
                "recommended_difficulty": "Medium"
            }}
        ],
        "difficulty_distribution": {{"Easy": 30, "Medium": 50, "Hard": 20}},
        "bloom_distribution": {{"Remember": 25, "Understand": 30, "Apply": 25, "Analyze": 20}}
    }}
    """

    try:
        data = generate_json(prompt, temperature=0.2)
        if data and isinstance(data, dict) and "topics" in data and len(data["topics"]) >= 2:
            # Clean and sanitize topic names
            cleaned_topics = []
            raw_sum = sum(int(t.get("weight_percentage", 0)) for t in data["topics"])
            acc = 0
            for i, t in enumerate(data["topics"]):
                t["name"] = _clean_topic_name(t.get("name", f"Topic {i+1}"))
                t["key_concepts"] = [_clean_concept(c) for c in t.get("key_concepts", []) if c]
                if raw_sum > 0:
                    if i == len(data["topics"]) - 1:
                        w = 100 - acc
                    else:
                        w = round((int(t.get("weight_percentage", 20)) / raw_sum) * 100)
                        acc += w
                    t["weight_percentage"] = max(5, w)
                cleaned_topics.append(t)
            data["topics"] = cleaned_topics
            return data
    except Exception as e:
        print(f"[SyllabusAnalyzer] LLM analysis unavailable or failed: {e}. Using deterministic parser.")

    return _deterministic_topic_fallback(content_text, course_name)


def generate_syllabus_questions(
    topics: List[Dict[str, Any]],
    total_count: int,
    exam_type: str = "Mixed",
    syllabus_context: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generates candidate assessment questions grounded in syllabus topics.
    Supports Objective MCQs and Subjective questions (Math, Derivations, Automata, Theory).
    """
    total_count = max(1, total_count)
    generated = []

    n_topics = len(topics)
    if n_topics == 0:
        return []

    quotas = {}
    remaining = total_count
    for t in topics:
        pct = float(t.get("weight_percentage", 100 / n_topics))
        c = math.floor((pct / 100.0) * total_count)
        quotas[t["name"]] = max(1, c)
        remaining -= quotas[t["name"]]

    # Adjust rounding remainder
    if remaining != 0:
        first_topic = topics[0]["name"]
        quotas[first_topic] = max(1, quotas[first_topic] + remaining)

    q_counter = 1

    for t in topics:
        t_name = _clean_topic_name(t.get("name", "Core Principles"))
        t_quota = quotas.get(t["name"], 1)
        t_bloom = t.get("recommended_bloom", "Apply")
        t_diff = t.get("recommended_difficulty", "Medium")
        t_concepts = [_clean_concept(c) for c in t.get("key_concepts", [])] or [t_name]

        for q_idx in range(t_quota):
            if exam_type == "Objective":
                is_sub = False
            elif exam_type == "Subjective":
                is_sub = True
            else:
                is_sub = (q_counter % 2 == 0)

            concept_focus = t_concepts[q_idx % len(t_concepts)] if t_concepts else t_name

            if not is_sub:
                q_obj = _generate_objective_question(t_name, concept_focus, t_bloom, t_diff)
            else:
                q_obj = _generate_subjective_question(t_name, concept_focus, t_bloom, t_diff, q_counter)

            generated.append(q_obj)
            q_counter += 1
            if len(generated) >= total_count:
                break
        if len(generated) >= total_count:
            break

    return generated


def _generate_objective_question(topic: str, concept: str, bloom: str, difficulty: str) -> Dict[str, Any]:
    """Create a structured, curriculum-grounded MCQ with natural, clear academic wording."""
    clean_topic = _clean_topic_name(topic)
    clean_concept = _clean_concept(concept)

    templates = [
        {
            "text": f"In {clean_topic}, which of the following best describes the operational purpose of {clean_concept}?",
            "opt_a": f"It provides a deterministic approach for managing {clean_concept} with optimal complexity.",
            "opt_b": f"It serves solely as an auxiliary cache layer without direct functional impact.",
            "opt_c": f"It triggers an unconstrained asynchronous routine that bypasses state validation.",
            "opt_d": f"It executes a brute-force linear search across all elements.",
            "correct": "A",
            "marks": 1.0,
            "explanation": f"In {clean_topic}, {clean_concept} ensures deterministic execution and optimal computational efficiency."
        },
        {
            "text": f"When analyzing runtime performance in {clean_topic}, what is the primary advantage of employing {clean_concept}?",
            "opt_a": f"Minimizing auxiliary memory overhead while preventing redundant recalculations.",
            "opt_b": f"Guaranteeing sub-linear or logarithmic operations across diverse input distributions.",
            "opt_c": f"Eliminating boundary and invariant verification during execution.",
            "opt_d": f"Doubling the recursion depth without any stack allocation overhead.",
            "correct": "A",
            "marks": 1.0,
            "explanation": f"A key theoretical advantage of {clean_concept} in {clean_topic} is optimizing time and memory overhead."
        },
        {
            "text": f"Which of the following statements regarding {clean_concept} in {clean_topic} is technically correct?",
            "opt_a": f"It preserves structural invariants across state transitions during execution.",
            "opt_b": f"It always requires quadratic time complexity regardless of input size.",
            "opt_c": f"It can only be applied to static read-only data structures.",
            "opt_d": f"It ignores memory boundary constraints to maximize throughput.",
            "correct": "A",
            "marks": 1.0,
            "explanation": f"Preserving system invariants across state transitions is fundamental to {clean_concept} in {clean_topic}."
        },
        {
            "text": f"In the context of {clean_topic}, what failure condition arises if {clean_concept} is improperly configured?",
            "opt_a": f"Violation of invariant properties leading to undefined or non-deterministic state.",
            "opt_b": f"Automatic promotion from logarithmic to constant-time execution.",
            "opt_c": f"Unconditional allocation of zero-byte stack frames.",
            "opt_d": f"Strict adherence to FIFO ordering in all execution scenarios.",
            "correct": "A",
            "marks": 1.0,
            "explanation": f"Improper configuration of {clean_concept} in {clean_topic} leads to invariant corruption and non-deterministic behavior."
        }
    ]

    selected = random.choice(templates)
    return {
        "text": selected["text"],
        "option_a": selected["opt_a"],
        "option_b": selected["opt_b"],
        "option_c": selected["opt_c"],
        "option_d": selected["opt_d"],
        "correct_option": selected["correct"],
        "topic": clean_topic,
        "difficulty": difficulty,
        "bloom_level": bloom,
        "is_subjective": False,
        "question_type": "MCQ",
        "max_marks": selected["marks"],
        "reference_answer": f"Option {selected['correct']}: {selected['explanation']}",
        "rubric": "1.0 mark for correct option selection. 0.0 marks for incorrect."
    }


def _generate_subjective_question(topic: str, concept: str, bloom: str, difficulty: str, index: int) -> Dict[str, Any]:
    """Create a structured Subjective question (Problem, Derivation, Automata, or Theory)."""
    clean_topic = _clean_topic_name(topic)
    clean_concept = _clean_concept(concept)
    topic_lower = clean_topic.lower()
    
    if "automata" in topic_lower or "language" in topic_lower or "dfa" in topic_lower or "grammar" in topic_lower:
        return {
            "text": f"Design a formal Finite Automaton (DFA/NFA) for {clean_concept} over the alphabet Σ = {{0, 1}}. Specify the 5-tuple (Q, Σ, δ, q₀, F) and draw or tabulate the state transition function.",
            "option_a": None, "option_b": None, "option_c": None, "option_d": None,
            "correct_option": None,
            "topic": clean_topic,
            "difficulty": difficulty,
            "bloom_level": "Create" if bloom in ("Create", "Evaluate") else "Apply",
            "is_subjective": True,
            "question_type": "DFA_NFA",
            "max_marks": 3.0,
            "reference_answer": f"State diagram with initial state q0, accepting states F, and deterministic transitions handling {clean_concept} correctly.",
            "rubric": "1.0 mark for correct state set Q and initial state q0; 1.0 mark for transition delta consistency; 1.0 mark for correct accepting states F."
        }
    elif "math" in topic_lower or "calculus" in topic_lower or "complexity" in topic_lower or index % 3 == 0:
        return {
            "text": f"Provide a rigorous mathematical derivation and complexity analysis for {clean_concept} in {clean_topic}. Express the recurrence relation and solve it using standard step-by-step techniques.",
            "option_a": None, "option_b": None, "option_c": None, "option_d": None,
            "correct_option": None,
            "topic": clean_topic,
            "difficulty": difficulty,
            "bloom_level": "Analyze",
            "is_subjective": True,
            "question_type": "MATH_EQUATION",
            "max_marks": 2.5,
            "reference_answer": f"Derivation: T(n) = aT(n/b) + f(n). Step-by-step substitution demonstrating upper and lower asymptotic bounds for {clean_concept}.",
            "rubric": "1.0 mark for recurrence formulation; 1.0 mark for algebraic step execution; 0.5 marks for correct asymptotic notation."
        }
    else:
        return {
            "text": f"Explain the core theoretical principles and architectural design of {clean_concept} within {clean_topic}. Discuss the trade-offs, edge cases, and runtime implications compared to alternative approaches.",
            "option_a": None, "option_b": None, "option_c": None, "option_d": None,
            "correct_option": None,
            "topic": clean_topic,
            "difficulty": difficulty,
            "bloom_level": bloom or "Understand",
            "is_subjective": True,
            "question_type": "SHORT_ANSWER",
            "max_marks": 2.0,
            "reference_answer": f"A comprehensive response detailing definition of {clean_concept}, operating mechanism in {clean_topic}, trade-off analysis, and mitigation of edge cases.",
            "rubric": "1.0 mark for conceptual clarity & definition; 0.5 marks for trade-off evaluation; 0.5 marks for real-world application."
        }
