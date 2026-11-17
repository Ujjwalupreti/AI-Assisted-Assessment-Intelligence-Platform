"""
QIS API Routes — Thin controllers. All analysis logic goes through ai.pipeline.
"""
import json
import re
import threading
import datetime
import concurrent.futures
from typing import Optional, List, Dict, Any
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
                    persist_qis_analysis(q_id, res, commit=True)

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
    if analysis.ai_analysis_json:
        try:
            ai_data = json.loads(analysis.ai_analysis_json)
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
        persist_qis_analysis(question.id, result, commit=True)
        return JSONResponse(status_code=200, content=result)

    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"message": str(e)})


@qis_bp.post('/{question_id}/review')
def submit_review(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
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
    data = data or {}
    raw_decision = str(data.get("decision", "")).strip().upper()
    if raw_decision in ("ACCEPT", "ACCEPTED"):
        decision = "ACCEPTED"
    elif raw_decision in ("EDIT", "EDITED"):
        decision = "EDITED"
    elif raw_decision in ("IGNORE", "IGNORED"):
        decision = "IGNORED"
    else:
        return JSONResponse(status_code=400, content={"message": "Invalid decision. Must be ACCEPTED, EDITED, or IGNORED."})

    # Ensure an analysis exists before reviewing
    analysis = get_current_analysis(db, question_id)
    if not analysis:
        q = db.get(Question, question_id)
        if q:
            opts = {"A": q.option_a or "", "B": q.option_b or "", "C": q.option_c or "", "D": q.option_d or ""}
            qis_res = analyze_question_qis(question_text=q.text, options=opts)
            persist_qis_analysis(db, q.id, qis_res, commit=True)

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

        from ai.generation.duplicate_detector import group_duplicates
        result = group_duplicates(exam_id, threshold=threshold)

        if "error" in result:
            return JSONResponse(status_code=500, content={"message": result["error"]})

        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": str(e)})


@qis_bp.get('/duplicates')
@qis_bp.get('/exam/{exam_id}/duplicates')
def get_duplicate_groups(exam_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    """
    GET /api/ai/questions/duplicates?exam_id=X or GET /api/ai/questions/exam/{exam_id}/duplicates
    Returns all duplicate groups for an exam.
    """
    try:
        if exam_id is None and request:
            exam_id_str = request.query_params.get('exam_id')
            if exam_id_str:
                exam_id = int(exam_id_str)
        if not exam_id:
            return JSONResponse(status_code=400, content={"message": "exam_id query parameter is required"})

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
            from ai.generation.duplicate_detector import archive_duplicates
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
            if a.bloom_level:
                bloom_counts[a.bloom_level] = bloom_counts.get(a.bloom_level, 0) + 1
            if a.difficulty:
                difficulty_counts[a.difficulty] = difficulty_counts.get(a.difficulty, 0) + 1
            if a.topic:
                topic_counts[a.topic] = topic_counts.get(a.topic, 0) + 1
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
        from ai.assembly.recommender import generate_recommendations
        recommendations = generate_recommendations(exam_id)
        return JSONResponse(status_code=200, content=recommendations)
    except ImportError:
        return JSONResponse(status_code=200, content=dict(message="Recommendation engine not yet available.", recommendations=[]))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"message": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: TEACHER AI ASSISTANCE & QUESTION IMPROVEMENT
# ═══════════════════════════════════════════════════════════════════════════

@qis_bp.post('/assist')
def assist_question(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(...)):
    """
    POST /api/ai/questions/assist
    AI assistance for subjective question creation:
    - Grammar & spelling correction
    - Ambiguity & missing condition detection
    - Incorrect math syntax detection
    - Reference answer suggestion
    - Marking rubric generation with partial marking breakdown
    - Bloom's level and difficulty recommendation
    - Alternative question versions
    """
    try:
        text = str(data.get('text', '')).strip()
        q_type = str(data.get('question_type', 'SUBJECTIVE')).upper()
        topic = str(data.get('topic', '')).strip()
        max_marks = float(data.get('max_marks', 5.0))
        ref_ans = str(data.get('reference_answer', '')).strip()
        
        if not text:
            return JSONResponse(status_code=400, content={"message": "Question text is required."})

        # 1. Deterministic Analysis Layer (always runs)
        det_issues = []
        if len(text) < 15:
            det_issues.append({"type": "TOO_SHORT", "severity": "high", "message": "Question statement is very brief and may lack required context."})
        if not any(text.endswith(p) for p in ['?', '.', ':']):
            det_issues.append({"type": "PUNCTUATION", "severity": "low", "message": "Question lacks concluding punctuation (e.g. '?' or '.')."})
            
        # Math & Automata specific structural checks
        if q_type in ('MATH_PROBLEM', 'DERIVATION', 'NUMERICAL', 'PROOF'):
            if text.count('(') != text.count(')') or text.count('[') != text.count(']'):
                det_issues.append({"type": "MATH_SYNTAX", "severity": "high", "message": "Unbalanced parentheses or brackets detected in mathematical statement."})
            if '^' in text and not re.search(r'\b[a-zA-Z0-9]\^[0-9a-zA-Z]', text):
                det_issues.append({"type": "MATH_NOTATION", "severity": "medium", "message": "Check exponent notation. Use x^2 or standard LaTeX."})
        elif q_type in ('DFA_NFA', 'STATE_TRANSITION'):
            lower = text.lower()
            if 'alphabet' not in lower and 'sigma' not in lower and '{0, 1}' not in lower and '{a, b}' not in lower:
                det_issues.append({"type": "MISSING_CONDITION", "severity": "medium", "message": "No input alphabet (Sigma) explicitly stated in automata question."})

        from ai.classifiers.bloom_classifier import classify_bloom
        from ai.classifiers.difficulty_estimator import estimate_difficulty
        
        det_bloom = classify_bloom(text).get('label', 'Apply')
        det_diff = estimate_difficulty(text).get('label', 'Medium')
        
        # Standard rubric generation fallback
        if q_type in ('MATH_PROBLEM', 'DERIVATION'):
            p1 = round(max_marks * 0.3, 1)
            p2 = round(max_marks * 0.4, 1)
            p3 = round(max_marks - p1 - p2, 1)
            det_rubric = (
                f"1. Problem Formulation & Setup: {p1} marks\n"
                f"2. Intermediate Derivation & Calculation Steps: {p2} marks\n"
                f"3. Final Result, Units & Simplification: {p3} marks"
            )
        elif q_type in ('DFA_NFA', 'STATE_TRANSITION'):
            p1 = round(max_marks * 0.25, 1)
            p2 = round(max_marks * 0.50, 1)
            p3 = round(max_marks - p1 - p2, 1)
            det_rubric = (
                f"1. Formal 5-tuple Definition & State Identification: {p1} marks\n"
                f"2. Correct Transition Logic & Determinism: {p2} marks\n"
                f"3. Accurate Initial & Final State Designations: {p3} marks"
            )
        elif q_type == 'TABLE':
            p1 = round(max_marks * 0.3, 1)
            p2 = round(max_marks - p1, 1)
            det_rubric = (
                f"1. Table Schema & Column Headers: {p1} marks\n"
                f"2. Accuracy and Completeness of Cell Entries: {p2} marks"
            )
        else:
            p1 = round(max_marks * 0.4, 1)
            p2 = round(max_marks * 0.4, 1)
            p3 = round(max_marks - p1 - p2, 1)
            det_rubric = (
                f"1. Core Concept Definition & Accuracy: {p1} marks\n"
                f"2. Key Arguments & Detailed Explanation: {p2} marks\n"
                f"3. Clarity, Terminology & Contextual Examples: {p3} marks"
            )

        # 2. LLM Semantic Enhancement (if available)
        llm_data = None
        try:
            from ai.core.llm_client import generate_json
            prompt = f"""
            Act as an educational assessment expert. Assist the teacher with the following subjective question.
            
            Question: {text}
            Question Type: {q_type}
            Topic: {topic or 'General'}
            Max Marks: {max_marks}
            Reference Answer (Current): {ref_ans or 'None provided'}
            
            Provide structured suggestions to improve this question:
            1. Identify issues (grammar, ambiguity, missing conditions, or incorrect mathematical expressions).
            2. Suggest an improved, clearer version of the question text.
            3. Suggest a comprehensive reference answer / solution.
            4. Generate a criteria-based marking rubric allocating total {max_marks} marks.
            5. Suggest Bloom's Taxonomy Level ('Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create').
            6. Suggest Difficulty ('Easy', 'Medium', 'Hard').
            7. Extract 3-5 important keywords/concepts.
            8. Provide 1-2 alternative phrasings of the question.
            
            Return ONLY a valid JSON object matching this schema:
            {{
                "identified_issues": [
                    {{"type": "<AMBIGUITY|GRAMMAR|MISSING_CONDITION|MATH_ERROR>", "severity": "<low|medium|high>", "message": "<specific explanation>"}}
                ],
                "suggested_version": "<improved question text>",
                "suggested_reference_answer": "<ideal answer or solution>",
                "suggested_rubric": "<detailed marking rubric with marks breakdown>",
                "suggested_bloom": "<Bloom level>",
                "suggested_difficulty": "<Difficulty>",
                "keywords": ["<keyword1>", "<keyword2>"],
                "alternative_versions": ["<alternative phrasing 1>"]
            }}
            """
            llm_data = generate_json(prompt, temperature=0.3)
        except Exception as e:
            print(f"[assist_question] LLM generation skipped: {e}")

        # Merge results safely
        if llm_data and isinstance(llm_data, dict) and "suggested_version" in llm_data:
            merged_issues = det_issues + [i for i in llm_data.get("identified_issues", []) if isinstance(i, dict)]
            return JSONResponse(status_code=200, content={
                "status": "SUCCESS",
                "source": "AI_LLM_ASSIST",
                "original_question": text,
                "identified_issues": merged_issues,
                "suggested_version": llm_data.get("suggested_version", text),
                "suggested_reference_answer": llm_data.get("suggested_reference_answer", ref_ans),
                "suggested_rubric": llm_data.get("suggested_rubric", det_rubric),
                "suggested_bloom": llm_data.get("suggested_bloom", det_bloom),
                "suggested_difficulty": llm_data.get("suggested_difficulty", det_diff),
                "keywords": llm_data.get("keywords", [topic] if topic else []),
                "alternative_versions": llm_data.get("alternative_versions", [])
            })

        # Deterministic fallback return
        return JSONResponse(status_code=200, content={
            "status": "SUCCESS",
            "source": "DETERMINISTIC_ASSIST",
            "original_question": text,
            "identified_issues": det_issues,
            "suggested_version": text if text.endswith('?') else f"{text}?",
            "suggested_reference_answer": ref_ans or f"Expected solution explaining core principles of {topic or 'the question'}.",
            "suggested_rubric": det_rubric,
            "suggested_bloom": det_bloom,
            "suggested_difficulty": det_diff,
            "keywords": [topic] if topic else ["core concept"],
            "alternative_versions": [f"Explain in detail: {text}"]
        })

    except Exception as e:
        print(f"Error in assist_question: {e}")
        return JSONResponse(status_code=500, content={"message": f"Assistance error: {str(e)}"})

