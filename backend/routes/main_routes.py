from fastapi import APIRouter, Depends, Body, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from auth_middleware import get_current_user, get_teacher_user
from datetime import datetime
import jwt
from models import User, Exam, Result, Question, ExamAttempt, Answer, ProctoringEvent
import os
import base64
import uuid
import csv
import io
import json
from config import Config

# 🚨 NEW IMPORTS FOR AI IMAGE DECODING
import cv2
import numpy as np
# pyrefly: ignore [missing-import]
from ultralytics import YOLO

# ==========================================
# 🧠 INITIALIZE AI MODELS GLOBALLY
# ==========================================
try:
    _yolo_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'yolov8n.pt'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yolov8n.pt'),
        'yolov8n.pt'
    ]
    _chosen_path = next((p for p in _yolo_paths if os.path.exists(p)), 'yolov8n.pt')
    model = YOLO(_chosen_path)
except Exception as e:
    print("WARNING: Error loading YOLO model. Object detection disabled:", e)
    model = None

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
# ==========================================

auth_bp = APIRouter()
exam_bp = APIRouter()

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

# --- 📸 SERVE UPLOADED IMAGES TO TEACHER (PATH TRAVERSAL PROTECTED) ---
@exam_bp.get('/uploads/{filename}')
def serve_upload(filename: str):
    clean_name = os.path.basename(filename)
    upload_dir = os.path.abspath(os.path.join(os.getcwd(), 'static', 'uploads'))
    target_path = os.path.abspath(os.path.join(upload_dir, clean_name))
    if not target_path.startswith(upload_dir) or not os.path.isfile(target_path):
        return JSONResponse(status_code=404, content={"message": "File not found"})
    return FileResponse(target_path)

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
        print(f"DELETE RESULT ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error deleting result"})


# --- LOGIN (JWT Token) ---
@auth_bp.post('/login')
def login(db: Session = Depends(get_db), data: dict = Body(None), request: Request = None):
    try:
        data = data
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
        print(f"LOGIN ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Login failed"})


# --- CREATE EXAM ---
@exam_bp.post('')
@exam_bp.post('/')
def create_exam(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        data = data
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
            import json
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

        # BUG FIX: Link selected_questions for automated mode
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
            db.commit()

        return JSONResponse(status_code=201, content=dict(message='Exam created!', exam_id=new_exam.id))
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


# --- GET EXAMS (🚨 WITH TEACHER PRIVACY & PASSWORD FLAGS) ---
@exam_bp.get('')
@exam_bp.get('/')
def get_exams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), request: Request = None):
    try:
        user_id = current_user.id
        user = db.get(User, user_id)

        # 🚨 PRIVACY FIX: Teachers see exams they created or unassigned template exams
        if user.role == 'teacher':
            from sqlalchemy import or_
            exams = db.execute(select(Exam).filter(or_(Exam.creator_id == user.id, Exam.creator_id == None))).scalars().all()
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
            assigned_slot = None
            if user.role == 'student':
                if db.query(Result).filter_by(student_id=user.id, exam_id=e.id).first():
                    has_attempted = True
                
                if getattr(e, 'slotting_enabled', False):
                    from models import StudentExamTimeSlot, ExamTimeSlot
                    assignment = db.query(StudentExamTimeSlot).filter_by(exam_id=e.id, student_id=user.id).first()
                    if assignment:
                        slot = db.get(ExamTimeSlot, assignment.slot_id)
                        if slot:
                            assigned_slot = {
                                "start_time": slot.start_time.isoformat(),
                                "end_time": slot.end_time.isoformat()
                            }
            
            exams_list.append({
                'id': e.id, 
                'title': e.title, 
                'duration': e.duration_minutes,
                'start_date': e.start_date.isoformat() if e.start_date else None,
                'end_date': e.end_date.isoformat() if e.end_date else None, 
                'attempted': has_attempted,
                'has_password': bool(e.password_hash),
                'question_count': question_count,
                'is_visible': e.is_visible,
                'cutoff_type': getattr(e, 'cutoff_type', 'percentage'),
                'cutoff_value': getattr(e, 'cutoff_value', 50.0),
                'description': getattr(e, 'description', None),
                'tags': getattr(e, 'tags', None),
                'slotting_enabled': getattr(e, 'slotting_enabled', False),
                'pooling_enabled': getattr(e, 'pooling_enabled', False),
                'pool_size': getattr(e, 'pool_size', None),
                'questions_per_student': getattr(e, 'questions_per_student', None),
                'randomize_questions': getattr(e, 'randomize_questions', True),
                'assigned_slot': assigned_slot
            })
        
        return JSONResponse(status_code=200, content=exams_list)
    except Exception as e:
        print(f"GET EXAMS ERROR: {e}")
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
            'blueprint_json': exam.blueprint_json,
            'start_date': exam.start_date.isoformat() if exam.start_date else None,
            'end_date': exam.end_date.isoformat() if exam.end_date else None,
            'description': getattr(exam, 'description', ''),
            'tags': getattr(exam, 'tags', ''),
            'cutoff_type': getattr(exam, 'cutoff_type', 'percentage'),
            'cutoff_value': getattr(exam, 'cutoff_value', 50.0),
            'slotting_enabled': getattr(exam, 'slotting_enabled', False),
            'pooling_enabled': getattr(exam, 'pooling_enabled', False),
            'pool_size': getattr(exam, 'pool_size', 0) or 0,
            'questions_per_student': getattr(exam, 'questions_per_student', 0) or 0,
            'randomize_questions': getattr(exam, 'randomize_questions', True)
        })
    except Exception as e:
        print(f"GET DETAILS ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error"})


