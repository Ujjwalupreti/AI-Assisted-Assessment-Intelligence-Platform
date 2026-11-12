"""
Blueprint Service.

Provides structured access to exam blueprints and gap analysis.
"""
import json
from typing import Dict, Optional, List
from models import Exam, Question, AssessmentBlueprint
from database import get_db_session

def get_blueprint(exam_id: int) -> Optional[dict]:
    with get_db_session() as db:
        # Try AssessmentBlueprint table first
        ab = db.query(AssessmentBlueprint).filter_by(exam_id=exam_id).order_by(
            AssessmentBlueprint.created_at.desc()
        ).first()
        
        if ab and ab.blueprint_json:
            try:
                return json.loads(ab.blueprint_json)
            except json.JSONDecodeError:
                pass

        # Fallback to Exam.blueprint_json
        exam = db.get(Exam, exam_id)
        if exam and exam.blueprint_json:
            try:
                return json.loads(exam.blueprint_json)
            except json.JSONDecodeError:
                pass

    return None


def get_actual_distribution(exam_id: int) -> dict:
    """
    Calculate the actual distribution of questions in an exam.
    
    Returns:
    {
        "bloom_distribution": {"Remember": 5, "Apply": 3, ...},
        "difficulty_distribution": {"Easy": 4, "Medium": 3, ...},
        "topic_distribution": {"Data Structures": 2, ...},
        "total_questions": 10,
        "total_marks": 10.0
    }
    Values are COUNTS (not percentages).
    """
    with get_db_session() as db:
        questions = db.query(Question).filter(Question.exam_id == exam_id, Question.is_archived == False).all()
        
        bloom_counts = {}
        difficulty_counts = {}
        topic_counts = {}
        total_marks = 0.0
        
        for q in questions:
            b = q.bloom_level or "Unknown"
            bloom_counts[b] = bloom_counts.get(b, 0) + 1
            
            d = q.difficulty or "Unknown"
            difficulty_counts[d] = difficulty_counts.get(d, 0) + 1
            
            t = q.topic or "Unknown"
            topic_counts[t] = topic_counts.get(t, 0) + 1
            
            total_marks += (q.max_marks or 1.0)
            
        return {
            "bloom_distribution": bloom_counts,
            "difficulty_distribution": difficulty_counts,
            "topic_distribution": topic_counts,
            "total_questions": len(questions),
            "total_marks": round(total_marks, 2)
        }
    
    for q in questions:
        bloom = q.bloom_level or "Uncategorized"
        diff = q.difficulty or "Uncategorized"
        topic = q.topic or "Uncategorized"
        
        bloom_counts[bloom] = bloom_counts.get(bloom, 0) + 1
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        total_marks += (q.max_marks or 1.0)
    
    return {
        "bloom_distribution": bloom_counts,
        "difficulty_distribution": difficulty_counts,
        "topic_distribution": topic_counts,
        "total_questions": len(questions),
        "total_marks": total_marks
    }


def compute_gap_analysis(exam_id: int) -> dict:
    """
    Compare actual exam composition against blueprint.
    
    Returns:
    {
        "has_blueprint": bool,
        "gaps": {
            "bloom": [{"category": "Analyze", "target": 10, "actual": 3, "deficit": 7}],
            "difficulty": [...],
            "topic": [...]
        },
        "excess": {
            "bloom": [{"category": "Remember", "target": 5, "actual": 12, "surplus": 7}],
            ...
        },
        "total_deficit": int,
        "total_surplus": int
    }
    """
    blueprint = get_blueprint(exam_id)
    actual = get_actual_distribution(exam_id)
    
    if not blueprint:
        return {
            "has_blueprint": False,
            "gaps": {"bloom": [], "difficulty": [], "topic": []},
            "excess": {"bloom": [], "difficulty": [], "topic": []},
            "total_deficit": 0,
            "total_surplus": 0
        }
    
    total_q = actual["total_questions"]
    bp_total = blueprint.get("total_questions", total_q) or total_q
    
    gaps = {"bloom": [], "difficulty": [], "topic": []}
    excess = {"bloom": [], "difficulty": [], "topic": []}
    
    # The true total deficit/surplus is the difference in overall question count
    total_deficit = max(0, bp_total - total_q)
    total_surplus = max(0, total_q - bp_total)
    
    for dim_key in ["bloom_distribution", "difficulty_distribution", "topic_distribution"]:
        short_key = dim_key.replace("_distribution", "")
        bp_dist = blueprint.get(dim_key, {})
        actual_dist = actual.get(dim_key, {})
        
        for category, bp_pct in bp_dist.items():
            # Convert blueprint percentage to target count
            target_count = round((bp_pct / 100.0) * bp_total) if bp_pct > 1 else round(bp_pct * bp_total)
            actual_count = actual_dist.get(category, 0)
            
            if actual_count < target_count:
                deficit = target_count - actual_count
                gaps[short_key].append({
                    "category": category,
                    "target": target_count,
                    "actual": actual_count,
                    "deficit": deficit
                })
            elif actual_count > target_count:
                surplus = actual_count - target_count
                excess[short_key].append({
                    "category": category,
                    "target": target_count,
                    "actual": actual_count,
                    "surplus": surplus
                })
    
    return {
        "has_blueprint": True,
        "gaps": gaps,
        "excess": excess,
        "total_deficit": total_deficit,
        "total_surplus": total_surplus
    }
