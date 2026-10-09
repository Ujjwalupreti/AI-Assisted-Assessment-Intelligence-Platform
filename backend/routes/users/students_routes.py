from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import User
from database import get_db
from auth_middleware import get_teacher_user

student_bp = APIRouter()

@student_bp.post('/bulk_add')
def bulk_add_students(data: dict = Body(...), db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        students_list = data.get('students', [])
        
        added_count = 0
        errors = []

        import logging; logging.info(f"---  BULK ADDING {len(students_list)} STUDENTS ---")

        for s in students_list:
            username = s.get('username')
            password = s.get('password')
            enrollment_id = s.get('enrollment_id')
            if enrollment_id and str(enrollment_id).strip():
                enrollment_id = str(enrollment_id).strip()
            else:
                enrollment_id = None
            
            if not username or not password:
                continue

            # Check if user exists
            if db.query(User).filter_by(username=username).first():
                errors.append(f"User '{username}' skipped (Exists)")
                continue

            # Create User
            email = f"{username}@student.com"
            new_user = User(username=username, email=email, enrollment_id=enrollment_id, role='student')
            new_user.set_password(password)
            db.add(new_user)
            added_count += 1

        db.commit()
        return {"message": f"Added {added_count} students.", "errors": errors}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@student_bp.get('/list')
def list_students(db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        students = db.query(User).filter_by(role='student', is_active=True).all()
        return [{
            'id': s.id, 'username': s.username, 'enrollment_id': s.enrollment_id
        } for s in students]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error")
    
# --- DELETE STUDENT ---
@student_bp.delete('/{user_id}')
def delete_student(user_id: int, db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        # Find user
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Soft Delete
        user.is_active = False
        db.commit()
        
        return {"message": "Student deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")