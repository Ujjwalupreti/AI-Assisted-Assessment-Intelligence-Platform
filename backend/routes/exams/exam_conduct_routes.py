from fastapi import APIRouter, Depends, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from auth_middleware import get_current_user
from datetime import datetime
from models import User, Exam, Result, Question, ExamAttempt, Answer, ProctoringEvent
import os
import base64
import uuid

conduct_bp = APIRouter()

# --- 📸 HELPER: SAVE BASE64 IMAGES LOCALLY ---
def save_base64_image(base64_data):
    if not base64_data:
        return None
    try:
        header, encoded = base64_data.split(",", 1)
        file_ext = header.split('/')[1].split(';')[0]
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        filepath = os.path.join(os.getcwd(), 'static', 'uploads', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(encoded))
        return filename
    except Exception as e:
        print(f"Image save error: {e}")
        return None

# --- 🚨 START EXAM (CREATE ATTEMPT) ---
@conduct_bp.post('/{exam_id}/start')
def start_exam(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        exam = db.get(Exam, exam_id)
        if not exam:
            return JSONResponse(status_code=404, content={"message": "Exam not found"})

        # Handle retakes by deleting existing attempts (for MVP purposes)
        existing_attempts = db.query(ExamAttempt).filter_by(exam_id=exam_id, student_id=user_id).all()
        for old_attempt in existing_attempts:
            from models import Answer, ProctoringEvent
            db.query(Answer).filter_by(attempt_id=old_attempt.id).delete(synchronize_session=False)
            db.query(ProctoringEvent).filter_by(attempt_id=old_attempt.id).delete(synchronize_session=False)
            db.delete(old_attempt)
        if existing_attempts:
            db.commit()

        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=user_id,
            status='IN_PROGRESS'
        )
        db.add(attempt)
        db.commit()
        return JSONResponse(status_code=201, content=dict(message="Exam started", attempt_id=attempt.id))
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# --- 🚨 SUBMIT EXAM & RECORD WARNINGS + IMAGES ---
@conduct_bp.post('/{exam_id}/submit')
def submit_exam(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        current_user_id = current_user.id
        data = data if data else {}
        
        answers = data.get('answers', {})
        tab_switches = data.get('tab_switches', 0)
        audio_warnings = data.get('audio_warnings', 0)
        
        if audio_warnings > 5:
            audio_warnings = 5

        # 🚨 DECODE AND SAVE ALL 3 IMAGES
        id_filename = save_base64_image(data.get('id_image'))
        face_filename = save_base64_image(data.get('face_image'))
        mid_exam_filename = save_base64_image(data.get('mid_exam_photo')) # <-- NEW SECRET PHOTO

        questions = db.execute(select(Question).filter_by(exam_id=exam_id)).scalars().all()
        
        # 🧠 PHASE 1: GET OR CREATE EXAM ATTEMPT
        attempt = db.query(ExamAttempt).filter_by(
            exam_id=exam_id, 
            student_id=current_user_id, 
            status='IN_PROGRESS'
        ).first()

        if not attempt:
            # Fallback if start wasn't called (backward compatibility for now)
            attempt = ExamAttempt(exam_id=exam_id, student_id=current_user_id, status='IN_PROGRESS')
            db.add(attempt)
            db.flush()

        # Enforce Server-Side Timer (grace period of 5 mins)
        exam = db.get(Exam, exam_id)
        if exam and attempt.start_time:
            time_spent = (datetime.utcnow() - attempt.start_time).total_seconds()
            allowed_time = (exam.duration_minutes * 60) + 300 # 5 minutes grace
            if time_spent > allowed_time:
                return JSONResponse(status_code=403, content={"message": "Time limit exceeded"})

        attempt.status = 'SUBMITTED'
        attempt.end_time = datetime.utcnow()

        score = 0.0
        total_max_marks = 0.0
        for q in questions:
            total_max_marks += q.max_marks
            selected = answers.get(str(q.id))
            is_correct = False
            marks_for_this_q = 0.0
            
            if not q.is_subjective:
                if selected is not None and selected == q.correct_option:
                    is_correct = True
                    marks_for_this_q = q.max_marks
                    score += marks_for_this_q
                    
            # Save individual answers for later AI analytics
            answer_record = Answer(
                attempt_id=attempt.id,
                question_id=q.id,
                selected_option=selected if not q.is_subjective else None,
                answer_text=selected if q.is_subjective else None,
                is_correct=is_correct,
                marks_awarded=marks_for_this_q
            )
            db.add(answer_record)

        # Keep original Result for backwards compatibility with Teacher Dashboard
        from ai.proctoring.proctoring_core import calculate_integrity_score
        
        # Log legacy proctoring events directly if frontend still uses old counters
        for _ in range(tab_switches):
            db.add(ProctoringEvent(attempt_id=attempt.id, event_type='TAB_SWITCH', severity='LOW', confidence=1.0))
        for _ in range(audio_warnings):
            db.add(ProctoringEvent(attempt_id=attempt.id, event_type='AUDIO_ACTIVITY', severity='LOW', confidence=1.0))
        db.flush() # Ensure events are written so we can calculate the score
        
        score_val, label = calculate_integrity_score(db, attempt.id)

        result = Result(
            exam_id=exam_id,
            student_id=current_user_id,
            score=score,
            total_marks=total_max_marks,
            total_questions=len(questions),
            tab_switches=tab_switches,
            audio_warnings=audio_warnings,
            id_card_url=id_filename,        
            face_photo_url=face_filename,
            mid_exam_photo_url=mid_exam_filename, # <-- SAVED TO DB
            integrity_score=score_val,
            integrity_label=label,
            teacher_decision='PENDING'
        )
        db.add(result)
        db.commit()
        
        return JSONResponse(status_code=200, content={"message": "Exam submitted successfully", "score": score})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error submitting exam"})

# --- 📝 GET STUDENT EXAM REVIEW ---
@conduct_bp.get('/{exam_id}/review')
def get_exam_review(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        
        # 1. Fetch the latest attempt for this user/exam
        attempt = db.execute(
            select(ExamAttempt)
            .filter_by(student_id=user_id, exam_id=exam_id)
            .order_by(ExamAttempt.id.desc())
        ).scalars().first()
        
        if not attempt:
            return JSONResponse(status_code=404, content={"message": "No attempt found for this exam"})
            
        # 2. Fetch the questions
        questions = db.execute(
            select(Question).filter_by(exam_id=exam_id)
        ).scalars().all()
        
        # 3. Fetch the answers
        answers = db.execute(
            select(Answer).filter_by(attempt_id=attempt.id)
        ).scalars().all()
        
        answer_map = {a.question_id: a for a in answers}
        
        review_data = []
        for q in questions:
            ans = answer_map.get(q.id)
            review_data.append({
                'question_text': q.text,
                'options': {
                    'A': q.option_a,
                    'B': q.option_b,
                    'C': q.option_c,
                    'D': q.option_d,
                },
                'correct_option': q.correct_option,
                'is_subjective': q.is_subjective,
                'student_answer': ans.selected_option if ans else None,
                'is_correct': ans.is_correct if ans else False,
                'marks_awarded': ans.marks_awarded if ans else 0.0
            })
            
        # Fetch the Result for penalties
        result = db.execute(
            select(Result).filter_by(student_id=user_id, exam_id=exam_id).order_by(Result.id.desc())
        ).scalars().first()
            
        return JSONResponse(status_code=200, content={
            'score': result.score if result else sum(a.marks_awarded for a in answers) if answers else 0,
            'total': len(questions),
            'tab_switches': result.tab_switches if result else 0,
            'audio_warnings': result.audio_warnings if result else 0,
            'questions': review_data
        })
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error fetching exam review"})

# --- 📝 GET STUDENT EXAM REVIEW (FOR TEACHERS) ---
@conduct_bp.get('/{exam_id}/review/{student_id}')
def get_student_exam_review_for_teacher(exam_id, student_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        user = db.get(User, user_id)
        if user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        attempt = db.execute(
            select(ExamAttempt)
            .filter_by(student_id=student_id, exam_id=exam_id)
            .order_by(ExamAttempt.id.desc())
        ).scalars().first()
        
        if not attempt:
            return JSONResponse(status_code=404, content={"message": "No attempt found for this exam"})
            
        questions = db.execute(select(Question).filter_by(exam_id=exam_id)).scalars().all()
        answers = db.execute(select(Answer).filter_by(attempt_id=attempt.id)).scalars().all()
        answer_map = {a.question_id: a for a in answers}
        
        review_data = []
        for q in questions:
            ans = answer_map.get(q.id)
            review_data.append({
                'id': ans.id if ans else None,
                'question_id': q.id,
                'question_text': q.text,
                'options': {'A': q.option_a, 'B': q.option_b, 'C': q.option_c, 'D': q.option_d},
                'correct_option': q.correct_option,
                'is_subjective': q.is_subjective,
                'reference_answer': q.reference_answer,
                'student_answer': ans.answer_text if q.is_subjective else (ans.selected_option if ans else None),
                'is_correct': ans.is_correct if ans else False,
                'marks_awarded': ans.marks_awarded if ans else 0.0,
                'ai_suggested_marks': ans.ai_suggested_marks if ans else None,
                'ai_explanation': ans.ai_explanation if ans else None,
                'teacher_feedback': ans.teacher_feedback if ans else None
            })
            
        result = db.execute(select(Result).filter_by(student_id=student_id, exam_id=exam_id).order_by(Result.id.desc())).scalars().first()
            
        return JSONResponse(status_code=200, content={
            'score': result.score if result else sum(a.marks_awarded for a in answers) if answers else 0,
            'total': len(questions),
            'tab_switches': result.tab_switches if result else 0,
            'audio_warnings': result.audio_warnings if result else 0,
            'questions': review_data
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error fetching exam review"})
