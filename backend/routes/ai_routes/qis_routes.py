"""
QIS API Routes — Thin controllers. All analysis logic goes through ai.pipeline.
"""
import json
import threading
import datetime
import concurrent.futures
from fastapi import APIRouter, Depends, Body, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from auth_middleware import get_current_user, get_teacher_user
from database import get_db
from models import Question, AIJob, Exam, QuestionAiAnalysis, DuplicateGroup, QuestionDuplicate, User
from ai.core.pipeline import analyze_question_qis
from ai.core.qis_persistence import persist_qis_analysis, get_current_analysis, apply_teacher_review

qis_bp = APIRouter()


@qis_bp.post('/analyze')

def analyze_single_question(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    POST /api/ai/questions/analyze
    Real-time QIS analysis for a single question.
    """
    try:
        data = data
        text = data.get('text', '').strip()
        if not text:
            return JSONResponse(status_code=400, content={"message": "No question text provided"})

        options = {
            "A": data.get("option_a", ""),
            "B": data.get("option_b", ""),
            "C": data.get("option_c", ""),
            "D": data.get("option_d", "")
        }

        result = analyze_question_qis(
            question_text=text,
            options=options,
            correct_option=data.get('correct_option'),
            expected_topic=data.get('expected_topic'),
            expected_bloom=data.get('expected_bloom'),
            expected_difficulty=data.get('expected_difficulty'),
            existing_questions=data.get('existing_questions', [])
        )

        return JSONResponse(status_code=200, content=result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=200, content={"status": "FAILED", "message": f"QIS error: {str(e)}"})


@qis_bp.post('/analyze-batch')

def analyze_batch_questions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    POST /api/ai/questions/analyze-batch
    Queues a background job to analyze multiple questions.
    """
    try:
        data = data
        questions = data.get('questions', [])
        if not questions:
            return JSONResponse(status_code=400, content={"message": "No questions provided"})

        job = AIJob(
            job_type='BULK_ANALYZE_EXAM',
            target_id=data.get('exam_id', 0),
            status='QUEUED',
            total=len(questions)
        )
        db.add(job)
        db.commit()

        app = None
        thread = threading.Thread(
            target=_background_analyze_batch,
            args=(app, job.id, questions),
            daemon=True
        )
        thread.start()

        return JSONResponse(status_code=200, content={
            "message": "Batch analysis queued",
            "job_id": job.id,
            "total_questions": len(questions)
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


def _background_analyze_batch(app, job_id: int, questions: list):
    """Background thread: analyzes questions one by one, tracks PARTIAL failures."""
    from database import SessionLocal
    with SessionLocal() as db:
        failed_ids = []
        job = db.get(AIJob, job_id)
        if not job:
            return

        job.status = 'PROCESSING'
        db.commit()

        for q_data in questions:
            q_id = q_data.get('id')
            try:
                options = {
                    "A": q_data.get("option_a", ""),
                    "B": q_data.get("option_b", ""),
                    "C": q_data.get("option_c", ""),
                    "D": q_data.get("option_d", "")
                }
                
                # BUG-20 FIX: Add timeout to prevent infinite hangs
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        analyze_question_qis,
                        question_text=q_data.get('text', ''),
                        options=options,
                        correct_option=q_data.get('correct_option')
                    )
                    # 60 seconds timeout per question
                    res = future.result(timeout=60)

                if q_id:
                    persist_qis_analysis(db, q_id, res, commit=True)

                job.successful = (job.successful or 0) + 1

            except Exception as e:
                print(f"[qis_batch] Failed question {q_id}: {e}")
                failed_ids.append(q_id)
                job.failed = (job.failed or 0) + 1

            finally:
                job.processed = (job.processed or 0) + 1
                db.commit()

        # Final status
        job.failed_question_ids = json.dumps(failed_ids)
        job.completed_at = datetime.datetime.utcnow()
        if job.failed and job.failed > 0:
            job.status = 'PARTIAL'
        else:
            job.status = 'COMPLETED'
        db.commit()


@qis_bp.get('/jobs/{job_id}')

def get_job_status(job_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """GET /api/ai/questions/jobs/{job_id}"""
    job = db.get(AIJob, job_id)
    if not job:
        return JSONResponse(status_code=404, content={"message": "Job not found"})

    return JSONResponse(status_code=200, content={
        "job_id": job.id,
        "status": job.status,
        "total": job.total,
        "processed": job.processed,
        "successful": job.successful,
        "failed": job.failed,
        "failed_question_ids": json.loads(job.failed_question_ids or "[]"),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None
    })


@qis_bp.get('/{question_id}/analysis')

def get_analysis(question_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """GET /api/ai/questions/{question_id}/analysis — Get current analysis"""
    analysis = get_current_analysis(db, question_id)
    if not analysis:
        return JSONResponse(status_code=404, content={"message": "No analysis found for this question."})

    ai_data = {}
    if analysis.analysis_json:
        try:
            ai_data = json.loads(analysis.analysis_json)
        except Exception:
            pass

    return JSONResponse(status_code=200, content={
        "question_id": question_id,
        "analysis": ai_data,
        "teacher_review_status": analysis.teacher_review_status,
        "teacher_accepted_at": analysis.teacher_accepted_at.isoformat() if analysis.teacher_accepted_at else None,
        "created_at": analysis.created_at.isoformat(),
        "model_metadata": {
            "model_name": analysis.model_name,
            "model_version": analysis.model_version,
            "analysis_method": analysis.analysis_method
        }
    })


@qis_bp.post('/{question_id}/reanalyze')

def reanalyze_question(question_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """POST /api/ai/questions/{question_id}/reanalyze"""
    question = db.get(Question, question_id)
    if not question:
        return JSONResponse(status_code=404, content={"message": "Question not found"})

    try:
        options = {
            "A": question.option_a or "",
            "B": question.option_b or "",
            "C": question.option_c or "",
            "D": question.option_d or ""
        }

        result = analyze_question_qis(question_text=question.text, options=options)
        persist_qis_analysis(db, question.id, result, commit=True)
        return JSONResponse(status_code=200, content=result)

    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"message": str(e)})


@qis_bp.post('/{question_id}/review')

def submit_review(question_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    POST /api/ai/questions/{question_id}/review

    Body:
    {
        "decision": "ACCEPTED" | "EDITED" | "IGNORED",
        "overrides": {   // optional
            "bloom_level": "Analyze",
            "reason": "Requires comparison of two algorithms."
        }
    }
    """
    data = data
    decision = data.get("decision")
    if decision not in ("ACCEPTED", "EDITED", "IGNORED"):
        return JSONResponse(status_code=400, content={"message": "Invalid decision. Must be ACCEPTED, EDITED, or IGNORED."})

    success = apply_teacher_review(
        db=db,
        question_id=question_id,
        decision=decision,
        teacher_id=current_user.id,
        overrides=data.get("overrides")
    )

    if not success:
        return JSONResponse(status_code=404, content={"message": "No current analysis found for this question."})

    return JSONResponse(status_code=200, content={"message": f"Review decision '{decision}' saved.", "question_id": question_id})


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: DUPLICATE MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@qis_bp.post('/deduplicate')

def deduplicate_questions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    POST /api/ai/questions/deduplicate
    Scan an exam for duplicate questions and create DuplicateGroups.
    Body: {"exam_id": int, "threshold": float (optional, default 0.85)}
    """
    try:
        data = data
        exam_id = data.get('exam_id')
        threshold = data.get('threshold', 0.85)

        if not exam_id:
            return JSONResponse(status_code=400, content={"message": "exam_id is required"})

        from ai.question.duplicate_detector import group_duplicates
        result = group_duplicates(exam_id, threshold=threshold)

        if "error" in result:
            return JSONResponse(status_code=500, content={"message": result["error"]})

        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": str(e)})


@qis_bp.get('/duplicates')

def get_duplicate_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    GET /api/ai/questions/duplicates?exam_id=X
    Returns all duplicate groups for an exam.
    """
    try:
        exam_id_str = request.query_params.get('exam_id')
        if not exam_id_str:
            return JSONResponse(status_code=400, content={"message": "exam_id query parameter is required"})
        exam_id = int(exam_id_str)

        groups = db.query(DuplicateGroup).filter_by(exam_id=exam_id).order_by(
            DuplicateGroup.created_at.desc()
        ).all()

        result = []
        for group in groups:
            members = db.query(QuestionDuplicate).filter_by(group_id=group.id).all()
            member_data = []
            for m in members:
                q = db.get(Question, m.question_id)
                member_data.append({
                    "id": m.id,
                    "question_id": m.question_id,
                    "question_text": q.text[:150] if q else "N/A",
                    "similarity_score": m.similarity_score,
                    "is_primary": m.is_primary,
                    "status": m.status
                })

            result.append({
                "group_id": group.id,
                "status": group.status,
                "threshold": group.similarity_threshold,
                "created_at": group.created_at.isoformat() if group.created_at else None,
                "members": member_data
            })

        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


@qis_bp.post('/duplicates/{group_id}/review')

def review_duplicate_group(group_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    POST /api/ai/questions/duplicates/{group_id}/review
    Teacher decides which question to keep.

    Body: {"decision": "ARCHIVE" | "KEEP_ALL" | "DELETE", "keeper_question_id": int (optional)}
    """
    try:
        data = data
        decision = data.get('decision', 'ARCHIVE')

        if decision == 'KEEP_ALL':
            group = db.get(DuplicateGroup, group_id)
            if group:
                group.status = 'RESOLVED'
                group.resolved_at = datetime.datetime.utcnow()
                group.resolved_by = current_user.id
                # Mark all members as KEPT
                members = db.query(QuestionDuplicate).filter_by(group_id=group_id).all()
                for m in members:
                    m.status = 'KEPT'
                db.commit()
            return JSONResponse(status_code=200, content={"message": "All questions kept."})

        elif decision == 'ARCHIVE':
            from ai.question.duplicate_detector import archive_duplicates
            keeper_id = data.get('keeper_question_id')
            result = archive_duplicates(group_id, keeper_question_id=keeper_id)

            if "error" in result:
                return JSONResponse(status_code=404, content={"message": result["error"]})

            # Set resolved_by
            group = db.get(DuplicateGroup, group_id)
            if group:
                group.resolved_by = current_user.id
                db.commit()

            return JSONResponse(status_code=200, content=result)

        else:
            return JSONResponse(status_code=400, content={"message": f"Unknown decision: {decision}"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: EXAM SUMMARY & RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════

@qis_bp.get('/exam/{exam_id}/summary')

def get_exam_qis_summary(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    GET /api/ai/questions/exam/{exam_id}/summary
    Exam-level QIS summary with distributions and quality metrics.
    """
    try:
        analyses = db.query(QuestionAiAnalysis).join(Question).filter(
            Question.exam_id == exam_id,
            QuestionAiAnalysis.is_current == True
        ).all()

        total = len(analyses)
        if total == 0:
            return JSONResponse(status_code=200, content={"message": "No analysis data. Run analysis first.", "total": 0})

        bloom_counts = {}
        difficulty_counts = {}
        topic_counts = {}
        total_quality = 0.0
        methods_used = {}

        for a in analyses:
            if a.bloom_label:
                bloom_counts[a.bloom_label] = bloom_counts.get(a.bloom_label, 0) + 1
            if a.difficulty_label:
                difficulty_counts[a.difficulty_label] = difficulty_counts.get(a.difficulty_label, 0) + 1
            if a.topic_label:
                topic_counts[a.topic_label] = topic_counts.get(a.topic_label, 0) + 1
            total_quality += (a.quality_score or 0.0)
            method = a.analysis_method or "unknown"
            methods_used[method] = methods_used.get(method, 0) + 1

        avg_quality = total_quality / total if total > 0 else 0
        high_risk = sum(1 for a in analyses if a.duplicate_risk and a.duplicate_risk >= 0.85)

        return JSONResponse(status_code=200, content={
            "exam_id": exam_id,
            "total_questions": total,
            "average_quality": round(avg_quality, 3),
            "duplicate_risk_count": high_risk,
            "bloom_distribution": bloom_counts,
            "difficulty_distribution": difficulty_counts,
            "topic_distribution": topic_counts,
            "analysis_methods": methods_used
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


@qis_bp.get('/exam/{exam_id}/recommendations')

def get_exam_recommendations(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    GET /api/ai/questions/exam/{exam_id}/recommendations
    Returns recommendations for the exam based on blueprint gap analysis.
    """
    try:
        from ai.exam.recommender import generate_recommendations
        recommendations = generate_recommendations(exam_id)
        return JSONResponse(status_code=200, content=recommendations)
    except ImportError:
        return JSONResponse(status_code=200, content=dict(message="Recommendation engine not yet available.", recommendations=[]))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": str(e)})

