from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import User, Exam, Result
from database import get_db
from auth_middleware import get_admin_user

admin_bp = APIRouter()

# --- 1. GET ALL USERS ---
@admin_bp.get('/users')
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    try:
        users = db.query(User).all()
        return [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role,
            'enrollment_id': u.enrollment_id
        } for u in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. CREATE USER (Any Role) ---
@admin_bp.post('/users', status_code=201)
def create_user(data: dict = Body(...), db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    try:
        username = data.get('username', '').strip().lower()
        password = data.get('password')
        role = data.get('role', 'student') # Default to student
        
        enrollment_id = data.get('enrollment_id')
        if enrollment_id and str(enrollment_id).strip():
            enrollment_id = str(enrollment_id).strip()
        else:
            enrollment_id = None

        # Checks
        if db.query(User).filter_by(username=username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        if enrollment_id and db.query(User).filter_by(enrollment_id=enrollment_id).first():
            raise HTTPException(status_code=400, detail="Enrollment ID already exists")

        # Create
        new_user = User(
            username=username,
            email=f"{username}@exam.com", # Auto-generate email
            role=role,
            enrollment_id=enrollment_id
        )
        new_user.set_password(password)
        db.add(new_user)
        db.commit()
        
        return {"message": "User created successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. DELETE USER ---
@admin_bp.delete('/users/{user_id}')
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    try:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Prevent deleting yourself (Security)
        if admin.id == user_id:
            raise HTTPException(status_code=403, detail="Cannot delete yourself")

        db.delete(user)
        db.commit()
        return {"message": "User deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. SYSTEM STATS ---
@admin_bp.get('/stats')
def get_stats(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    try:
        total_users = db.query(User).count()
        total_exams = db.query(Exam).count()
        total_results = db.query(Result).count()
        
        return {
            "users": total_users,
            "exams": total_exams,
            "results": total_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving stats")