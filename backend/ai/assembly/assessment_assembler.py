import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Question
from sqlalchemy import select

def _calculate_quotas(distribution: dict, total: int) -> dict:
    """Converts percentage distribution (e.g., {'Easy': 30, 'Medium': 70}) to exact counts based on total."""
    quotas = {}
    remaining = total
    # Sort to ensure consistent rounding
    for k, pct in sorted(distribution.items(), key=lambda x: -x[1]):
        count = math.floor((pct / 100.0) * total)
        if count > remaining:
            count = remaining
        quotas[k] = count
        remaining -= count
        
    # Distribute remainder to highest pct
    if remaining > 0 and quotas:
        highest = max(quotas, key=lambda k: distribution.get(k, 0))
        quotas[highest] += remaining
        
    return quotas

def assemble_assessment(
    db: Session,
    topics: dict, # e.g. {"Algorithms": 50, "DBMS": 50}
    difficulty_distribution: dict, # e.g. {"Easy": 30, "Medium": 50, "Hard": 20}
    question_count: int,
    exam_type: str = "Objective",
    bloom_distribution: dict = None
) -> dict:
    if not bloom_distribution:
        # Auto-derive Bloom based on exam type and difficulty
        if exam_type == "Objective":
            bloom_distribution = {"Remember": 35, "Understand": 30, "Apply": 20, "Analyze": 10, "Evaluate": 3, "Create": 2}
        else:
            bloom_distribution = {"Remember": 10, "Understand": 20, "Apply": 30, "Analyze": 20, "Evaluate": 10, "Create": 10}

    # 1. Calculate target quotas
    topic_quotas = _calculate_quotas(topics, question_count)
    diff_quotas = _calculate_quotas(difficulty_distribution, question_count)
    bloom_quotas = _calculate_quotas(bloom_distribution, question_count)
    
    # 2. Retrieve eligible questions from Bank (exam_id is null or active questions)
    # For MVP, we'll just grab all active questions that match the topics
    target_topics = list(topics.keys())
    # Note: SQLite IN clause
    query = select(Question).filter(Question.status == 'ACTIVE', Question.topic.in_(target_topics))
    if exam_type == "Objective":
        query = query.filter(Question.question_type == 'MCQ')
    elif exam_type == "Subjective":
        query = query.filter(Question.question_type != 'MCQ')
        
    available_records = db.execute(query).scalars().all()
    
    # Convert to dicts for easy manipulation
    pool = []
    for q in available_records:
        pool.append({
            "id": q.id,
            "text": q.text,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "bloom_level": q.bloom_level,
            "quality_score": q.ai_quality_score or 0.5,
            "duplicate_status": q.duplicate_status or 'SAFE',
            "source": q.source,
            "options": {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d}
        })
        
    selected_questions = []
    used_ids = set()
    warnings = []
    
    # 3. Greedy Selection
    for topic, quota in topic_quotas.items():
        for _ in range(quota):
            best_q = None
            best_score = -1
            
            for q in pool:
                if q["id"] in used_ids:
                    continue
                if q["topic"] != topic:
                    continue
                    
                # Calculate scores
                diff_match = 1.0 if diff_quotas.get(q["difficulty"], 0) > 0 else 0.0
                bloom_match = 1.0 if bloom_quotas.get(q["bloom_level"], 0) > 0 else 0.0
                q_score = q["quality_score"]
                dup_safety = 1.0 if q["duplicate_status"] == 'SAFE' else (0.5 if q["duplicate_status"] == 'FLAGGED' else 0.0)
                
                # Weighting logic
                score = (diff_match * 0.30) + (bloom_match * 0.30) + (q_score * 0.30) + (dup_safety * 0.10)
                
                if score > best_score:
                    best_score = score
                    best_q = q
                    
            if best_q:
                selected_questions.append(best_q)
                used_ids.add(best_q["id"])
                # Deduct quotas
                if best_q["difficulty"] in diff_quotas:
                    diff_quotas[best_q["difficulty"]] -= 1
                if best_q["bloom_level"] in bloom_quotas:
                    bloom_quotas[best_q["bloom_level"]] -= 1
            else:
                warnings.append(f"Not enough questions for topic '{topic}'. Missing {quota - sum(1 for q in selected_questions if q['topic'] == topic)}.")
                break # Move to next topic if we ran out of questions for this topic
                
    # 4. Validate Blueprint & Compile Gaps
    actual_topic = {}
    actual_diff = {}
    actual_bloom = {}
    
    for q in selected_questions:
        actual_topic[q["topic"]] = actual_topic.get(q["topic"], 0) + 1
        actual_diff[q["difficulty"]] = actual_diff.get(q["difficulty"], 0) + 1
        actual_bloom[q["bloom_level"]] = actual_bloom.get(q["bloom_level"], 0) + 1
        
    gaps = []
    if len(selected_questions) < question_count:
        gaps.append(f"Requested {question_count} questions but could only find {len(selected_questions)}.")
        
    for k, v in diff_quotas.items():
        if v > 0:
            gaps.append(f"Missing {v} '{k}' difficulty questions.")
            
    for k, v in bloom_quotas.items():
        if v > 0:
            gaps.append(f"Missing {v} '{k}' level questions.")
            
    return {
        "selected_questions": selected_questions,
        "actual_distribution": {
            "topic": actual_topic,
            "difficulty": actual_diff,
            "bloom": actual_bloom
        },
        "gaps": gaps,
        "warnings": warnings
    }
