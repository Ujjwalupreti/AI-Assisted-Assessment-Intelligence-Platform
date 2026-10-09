from fastapi import APIRouter, Depends, Body, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from auth_middleware import get_current_user, get_teacher_user
from ai.core.qis_persistence import persist_qis_analysis
from datetime import datetime
import jwt
from models import User, Exam, Result, Question, ExamAttempt, Answer, ProctoringEvent
import os
import json
from config import Config

auth_bp = APIRouter()
exam_bp = APIRouter()

# --- 📸 SERVE UPLOADED IMAGES TO TEACHER ---
@exam_bp.get('/uploads/{filename}')
def serve_upload(filename):
    upload_dir = os.path.join(os.getcwd(), 'static', 'uploads')
    return FileResponse(os.path.join(upload_dir, filename))

# --- 🗑 DELETE RESULT ---
@exam_bp.delete('/results/{result_id}')
def delete_result(result_id, db: Session = Depends(get_db), current_user: User = Depends(get_teacher_user)):
    try:
        result = db.get(Result, result_id)
        if not result:
            return JSONResponse(status_code=404, content={"message": "Result not found"})
        
        # Verify teacher owns this exam
        exam = db.get(Exam, result.exam_id)
        if str(exam.creator_id) != str(current_user.id):
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        db.delete(result)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Result deleted successfully"})
    except Exception as e:
        import logging; logging.error(f"DELETE RESULT ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error deleting result"})

