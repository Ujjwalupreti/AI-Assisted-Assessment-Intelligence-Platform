"""
Question Recommendation Engine.

Analyzes an exam against its blueprint, identifies gaps and excess,
searches the Question Bank for suitable candidates, ranks them,
and returns actionable ADD / REMOVE / REPLACE / REVIEW recommendations.

Configurable ranking weights.
"""
import json
from database import get_db_session
from typing import List, Dict, Optional
from models import Question, QuestionAiAnalysis


# ─── Configurable Weights for Candidate Ranking ─────────────────────────
DEFAULT_WEIGHTS = {
    "blueprint_match": 0.30,   # How well the candidate fills a specific gap
    "topic_match": 0.20,       # Exact topic match with the gap
    "bloom_match": 0.15,       # Exact Bloom level match
    "difficulty_match": 0.15,  # Exact difficulty match
    "quality_score": 0.10,     # ai_quality_score from QIS
    "duplicate_risk": 0.05,    # Lower risk = better
    "diversity": 0.05,         # Prefer questions from different sources/exams
}


def generate_recommendations(exam_id: int, weights: dict = None) -> dict:
    """
    Generate recommendations for an exam.
    
    Returns:
    {
        "exam_id": int,
        "has_blueprint": bool,
        "gap_summary": str,
        "recommendations": [
            {
                "action": "ADD" | "REMOVE" | "REPLACE" | "REVIEW",
                "reason": str,
                "priority": "HIGH" | "MEDIUM" | "LOW",
                "gap": {"bloom": "Analyze", "difficulty": "Hard", "topic": "Data Structures"},
                "candidates": [{"question_id": int, "text_preview": str, "score": float, "exam_id": int}]
            }
        ]
    }
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    from services.blueprint_service import compute_gap_analysis, get_actual_distribution

    gap_analysis = compute_gap_analysis(exam_id)
    actual = get_actual_distribution(exam_id)
    recommendations = []

    if not gap_analysis["has_blueprint"]:
        # No blueprint — provide generic recommendations
        recommendations.append({
            "action": "REVIEW",
            "reason": "No assessment blueprint defined. Define a blueprint to get targeted recommendations.",
            "priority": "MEDIUM",
            "gap": {},
            "candidates": []
        })

        # Still check for quality issues
        low_quality = _find_low_quality_questions(exam_id)
        for lq in low_quality:
            recommendations.append({
                "action": "REVIEW",
                "reason": f"Question #{lq['id']} has low quality score ({lq['quality']:.2f}). Consider improving or replacing.",
                "priority": "MEDIUM",
                "gap": {},
                "candidates": []
            })

        return {
            "exam_id": exam_id,
            "has_blueprint": False,
            "gap_summary": "No blueprint defined.",
            "recommendations": recommendations
        }

    # ─── Process Blueprint Gaps ───────────────────────────────────────────
    gaps = gap_analysis["gaps"]
    excess = gap_analysis["excess"]

    # Generate ADD recommendations for each gap
    for dim_key in ["bloom", "difficulty", "topic"]:
        for gap in gaps.get(dim_key, []):
            gap_spec = {dim_key: gap["category"]}
            deficit = gap["deficit"]

            # Search Question Bank for candidates
            candidates = _search_question_bank(
                exam_id=exam_id,
                target_bloom=gap["category"] if dim_key == "bloom" else None,
                target_difficulty=gap["category"] if dim_key == "difficulty" else None,
                target_topic=gap["category"] if dim_key == "topic" else None,
                weights=weights,
                limit=5
            )

            priority = "HIGH" if deficit >= 3 else ("MEDIUM" if deficit >= 1 else "LOW")

            recommendations.append({
                "action": "ADD",
                "reason": f"Short {deficit} {gap['category']} question(s) in {dim_key}. Target: {gap['target']}, Current: {gap['actual']}.",
                "priority": priority,
                "gap": gap_spec,
                "candidates": candidates
            })

    # Generate REMOVE recommendations for excess
    for dim_key in ["bloom", "difficulty", "topic"]:
        for ex in excess.get(dim_key, []):
            surplus = ex["surplus"]
            if surplus >= 2:  # Only recommend removal for significant excess
                removable = _find_removable_questions(
                    exam_id=exam_id,
                    category_key=dim_key,
                    category_value=ex["category"],
                    count=surplus
                )

                recommendations.append({
                    "action": "REMOVE",
                    "reason": f"Excess {surplus} {ex['category']} question(s) in {dim_key}. Target: {ex['target']}, Current: {ex['actual']}.",
                    "priority": "MEDIUM" if surplus >= 3 else "LOW",
                    "gap": {dim_key: ex["category"]},
                    "candidates": removable
                })

    # Check for low-quality questions → REVIEW
    low_quality = _find_low_quality_questions(exam_id)
    for lq in low_quality:
        recommendations.append({
            "action": "REVIEW",
            "reason": f"Question #{lq['id']} has low quality score ({lq['quality']:.2f}).",
            "priority": "MEDIUM",
            "gap": {},
            "candidates": []
        })

    # Sort recommendations by priority
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 3))

    gap_summary = (
        f"{gap_analysis['total_deficit']} question(s) needed, "
        f"{gap_analysis['total_surplus']} excess."
    )

    return {
        "exam_id": exam_id,
        "has_blueprint": True,
        "gap_summary": gap_summary,
        "recommendations": recommendations
    }


def _search_question_bank(
    exam_id: int,
    target_bloom: str = None,
    target_difficulty: str = None,
    target_topic: str = None,
    weights: dict = None,
    limit: int = 5
) -> List[dict]:
    """
    Search the Question Bank for candidates that match the gap.
    Filters: valid, not archived, not already in this exam, not duplicate.
    Ranks by weighted score.
    """
    # Base query: all non-archived questions NOT in this exam
    with get_db_session() as db:
        query = db.query(Question).filter(
            Question.exam_id != exam_id,
            Question.is_archived == False
        )

        # Apply filters
        if target_topic:
            query = query.filter(Question.topic == target_topic)
        if target_bloom:
            query = query.filter(Question.bloom_level == target_bloom)
        if target_difficulty:
            query = query.filter(Question.difficulty == target_difficulty)

        candidates = query.limit(50).all()  # Fetch up to 50, then rank

        if not candidates:
            # Try broader search (just topic match)
            if target_topic:
                candidates = db.query(Question).filter(
                    Question.exam_id != exam_id,
                    Question.is_archived == False,
                    Question.topic == target_topic
                ).limit(20).all()

        if not candidates:
            return []

        detached_candidates = [
            {
                "id": q.id,
                "text": q.text,
                "exam_id": q.exam_id,
                "topic": q.topic,
                "bloom_level": q.bloom_level,
                "difficulty": q.difficulty,
                "quality_score": q.ai_quality_score
            }
            for q in candidates
        ]

    # Rank candidates
    scored = []
    for q in detached_candidates:
        score = 0.0
        w = weights or DEFAULT_WEIGHTS

        # Topic match
        if target_topic and q["topic"] == target_topic:
            score += w.get("topic_match", 0.2)

        # Bloom match
        if target_bloom and q["bloom_level"] == target_bloom:
            score += w.get("bloom_match", 0.15)

        # Difficulty match
        if target_difficulty and q["difficulty"] == target_difficulty:
            score += w.get("difficulty_match", 0.15)

        # Quality score
        quality = q["quality_score"] or 0.5
        score += w.get("quality_score", 0.1) * quality

        # Blueprint match bonus (all criteria match)
        all_match = True
        if target_topic and q["topic"] != target_topic: all_match = False
        if target_bloom and q["bloom_level"] != target_bloom: all_match = False
        if target_difficulty and q["difficulty"] != target_difficulty: all_match = False
        if all_match:
            score += w.get("blueprint_match", 0.3)

        scored.append((score, q))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "question_id": q["id"],
            "text_preview": q["text"][:120],
            "score": round(s, 3),
            "exam_id": q["exam_id"],
            "topic": q["topic"],
            "bloom_level": q["bloom_level"],
            "difficulty": q["difficulty"],
            "quality_score": q["quality_score"]
        }
        for s, q in scored[:limit]
    ]


def _find_removable_questions(exam_id: int, category_key: str, category_value: str, count: int) -> List[dict]:
    """
    Find questions that could be removed to reduce excess.
    Prefers lowest quality, most recently added.
    """
    with get_db_session() as db:
        query = db.query(Question).filter_by(exam_id=exam_id, is_archived=False)

        if category_key == "bloom":
            query = query.filter(Question.bloom_level == category_value)
        elif category_key == "difficulty":
            query = query.filter(Question.difficulty == category_value)
        elif category_key == "topic":
            query = query.filter(Question.topic == category_value)

        # Order by quality (lowest first), then by id (newest first)
        questions = query.order_by(
            Question.ai_quality_score.asc().nullsfirst(),
            Question.id.desc()
        ).limit(count).all()

        return [
            {
                "question_id": q.id,
                "text_preview": q.text[:120],
                "score": round(q.ai_quality_score or 0.0, 3),
                "exam_id": q.exam_id,
                "topic": q.topic,
                "bloom_level": q.bloom_level,
                "difficulty": q.difficulty,
                "quality_score": q.ai_quality_score
            }
            for q in questions
        ]


def _find_low_quality_questions(exam_id: int, threshold: float = 0.5) -> List[dict]:
    """Find questions in the exam with quality below threshold."""
    with get_db_session() as db:
        questions = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.is_archived == False,
            Question.ai_quality_score != None,
            Question.ai_quality_score < threshold
        ).all()

        return [
            {"id": q.id, "text": q.text[:80], "quality": q.ai_quality_score or 0.0}
            for q in questions
        ]
