from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Question, Answer, Exam, Result, User
from database import get_db
from auth_middleware import get_current_user, get_teacher_user
import json

analytics_bp = APIRouter()

# ---  1. QUESTION ANALYTICS (EMPIRICAL DIFFICULTY) ---
@analytics_bp.get('/questions/{question_id}')
def question_analytics(question_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Computes real-time empirical difficulty and discrimination for a specific question.
    """
    try:
        question = db.get(Question, question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
            
        # Get all answers for this question
        answers = db.query(Answer).filter_by(question_id=question_id).all()
        
        attempt_count = len(answers)
        if attempt_count == 0:
            return {
                "message": "No attempts yet",
                "predicted_difficulty": question.difficulty,
                "empirical_difficulty_percentage": None
            }
            
        # Calculate how many were correct (or received full marks for subjective)
        correct_count = 0
        for ans in answers:
            if ans.is_correct or (ans.marks_awarded is not None and ans.marks_awarded >= question.max_marks * 0.9):
                correct_count += 1
                
        empirical_difficulty_percentage = (correct_count / attempt_count) * 100
        
        # Categorize empirical difficulty
        if empirical_difficulty_percentage >= 70:
            empirical_category = "Easy"
        elif empirical_difficulty_percentage >= 40:
            empirical_category = "Medium"
        else:
            empirical_category = "Hard"
            
        return {
            "question_id": question.id,
            "attempt_count": attempt_count,
            "correct_count": correct_count,
            "empirical_difficulty_percentage": round(empirical_difficulty_percentage, 2),
            "empirical_category": empirical_category,
            "predicted_difficulty": question.difficulty,
            "bloom_level": question.bloom_level
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


# ---  2. EXAM BLUEPRINT ANALYTICS ---
@analytics_bp.get('/exams/{exam_id}/blueprint')
def exam_blueprint_analytics(exam_id: int, db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    """
    Compares the actual distribution of questions against the teacher's defined blueprint.
    """
    try:
        exam = db.get(Exam, exam_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
            
        questions = db.query(Question).filter_by(exam_id=exam_id).all()
        total_q = len(questions)
        
        if total_q == 0:
            return {"message": "No questions in exam"}
            
        # Calculate actual distributions
        actual_bloom = {}
        actual_difficulty = {}
        actual_topic = {}
        
        for q in questions:
            bloom = q.bloom_level or "Uncategorized"
            diff = q.difficulty or "Uncategorized"
            topic = q.topic or "Uncategorized"
            
            actual_bloom[bloom] = actual_bloom.get(bloom, 0) + 1
            actual_difficulty[diff] = actual_difficulty.get(diff, 0) + 1
            actual_topic[topic] = actual_topic.get(topic, 0) + 1
            
        # Convert to percentages
        actual_bloom_pct = {k: round((v / total_q) * 100, 1) for k, v in actual_bloom.items()}
        actual_diff_pct = {k: round((v / total_q) * 100, 1) for k, v in actual_difficulty.items()}
        
        blueprint = {}
        if exam.blueprint_json:
            try:
                blueprint = json.loads(exam.blueprint_json)
            except:
                pass
                
        return {
            "exam_id": exam.id,
            "total_questions": total_q,
            "distributions": {
                "bloom": actual_bloom_pct,
                "difficulty": actual_diff_pct,
                "topic_counts": actual_topic
            },
            "blueprint_target": blueprint
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")