# --- LOGIN (JWT Token) ---
@auth_bp.post('/login')
def login(db: Session = Depends(get_db), data: dict = Body(None), request: Request = None):
    try:
        data = data if data else {}
        username = data.get('username', '').strip().lower()
        user = db.execute(select(User).filter_by(username=username)).scalar_one_or_none()

        if user and user.check_password(data.get('password')):
            token = jwt.encode(
                {'user_id': user.id, 'role': user.role},
                getattr(Config, 'SECRET_KEY', 'my_precious_secret'),
                algorithm="HS256"
            )
            return JSONResponse(status_code=200, content={"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}})
        return JSONResponse(status_code=401, content={"message": 'Invalid credentials'})
    except Exception as e:
        import logging; logging.error(f"LOGIN ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Login failed"})

# --- CREATE EXAM ---
@exam_bp.post('')
@exam_bp.post('/')
def create_exam(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        data = data if data else {}
        creator_id = current_user.id

        start_dt = datetime.now()
        end_dt = None

        if 'start_date' in data:
            try: start_dt = datetime.fromisoformat(data['start_date'])
            except: pass
        
        if 'end_date' in data:
            try: end_dt = datetime.fromisoformat(data['end_date'])
            except: pass

        blueprint_json_str = data.get('blueprint_json')
        if blueprint_json_str:
            try:
                bp_dict = json.loads(blueprint_json_str)
                for key in ['topic_distribution', 'difficulty_distribution']:
                    dist = bp_dict.get(key, {})
                    if dist:
                        total = 0.0
                        for k, v in dist.items():
                            if not isinstance(v, (int, float)) or v < 0 or v > 100:
                                raise ValueError(f"Value for {k} in {key} must be between 0 and 100")
                            total += v
                        if abs(total - 100.0) > 0.05:
                            raise ValueError(f"Total weight for {key} must equal exactly 100%. Got {total}%")
            except ValueError as ve:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=str(ve))
            except json.JSONDecodeError:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Invalid JSON in blueprint")
        
        new_exam = Exam(
            title=data.get('title'),
            duration_minutes=data.get('duration_minutes', 60),
            start_date=datetime.fromisoformat(data.get('start_date').replace('Z', '+00:00')),
            end_date=datetime.fromisoformat(data.get('end_date').replace('Z', '+00:00')) if data.get('end_date') else None,
            is_visible=data.get('is_visible', False),
            creator_id=current_user.id,
            blueprint_json=blueprint_json_str,
            creation_mode=data.get('creation_mode', 'manual')
        )
        new_exam.set_password(data.get('password', ''))
        
        db.add(new_exam)
        db.commit()
        db.refresh(new_exam)

        # Link selected_questions for automated mode
        selected_questions = data.get('selected_questions', [])
        if selected_questions:
            for q_id in selected_questions:
                orig_q = db.query(Question).filter(Question.id == q_id).first()
                if orig_q:
                    new_q = Question(
                        exam_id=new_exam.id,
                        text=orig_q.text,
                        option_a=orig_q.option_a,
                        option_b=orig_q.option_b,
                        option_c=orig_q.option_c,
                        option_d=orig_q.option_d,
                        correct_option=orig_q.correct_option,
                        topic=orig_q.topic,
                        difficulty=orig_q.difficulty,
                        bloom_level=orig_q.bloom_level,
                        ai_quality_score=orig_q.ai_quality_score,
                        is_subjective=orig_q.is_subjective,
                        reference_answer=orig_q.reference_answer,
                        rubric=orig_q.rubric,
                        max_marks=orig_q.max_marks,
                        subject=orig_q.subject,
                        subtopic=orig_q.subtopic,
                        question_type=orig_q.question_type,
                        created_by=orig_q.created_by,
                        status=orig_q.status,
                        source='AUTO_ASSEMBLED'
                    )
                    db.add(new_q)
                    
        # Add generated questions from AI Generation
        generated_questions = data.get('generated_questions', [])
        if generated_questions:
            for q_data in generated_questions:
                new_q = Question(
                    exam_id=new_exam.id,
                    text=q_data.get('text', ''),
                    option_a=q_data.get('option_a', ''),
                    option_b=q_data.get('option_b', ''),
                    option_c=q_data.get('option_c', ''),
                    option_d=q_data.get('option_d', ''),
                    correct_option=q_data.get('correct_option', ''),
                    topic=q_data.get('topic', 'General'),
                    difficulty=q_data.get('difficulty', 'Medium'),
                    bloom_level=q_data.get('bloom_level', 'Understand'),
                    question_type='MCQ',
                    created_by=current_user.id,
                    source='AI_GENERATED',
                    status='ACTIVE',
                    duplicate_status='SAFE'
                )
                db.add(new_q)
                db.flush() # Flush to get the new_q.id
                
                # Persist the QIS Analysis metadata that was generated during the preview phase
                ai_analysis = q_data.get('ai_analysis')
                if ai_analysis:
                    persist_qis_analysis(db, new_q.id, ai_analysis)
                    
        # Commit BOTH selected_questions and generated_questions
        if selected_questions or generated_questions:
            db.commit()

        return JSONResponse(status_code=201, content=dict(message='Exam created!', exam_id=new_exam.id))
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# --- GET EXAMS (🚨 WITH TEACHER PRIVACY & PASSWORD FLAGS) ---
@exam_bp.get('')
@exam_bp.get('/')
def get_exams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        user = db.get(User, user_id)

        # 🚨 PRIVACY FIX: Teachers ONLY see exams they created!
        if user.role == 'teacher':
            exams = db.execute(select(Exam).filter_by(creator_id=user.id)).scalars().all()
        else:
            # Students still see all visible exams
            exams = db.execute(select(Exam).filter_by(is_visible=True)).scalars().all()
            
        exams_list = []
        
        for e in exams:
            question_count = db.query(Question).filter_by(exam_id=e.id).count()
            
            # BUG FIX: Hide empty exams from students
            if user.role == 'student' and question_count == 0:
                continue
                
            has_attempted = False
            if user.role == 'student':
                if db.query(Result).filter_by(student_id=user.id, exam_id=e.id).first():
                    has_attempted = True
            
            exams_list.append({
                'id': e.id, 
                'title': e.title, 
                'duration': e.duration_minutes,
                'start_date': e.start_date.isoformat() if e.start_date else None,
                'end_date': e.end_date.isoformat() if e.end_date else None, 
                'attempted': has_attempted,
                'has_password': bool(e.password_hash),
                'question_count': question_count,
                'is_visible': e.is_visible
            })
        
        return JSONResponse(status_code=200, content=exams_list)
    except Exception as e:
        import logging; logging.error(f"GET EXAMS ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error"})

