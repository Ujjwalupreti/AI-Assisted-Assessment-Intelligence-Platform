from fastapi import APIRouter, Depends, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from auth_middleware import get_current_user
from models import User, Exam, Question
import json

question_bp = APIRouter()

@question_bp.get('/{exam_id}/questions')
def get_questions(exam_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        exam = db.get(Exam, exam_id)
        if not exam:
            return JSONResponse(status_code=404, content={"message": "Exam not found"})
        
        # In a real scenario, we might want to hide the correct_option from students, but for simplicity:
        questions = db.execute(select(Question).filter_by(exam_id=exam_id)).scalars().all()
        q_list = []
        for q in questions:
            q_list.append({
                'id': q.id,
                'text': q.text,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_option': q.correct_option,
                'is_subjective': q.is_subjective,
                'question_type': q.question_type,
                'reference_answer': q.reference_answer,
                'topic': q.topic,
                'difficulty': q.difficulty,
                'bloom_level': q.bloom_level,
                'max_marks': q.max_marks
            })
        return JSONResponse(status_code=200, content=q_list)
    except Exception as e:
        print(f"Error fetching questions: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})


@question_bp.post('/{exam_id}/questions')
def add_question(exam_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(...)):
    try:
        if current_user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        question_type = data.get('question_type', 'MCQ').upper()
        if question_type not in ['MCQ', 'SUBJECTIVE']:
            question_type = 'MCQ'
            
        is_subjective = (question_type == 'SUBJECTIVE')
        reference_answer = data.get('reference_answer')
        
        if is_subjective and (not reference_answer or str(reference_answer).strip() == '' or str(reference_answer).strip().lower() == 'none'):
            return JSONResponse(status_code=400, content={"message": "Reference answer is required for subjective questions."})
            
        max_marks = float(data.get('max_marks', data.get('marks', 1.0)))
        if max_marks <= 0:
            return JSONResponse(status_code=400, content={"message": "Marks must be greater than 0."})
            
        new_q = Question(
            exam_id=exam_id,
            text=data.get('text', ''),
            option_a=data.get('option_a'),
            option_b=data.get('option_b'),
            option_c=data.get('option_c'),
            option_d=data.get('option_d'),
            correct_option=data.get('correct_option_hash', data.get('correct_option')),
            is_subjective=is_subjective,
            question_type=question_type,
            reference_answer=reference_answer,
            topic=data.get('topic'),
            difficulty=data.get('difficulty'),
            bloom_level=data.get('bloom_level'),
            max_marks=max_marks
        )
        db.add(new_q)
        db.commit()
        return JSONResponse(status_code=201, content={"message": "Question added", "id": new_q.id})
    except Exception as e:
        print(f"Error adding question: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})


@question_bp.put('/question/{question_id}')
def update_question(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(...)):
    try:
        if current_user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        q = db.get(Question, question_id)
        if not q:
            return JSONResponse(status_code=404, content={"message": "Question not found"})
            
        q.text = data.get('text', q.text)
        q.option_a = data.get('option_a', q.option_a)
        q.option_b = data.get('option_b', q.option_b)
        q.option_c = data.get('option_c', q.option_c)
        q.option_d = data.get('option_d', q.option_d)
        q.correct_option = data.get('correct_option_hash', data.get('correct_option', q.correct_option))
        
        if 'question_type' in data or 'is_subjective' in data:
            if 'question_type' in data:
                q.question_type = str(data.get('question_type')).upper()
            elif 'is_subjective' in data:
                q.question_type = 'SUBJECTIVE' if data.get('is_subjective') else 'MCQ'
                
            q.is_subjective = (q.question_type == 'SUBJECTIVE')
            
        if 'reference_answer' in data:
            q.reference_answer = data.get('reference_answer')
            
        if q.is_subjective and (not q.reference_answer or str(q.reference_answer).strip() == '' or str(q.reference_answer).strip().lower() == 'none'):
            return JSONResponse(status_code=400, content={"message": "Reference answer is required for subjective questions."})
            
        q.topic = data.get('topic', q.topic)
        q.difficulty = data.get('difficulty', q.difficulty)
        q.bloom_level = data.get('bloom_level', q.bloom_level)
        
        if 'max_marks' in data or 'marks' in data:
            marks = float(data.get('max_marks', data.get('marks', q.max_marks)))
            if marks <= 0:
                return JSONResponse(status_code=400, content={"message": "Marks must be greater than 0."})
            q.max_marks = marks

        
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Question updated"})
    except Exception as e:
        print(f"Error updating question: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})


@question_bp.delete('/question/{question_id}')
def delete_question(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if current_user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        q = db.get(Question, question_id)
        if not q:
            return JSONResponse(status_code=404, content={"message": "Question not found"})
            
        db.delete(q)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Question deleted"})
    except Exception as e:
        print(f"Error deleting question: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})


@question_bp.post('/{exam_id}/bulk_questions')
def bulk_add_questions(exam_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(...)):
    try:
        if current_user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        questions_list = data.get('questions', [])
        for row in questions_list:
            question_type = str(row.get('question_type', 'MCQ')).upper()
            if question_type not in ['MCQ', 'SUBJECTIVE']:
                question_type = 'SUBJECTIVE' if (str(row.get('is_subjective', '')).lower() in ['true', '1']) else 'MCQ'
                
            is_subjective = (question_type == 'SUBJECTIVE')
            reference_answer = row.get('reference_answer')
            
            if is_subjective and (not reference_answer or str(reference_answer).strip() == '' or str(reference_answer).strip().lower() == 'none'):
                # Skip invalid subjective questions silently for bulk add or raise? We'll raise to be safe.
                return JSONResponse(status_code=400, content={"message": f"Reference answer is required for subjective question: '{row.get('text', '')[:20]}...'"})
            
            try:
                max_marks = float(row.get('max_marks', row.get('marks', 1.0)))
            except:
                max_marks = 1.0
                
            if max_marks <= 0:
                max_marks = 1.0
                
            new_q = Question(
                exam_id=exam_id,
                text=row.get('text', ''),
                option_a=row.get('option_a'),
                option_b=row.get('option_b'),
                option_c=row.get('option_c'),
                option_d=row.get('option_d'),
                correct_option=row.get('correct_option_hash', row.get('correct_option')),
                is_subjective=is_subjective,
                question_type=question_type,
                reference_answer=reference_answer,
                topic=row.get('topic'),
                difficulty=row.get('difficulty'),
                bloom_level=row.get('bloom_level'),
                max_marks=max_marks
            )
            db.add(new_q)
        db.commit()
        return JSONResponse(status_code=201, content={"message": f"{len(questions_list)} questions added"})
    except Exception as e:
        print(f"Error bulk adding: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})


@question_bp.get('/bank')
def get_question_bank(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if current_user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        # Simplistic bank: returns all questions from all exams created by this teacher
        exams = db.execute(select(Exam).filter_by(creator_id=current_user.id)).scalars().all()
        exam_ids = [e.id for e in exams]
        
        if not exam_ids:
            return JSONResponse(status_code=200, content=[])
            
        questions = db.execute(select(Question).filter(Question.exam_id.in_(exam_ids))).scalars().all()
        q_list = []
        for q in questions:
            q_list.append({
                'id': q.id,
                'exam_id': q.exam_id,
                'text': q.text,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_option': q.correct_option,
                'is_subjective': q.is_subjective,
                'topic': q.topic,
                'difficulty': q.difficulty,
                'bloom_level': q.bloom_level
            })
        return JSONResponse(status_code=200, content=q_list)
    except Exception as e:
        print(f"Error fetching bank: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})


@question_bp.post('/{exam_id}/clone_from_bank')
def clone_from_bank(exam_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(...)):
    try:
        if current_user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})
            
        question_id = data.get('question_id')
        q = db.get(Question, question_id)
        if not q:
            return JSONResponse(status_code=404, content={"message": "Question not found"})
            
        # Clone it
        new_q = Question(
            exam_id=exam_id,
            text=q.text,
            option_a=q.option_a,
            option_b=q.option_b,
            option_c=q.option_c,
            option_d=q.option_d,
            correct_option=q.correct_option,
            is_subjective=q.is_subjective,
            topic=q.topic,
            difficulty=q.difficulty,
            bloom_level=q.bloom_level,
            max_marks=q.max_marks
        )
        db.add(new_q)
        db.commit()
        return JSONResponse(status_code=201, content={"message": "Cloned successfully", "new_id": new_q.id})
    except Exception as e:
        print(f"Error cloning question: {e}")
        return JSONResponse(status_code=500, content={"message": "Internal server error"})