# --- 🔒 VERIFY EXAM PASSWORD ---
@exam_bp.post('/{exam_id}/verify_password')

def verify_password(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        data = data
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
        print(f"TOGGLE PUBLISH ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error toggling visibility"})



# --- EXAM SETTINGS (PUT) ---
@exam_bp.put('/{exam_id}/settings')
def update_exam_settings(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        exam = db.get(Exam, exam_id)
        if not exam or str(exam.creator_id) != str(current_user.id):
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})

        if 'duration' in data: exam.duration_minutes = int(data['duration'])
        if 'start_date' in data: exam.start_date = datetime.fromisoformat(data['start_date'].replace('Z', ''))
        if 'end_date' in data and data['end_date']: exam.end_date = datetime.fromisoformat(data['end_date'].replace('Z', ''))
        
        if 'cutoff_type' in data: exam.cutoff_type = data['cutoff_type']
        if 'cutoff_value' in data: exam.cutoff_value = float(data['cutoff_value'])
        if 'description' in data: exam.description = data['description']
        if 'tags' in data: exam.tags = data['tags']
        if 'slotting_enabled' in data: exam.slotting_enabled = bool(data['slotting_enabled'])
        if 'pooling_enabled' in data: exam.pooling_enabled = bool(data['pooling_enabled'])
        if 'pool_size' in data: exam.pool_size = int(data['pool_size']) if data['pool_size'] else None
        if 'questions_per_student' in data: exam.questions_per_student = int(data['questions_per_student']) if data['questions_per_student'] else None
        if 'randomize_questions' in data: exam.randomize_questions = bool(data['randomize_questions'])

        db.commit()
        return JSONResponse(status_code=200, content={'message': 'Settings updated successfully'})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# --- SLOTTING API ---
