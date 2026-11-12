"""
QIS Persistence Layer.

Handles: QuestionAiAnalysis records with is_current flag.

When a new analysis is persisted:
  - All previous analyses for the same question are marked is_current=False
  - New analysis is marked is_current=True

This allows the intelligence report to always use the latest analysis.
"""
import json
from database import get_db
from datetime import datetime
from models import Question, QuestionAiAnalysis


def persist_qis_analysis(db, question_id: int, result: dict, commit: bool = False) -> QuestionAiAnalysis:
    """
    Persist canonical AnalysisResult to the database.

    Args:
        db: SQLAlchemy session
        question_id: The Question.id
        result: Canonical AnalysisResult dict from analyze_question_qis()
        commit: If True, commit the session. Default False (let caller manage transaction).

    Returns: The new QuestionAiAnalysis record.
    """
    q = db.get(Question, question_id)
    if not q:
        raise ValueError(f"Question {question_id} not found")

    # Mark all previous analyses for this question as no longer current
    try:
        db.query(QuestionAiAnalysis).filter_by(
            question_id=question_id,
            is_current=True
        ).update({"is_current": False}, synchronize_session=False)
    except Exception as e:
        print(f"[qis_persistence] Could not update is_current flags: {e}")

    classification = result.get("classification", {})
    topic_data     = classification.get("topic", {})
    bloom_data     = classification.get("bloom", {})
    diff_data      = classification.get("difficulty", {})
    type_data      = classification.get("question_type", {})
    quality        = result.get("quality", {})
    dup_data       = result.get("duplicate", {})
    meta           = result.get("model_metadata", {})

    # Recommendations serialized as JSON
    recs = result.get("recommendations", [])
    recs_json = json.dumps(recs) if recs else "[]"

    # Quality issues serialized (from validation)
    validation = result.get("validation", {})
    issues_json = json.dumps(validation.get("issues", []))

    analysis = QuestionAiAnalysis(
        question_id=question_id,
        model_name=meta.get("model_name"),
        model_version=meta.get("model_version"),
        topic_label=topic_data.get("label"),
        topic_confidence=topic_data.get("confidence"),
        bloom_label=bloom_data.get("label"),
        bloom_confidence=bloom_data.get("confidence"),
        difficulty_label=diff_data.get("label"),
        difficulty_confidence=diff_data.get("confidence"),
        question_type=type_data.get("label"),
        question_type_confidence=type_data.get("confidence"),
        quality_score=quality.get("overall_score"),
        duplicate_risk=dup_data.get("risk"),
        analysis_json=json.dumps(result),
        teacher_review_status="PENDING",
        analysis_status=meta.get("llm_status", "PARTIAL"),
        is_current=True
    )

    # Update denormalized fields on Question for quick access
    if topic_data.get("label"):
        q.topic = topic_data["label"]
    if bloom_data.get("label"):
        q.bloom_level = bloom_data["label"]
    if diff_data.get("label"):
        q.difficulty = diff_data["label"]
    if quality.get("overall_score") is not None:
        q.ai_quality_score = quality["overall_score"]
    q.is_subjective = (type_data.get("label") not in ("MCQ", "TRUE_FALSE", "NUMERICAL", "FILL_IN_THE_BLANK"))

    db.add(analysis)

    if commit:
        db.commit()
    else:
        db.flush()

    return analysis


def get_current_analysis(db, question_id: int) -> QuestionAiAnalysis:
    """Retrieve the current (latest accepted) analysis for a question."""
    return db.query(QuestionAiAnalysis).filter_by(
        question_id=question_id,
        is_current=True
    ).order_by(QuestionAiAnalysis.created_at.desc()).first()


def get_analysis_history(db, question_id: int):
    """Retrieve all historical analyses for a question."""
    return db.query(QuestionAiAnalysis).filter_by(
        question_id=question_id
    ).order_by(QuestionAiAnalysis.created_at.desc()).all()


def apply_teacher_review(db, question_id: int, decision: str, teacher_id: int,
                          overrides: dict = None) -> bool:
    """
    Apply teacher review decision to the current analysis.

    Args:
        db: SQLAlchemy session
        question_id: Question.id
        decision: 'ACCEPTED' | 'EDITED' | 'IGNORED'
        teacher_id: User.id of the reviewing teacher
        overrides: Optional dict of teacher-provided corrections
                   e.g. {"bloom_level": "Analyze", "reason": "Requires comparison"}

    Returns: True if successful.
    """
    analysis = get_current_analysis(db, question_id)
    if not analysis:
        return False

    analysis.teacher_review_status = decision
    analysis.teacher_accepted_at = datetime.utcnow()

    if overrides:
        # Load the full JSON to add teacher override metadata
        try:
            data = json.loads(analysis.ai_analysis_json or "{}")
            data["teacher_override"] = {
                "teacher_id": teacher_id,
                "decision": decision,
                "timestamp": datetime.utcnow().isoformat(),
                "overrides": overrides
            }
            analysis.ai_analysis_json = json.dumps(data)
        except Exception as e:
            print(f"[qis_persistence] Could not save teacher override metadata: {e}")

    db.commit()
    return True