# --- ℹ️ GET EXAM DETAILS FOR LOBBY ---
@exam_bp.get('/{exam_id}/details')
def get_exam_details(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        exam = db.get(Exam, exam_id)
        if not exam:
            return JSONResponse(status_code=404, content={"message": "Not found"})
            
        questions = db.execute(
            select(Question).filter_by(exam_id=exam_id)
        ).scalars().all()
        
        topics = list(set([q.topic for q in questions if hasattr(q, 'topic') and q.topic]))
        
        return JSONResponse(status_code=200, content={
            'title': exam.title,
            'duration': exam.duration_minutes,
            'question_count': len(questions),
            'topics': topics,
            'total_marks': sum(1.0 for q in questions if not getattr(q, 'is_subjective', False)),
            'blueprint_json': exam.blueprint_json
        })
    except Exception as e:
        import logging; logging.error(f"GET DETAILS ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error"})

# --- 🔒 VERIFY EXAM PASSWORD ---
@exam_bp.post('/{exam_id}/verify_password')
def verify_password(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        data = data if data else {}
        exam = db.get(Exam, exam_id)
        
        if not exam:
            return JSONResponse(status_code=404, content={"message": "Exam not found"})
            
        if not exam.check_password(data.get('password')):
            return JSONResponse(status_code=401, content={"message": "Invalid password"})
            
        return JSONResponse(status_code=200, content={"message": "Access granted"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error verifying password"})

# --- 📝 TOGGLE EXAM VISIBILITY (PUBLISH/UNPUBLISH) ---
@exam_bp.put('/{exam_id}/toggle_publish')
def toggle_publish(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user = current_user
            
        exam = db.get(Exam, exam_id)
        if str(exam.creator_id) != str(user.id):
            return JSONResponse(status_code=403, content={"message": "Unauthorized: You do not own this exam!"})
            
        exam.is_visible = not exam.is_visible
        db.commit()
        return JSONResponse(status_code=200, content={'message': 'Success', 'is_visible': exam.is_visible})
    except Exception as e:
        import logging; logging.error(f"TOGGLE PUBLISH ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error toggling visibility"})

# --- DELETE EXAM ---
@exam_bp.delete('/{exam_id}')
def delete_exam(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        exam = db.get(Exam, exam_id)
        if exam:
            if str(exam.creator_id) != str(current_user.id) and current_user.role != 'admin':
                return JSONResponse(status_code=403, content={"message": "Unauthorized: You do not own this exam!"})
                
            # 🚨 FIX: Delete associated questions and attempts first!
            attempts = db.query(ExamAttempt).filter_by(exam_id=exam_id).all()
            for attempt in attempts:
                db.query(Answer).filter_by(attempt_id=attempt.id).delete()
                db.query(ProctoringEvent).filter_by(attempt_id=attempt.id).delete()
            db.query(ExamAttempt).filter_by(exam_id=exam_id).delete()
            db.query(Question).filter_by(exam_id=exam_id).delete()
            db.query(Result).filter_by(exam_id=exam_id).delete()
            db.delete(exam)
            db.commit()
            return JSONResponse(status_code=200, content={"message": "Deleted"})
        return JSONResponse(status_code=404, content={"message": "Not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# --- 📊 GET RESULTS FOR TEACHER DASHBOARD (🚨 WITH SECURITY LOCK) ---
@exam_bp.get('/{exam_id}/results')
def get_results(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        user = db.get(User, user_id)
        
        # 🚨 SECURITY LOCK: Make sure this teacher actually created this exam!
        if user.role == 'teacher':
            exam = db.get(Exam, exam_id)
            if not exam or str(exam.creator_id) != str(user.id):
                return JSONResponse(status_code=403, content={"message": "Unauthorized: You do not own this exam!"})

        results = db.execute(
            select(Result, User).join(User, Result.student_id == User.id).filter(Result.exam_id == exam_id)
        ).all()

        data = []
        for res, student_user in results:
            attempt = db.query(ExamAttempt).filter_by(exam_id=exam_id, student_id=student_user.id).order_by(ExamAttempt.id.desc()).first()
            data.append({
                'id': res.id,
                'student_id': res.student_id,
                'attempt_id': attempt.id if attempt else None,
                'student_name': student_user.username,
                'enrollment_id': student_user.enrollment_id,
                'score': res.score,
                'total_marks': res.total_marks,
                'total_questions': res.total_questions,
                'tab_switches': res.tab_switches,
                'audio_warnings': res.audio_warnings,
                'id_card_url': f"/exams/uploads/{res.id_card_url}" if res.id_card_url else None,
                'face_photo_url': f"/exams/uploads/{res.face_photo_url}" if res.face_photo_url else None,
                'mid_exam_photo_url': f"/exams/uploads/{res.mid_exam_photo_url}" if res.mid_exam_photo_url else None, 
                'integrity_score': res.integrity_score,
                'integrity_label': res.integrity_label,
                'teacher_decision': res.teacher_decision,
                'date_taken': res.date_taken.isoformat() if res.date_taken else None
            })
        
        return JSONResponse(status_code=200, content=data)
    except Exception as e:
        import logging; logging.error(f"GET RESULTS ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error fetching results"})

# --- 🤖 EVALUATE SUBJECTIVE ANSWERS ---
from pydantic import BaseModel
class SubjectiveEvalRequest(BaseModel):
    pass

@exam_bp.post('/{exam_id}/evaluate_subjective/{student_id}')
def evaluate_exam_subjective_answers(exam_id, student_id, request_data: SubjectiveEvalRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user = db.get(User, current_user.id)
        if user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})

        attempt = db.query(ExamAttempt).filter_by(exam_id=exam_id, student_id=student_id).order_by(ExamAttempt.id.desc()).first()
        if not attempt:
            return JSONResponse(status_code=404, content={"message": "Attempt not found"})

        from ai.grading.subjective_evaluator import batch_evaluate_attempt
        stats = batch_evaluate_attempt(db, attempt.id)

        # Update final score in Result
        result = db.query(Result).filter_by(exam_id=exam_id, student_id=student_id).order_by(Result.id.desc()).first()
        if result:
            answers = db.query(Answer).filter_by(attempt_id=attempt.id).all()
            new_score = sum(a.marks_awarded or 0.0 for a in answers)
            result.score = new_score
            db.commit()

        return JSONResponse(status_code=200, content={
            "message": "Evaluation complete",
            "stats": stats,
            "new_total_score": new_score if result else None
        })

    except Exception as e:
        import logging; logging.error(f"EVALUATE ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error evaluating answers"})

# --- ✍️ TEACHER OVERRIDE GRADE ---
class GradeOverrideRequest(BaseModel):
    answer_id: int
    new_marks: float
    feedback: str = ""

@exam_bp.post('/{exam_id}/override_grade/{student_id}')
def override_grade(exam_id, student_id, request_data: GradeOverrideRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if current_user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})

        answer = db.get(Answer, request_data.answer_id)
        if not answer:
            return JSONResponse(status_code=404, content={"message": "Answer not found"})

        question = db.get(Question, answer.question_id)
        if request_data.new_marks > question.max_marks or request_data.new_marks < 0:
            return JSONResponse(status_code=400, content={"message": f"Marks must be between 0 and {question.max_marks}"})

        # Apply override
        old_marks = answer.marks_awarded or 0.0
        diff = request_data.new_marks - old_marks
        
        answer.marks_awarded = request_data.new_marks
        answer.teacher_feedback = request_data.feedback
        answer.is_correct = (request_data.new_marks > 0)

        # Update overall result score
        result = db.query(Result).filter_by(exam_id=exam_id, student_id=student_id).order_by(Result.id.desc()).first()
        if result:
            result.score = (result.score or 0.0) + diff
            
        db.commit()

        return JSONResponse(status_code=200, content={
            "message": "Grade overridden successfully",
            "new_marks": answer.marks_awarded,
            "new_total": result.score if result else None
        })
    except Exception as e:
        import logging; logging.error(f"OVERRIDE ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error overriding grade"})