@exam_bp.get('/{exam_id}/slots')
def get_exam_slots(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from models import ExamTimeSlot, StudentExamTimeSlot, User
    try:
        slots = db.query(ExamTimeSlot).filter_by(exam_id=exam_id).all()
        result = []
        for s in slots:
            assigned = db.query(StudentExamTimeSlot).filter_by(slot_id=s.id).count()
            result.append({
                "id": s.id,
                "slot_name": s.slot_name,
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "capacity": s.capacity,
                "assigned_count": assigned
            })
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@exam_bp.post('/{exam_id}/slots')
def create_exam_slot(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None)):
    from models import ExamTimeSlot
    try:
        slot = ExamTimeSlot(
            exam_id=exam_id,
            slot_name=data.get('slot_name', 'Slot'),
            start_time=datetime.fromisoformat(data['start_time'].replace('Z', '')),
            end_time=datetime.fromisoformat(data['end_time'].replace('Z', '')),
            capacity=data.get('capacity')
        )
        db.add(slot)
        db.commit()
        return JSONResponse(status_code=201, content={"message": "Slot created", "id": slot.id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@exam_bp.delete('/{exam_id}/slots/{slot_id}')
def delete_exam_slot(exam_id, slot_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from models import ExamTimeSlot, StudentExamTimeSlot
    try:
        db.query(StudentExamTimeSlot).filter_by(slot_id=slot_id).delete(synchronize_session=False)
        db.query(ExamTimeSlot).filter_by(id=slot_id, exam_id=exam_id).delete(synchronize_session=False)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Slot deleted"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@exam_bp.post('/{exam_id}/slots/auto-assign')
def auto_assign_slots(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from models import ExamTimeSlot, StudentExamTimeSlot, User
    import random
    try:
        slots = db.query(ExamTimeSlot).filter_by(exam_id=exam_id).all()
        if not slots: return JSONResponse(status_code=400, content={"message": "No slots available"})
        
        # Clear existing assignments
        db.query(StudentExamTimeSlot).filter_by(exam_id=exam_id).delete(synchronize_session=False)
        
        # Get all students (simplified: getting all users with role 'student')
        students = db.query(User).filter_by(role='student').all()
        
        assignments = []
        for student in students:
            slot = random.choice(slots)
            assignments.append(StudentExamTimeSlot(exam_id=exam_id, student_id=student.id, slot_id=slot.id))
        
        if assignments:
            db.bulk_save_objects(assignments)
        db.commit()
        return JSONResponse(status_code=200, content={"message": f"Assigned {len(assignments)} students to slots"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

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


# --- 🚨 START EXAM (CREATE ATTEMPT) ---
@exam_bp.post('/{exam_id}/start')

def start_exam(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        exam = db.get(Exam, exam_id)
        if not exam:
            return JSONResponse(status_code=404, content={"message": "Exam not found"})

        if getattr(exam, 'slotting_enabled', False):
            from models import StudentExamTimeSlot, ExamTimeSlot
            assignment = db.query(StudentExamTimeSlot).filter_by(exam_id=exam_id, student_id=user_id).first()
            if not assignment:
                return JSONResponse(status_code=403, content={"message": "You are not assigned to any slot for this exam."})
            slot = db.get(ExamTimeSlot, assignment.slot_id)
            now = datetime.now()
            if now < slot.start_time or now > slot.end_time:
                return JSONResponse(status_code=403, content={"message": f"Your slot is not currently active."})

        # Handle retakes by deleting existing attempts (for MVP purposes)
        existing_attempts = db.query(ExamAttempt).filter_by(exam_id=exam_id, student_id=user_id).all()
        for old_attempt in existing_attempts:
            from models import Answer, ProctoringEvent
            db.query(Answer).filter_by(attempt_id=old_attempt.id).delete(synchronize_session=False)
            db.query(ProctoringEvent).filter_by(attempt_id=old_attempt.id).delete(synchronize_session=False)
            db.delete(old_attempt)
        if existing_attempts:
            db.commit()

        assigned_questions_json = None
        if getattr(exam, 'pooling_enabled', False) or getattr(exam, 'slotting_enabled', False):
            import json, random
            from models import Question
            all_q = db.query(Question).filter_by(exam_id=exam_id, is_archived=False).all()
            
            if getattr(exam, 'pooling_enabled', False) and exam.questions_per_student and exam.questions_per_student < len(all_q):
                selected_q = random.sample(all_q, exam.questions_per_student)
            else:
                selected_q = all_q
                if getattr(exam, 'randomize_questions', True) or getattr(exam, 'slotting_enabled', False):
                    random.shuffle(selected_q)
            assigned_questions_json = json.dumps([q.id for q in selected_q])

        attempt = ExamAttempt(
            exam_id=exam_id,
            student_id=user_id,
            status='IN_PROGRESS',
            assigned_questions_json=assigned_questions_json
        )
        db.add(attempt)
        db.commit()
        return JSONResponse(status_code=201, content=dict(message="Exam started", attempt_id=attempt.id))
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


# --- 🚨 SUBMIT EXAM & RECORD WARNINGS + IMAGES ---
@exam_bp.post('/{exam_id}/submit')

def submit_exam(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        current_user_id = current_user.id
        data = data
        
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
        print(f"SUBMIT ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error submitting exam"})


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
        print(f"GET RESULTS ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error fetching results"})

# --- 🔎 GET PROCTORING EVENTS TIMELINE ---
@exam_bp.get('/{exam_id}/proctoring_events/{student_id}')
def get_proctoring_events(exam_id, student_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user = db.get(User, current_user.id)
        if user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})

        attempt = db.query(ExamAttempt).filter_by(exam_id=exam_id, student_id=student_id).order_by(ExamAttempt.id.desc()).first()
        if not attempt:
            return JSONResponse(status_code=404, content={"message": "No attempt found"})

        events = db.query(ProctoringEvent).filter_by(attempt_id=attempt.id).order_by(ProctoringEvent.timestamp.asc()).all()
        
        event_data = []
        for e in events:
            event_data.append({
                'id': e.id,
                'timestamp': e.timestamp.isoformat() if e.timestamp else None,
                'event_type': e.event_type,
                'severity': e.severity,
                'confidence': e.confidence,
                'duration_ms': e.duration_ms,
                'evidence_url': e.evidence_url
            })
            
        return JSONResponse(status_code=200, content=event_data)
    except Exception as e:
        print(f"GET EVENTS ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error fetching events"})


# --- 📝 GET STUDENT EXAM REVIEW ---
@exam_bp.get('/{exam_id}/review')

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
        print(f"GET EXAM REVIEW ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error fetching exam review"})

# --- 📝 GET STUDENT EXAM REVIEW (FOR TEACHERS) ---
@exam_bp.get('/{exam_id}/review/{student_id}')

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
        print(f"GET EXAM REVIEW FOR TEACHER ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error fetching exam review"})


# ==========================================================
# 🚨 BULLETPROOF AI PROCTORING ENDPOINT (DEVICE-INDEPENDENT)
# ==========================================================
from ai.proctoring.proctoring_core import process_frame_detections

@exam_bp.post('/analyze_frame')
def analyze_frame(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        if not data or 'frame' not in data:
            return JSONResponse(status_code=200, content={"status": "safe", "events": []})
            
        base64_frame = data.get('frame')
        attempt_id = data.get('attempt_id')
        if not base64_frame or not attempt_id:
            return JSONResponse(status_code=200, content={"status": "safe", "events": []})
            
        # Decode Base64 to OpenCV image
        header, encoded = base64_frame.split(",", 1)
        encoded = encoded.strip()
        encoded += "=" * ((4 - len(encoded) % 4) % 4)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return JSONResponse(status_code=200, content={"status": "safe", "events": []})

        high_res_img = img.copy()

        # Resize for Face Detection
        original_height, original_width = img.shape[:2]
        max_width = 640
        if original_width > max_width:
            scale = max_width / original_width
            img = cv2.resize(img, (max_width, int(original_height * scale)))

        height, width, _ = img.shape
        center_x_min = width // 4
        center_x_max = 3 * (width // 4)

        # 🧠 FACE DETECTION
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=4, minSize=(30, 30))

        looking_away = False
        for (x, y, w, h) in faces:
            face_center_x = x + (w // 2)
            if face_center_x < center_x_min or face_center_x > center_x_max:
                looking_away = True

        # 📱 YOLO OBJECT DETECTION (Classes: 63=laptop, 67=cell phone, 73=book)
        objects = []
        if model:
            results = model.predict(high_res_img, classes=[63, 67, 73], conf=0.35, verbose=False)
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls_id == 67:
                        objects.append({"class": "phone", "conf": conf})
                    elif cls_id == 63:
                        objects.append({"class": "laptop", "conf": conf})
                    elif cls_id == 73:
                        objects.append({"class": "book", "conf": conf})

        detections = {
            "face_count": len(faces),
            "looking_away": looking_away,
            "objects": objects
        }

        # Temporal Aggregation
        new_events = process_frame_detections(attempt_id, detections, db, base64_frame)

        # Format events for response
        events_json = []
        for e in new_events:
            events_json.append({
                "type": e.event_type,
                "severity": e.severity,
                "confidence": e.confidence
            })

        # Backward compatibility for status
        current_status = "safe"
        if len(faces) == 0: current_status = "missing"
        elif len(faces) > 1: current_status = "multiple"
        elif looking_away: current_status = "looking_away"
        elif any(obj['class'] == 'phone' for obj in objects): current_status = "phone_detected"
        elif any(obj['class'] == 'book' for obj in objects): current_status = "book_detected"

        return JSONResponse(status_code=200, content={
            "status": current_status,
            "events": events_json,
            "detections": detections
        })
        
    except Exception as e:
        print(f"🚨 CRITICAL AI ERROR: {e}")
        return JSONResponse(status_code=200, content={"status": "safe", "events": []})

# --- 🚀 EXPLICIT PROCTORING EVENT LOGGING ---
from models import ProctoringEvent

@exam_bp.post('/proctoring_event')
def log_proctoring_event(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        if not data or not data.get('attempt_id') or not data.get('event_type'):
            return JSONResponse(status_code=400, content={"message": "Missing required fields"})

        attempt_id = data.get('attempt_id')
        event_type = data.get('event_type')
        severity = data.get('severity', 'LOW')
        duration_ms = data.get('duration_ms', 0)
        
        event = ProctoringEvent(
            attempt_id=attempt_id,
            event_type=event_type,
            severity=severity,
            duration_ms=duration_ms,
            confidence=1.0,
            metadata_json=json.dumps({"source": "browser/audio client"})
        )
        db.add(event)
        db.commit()
        
        return JSONResponse(status_code=200, content={"status": "recorded"})
    except Exception as e:
        print(f"Error logging proctoring event: {e}")
        return JSONResponse(status_code=500, content={"message": "Failed to log event"})

# --- 🧠 AI EVALUATE SUBJECTIVE ANSWERS ---
from ai.evaluation.subjective_evaluator import evaluate_subjective_answer

@exam_bp.post('/{exam_id}/evaluate')

def evaluate_exam_subjective_answers(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        user = db.get(User, user_id)
        if user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        data = data or {}
        use_rag = data.get('use_rag', False)
            
        attempts = db.execute(select(ExamAttempt).filter_by(exam_id=exam_id)).scalars().all()
        attempt_ids = [a.id for a in attempts]
        
        if not attempt_ids:
            return JSONResponse(status_code=200, content={"message": "No attempts to evaluate."})
            
        answers = db.execute(
            select(Answer).join(Question).filter(
                Answer.attempt_id.in_(attempt_ids),
                Question.is_subjective == True
            )
        ).scalars().all()
        
        evaluated_count = 0
        for ans in answers:
            if not ans.ai_explanation: # only evaluate if not already evaluated
                question = db.get(Question, ans.question_id)
                evaluation = evaluate_subjective_answer(
                    question_text=question.text,
                    reference_answer=question.reference_answer,
                    student_answer=ans.answer_text,
                    max_marks=question.max_marks, # --- BUG FIX: Use actual max_marks ---
                    rubric=question.rubric, # --- NEW: Pass rubric ---
                    use_rag=use_rag
                )
                
                ans.ai_suggested_marks = evaluation.get("suggested_marks", 0.0)
                ans.ai_explanation = evaluation.get("explanation", "")
                
                # --- BUG FIX: Safely cast confidence to float ---
                try:
                    ans.ai_confidence = float(evaluation.get("confidence", 1.0))
                except (ValueError, TypeError):
                    ans.ai_confidence = 1.0
                    
                ans.ai_model_name = evaluation.get("model_name", "unknown")
                ans.review_status = evaluation.get("review_status", "COMPLETED")
                
                # --- BUG FIX: The Subjective Grading Blackhole ---
                # marks_awarded defaults to 0.0 on submit, so "is None" was always false.
                # Only overwrite if teacher hasn't manually graded it.
                if not ans.teacher_feedback:
                    ans.marks_awarded = ans.ai_suggested_marks
                    
                evaluated_count += 1
                
        # Re-calculate attempt scores
        for attempt in attempts:
            attempt_answers = db.execute(select(Answer).filter_by(attempt_id=attempt.id)).scalars().all()
            total_score = sum(a.marks_awarded for a in attempt_answers if a.marks_awarded is not None)
            
            result = db.execute(select(Result).filter_by(student_id=attempt.student_id, exam_id=exam_id)).scalars().first()
            if result:
                result.score = total_score
                
        db.commit()
        return JSONResponse(status_code=200, content={"message": f"Evaluated {evaluated_count} answers."})
    except Exception as e:
        print(f"EVALUATE ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error evaluating answers"})

# --- ✍️ TEACHER OVERRIDE GRADE ---
@exam_bp.put('/answers/{answer_id}/grade')

def override_grade(answer_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        user_id = current_user.id
        user = db.get(User, user_id)
        if user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        data = data
        new_marks = data.get('marks') if data.get('marks') is not None else data.get('marks_awarded')
        feedback = data.get('feedback')
        
        ans = db.get(Answer, answer_id)
        if not ans:
            return JSONResponse(status_code=404, content={"message": "Answer not found"})
            
        ans.marks_awarded = float(new_marks)
        if feedback is not None:
            ans.teacher_feedback = feedback
            
        # Update Result score
        attempt = db.get(ExamAttempt, ans.attempt_id)
        attempt_answers = db.execute(select(Answer).filter_by(attempt_id=attempt.id)).scalars().all()
        total_score = sum(a.marks_awarded for a in attempt_answers if a.marks_awarded is not None)
        
        result = db.execute(select(Result).filter_by(student_id=attempt.student_id, exam_id=attempt.exam_id)).scalars().first()
        if result:
            result.score = total_score
            
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Grade updated"})
    except Exception as e:
        print(f"OVERRIDE GRADE ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error overriding grade"})