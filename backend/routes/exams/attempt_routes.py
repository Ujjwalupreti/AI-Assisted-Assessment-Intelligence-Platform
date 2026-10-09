from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import Result, User
from database import get_db
from auth_middleware import get_current_user

attempt_bp = APIRouter()

@attempt_bp.get('/my_attempts')
def get_my_attempts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    student_id = current_user.id
    results = db.query(Result.exam_id).filter_by(student_id=student_id).all()
    return [r[0] for r in results]