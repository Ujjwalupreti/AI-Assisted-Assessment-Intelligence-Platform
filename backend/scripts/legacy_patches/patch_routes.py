import re

with open('routes/main_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_routes = """
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
    from models import ExamSlot, StudentExamSlot, User
    try:
        slots = db.query(ExamSlot).filter_by(exam_id=exam_id).all()
        result = []
        for s in slots:
            assigned = db.query(StudentExamSlot).filter_by(slot_id=s.id).count()
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
    from models import ExamSlot
    try:
        slot = ExamSlot(
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
    from models import ExamSlot, StudentExamSlot
    try:
        db.query(StudentExamSlot).filter_by(slot_id=slot_id).delete(synchronize_session=False)
        db.query(ExamSlot).filter_by(id=slot_id, exam_id=exam_id).delete(synchronize_session=False)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Slot deleted"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@exam_bp.post('/{exam_id}/slots/auto-assign')
def auto_assign_slots(exam_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from models import ExamSlot, StudentExamSlot, User
    import random
    try:
        slots = db.query(ExamSlot).filter_by(exam_id=exam_id).all()
        if not slots: return JSONResponse(status_code=400, content={"message": "No slots available"})
        
        # Clear existing assignments
        db.query(StudentExamSlot).filter_by(exam_id=exam_id).delete(synchronize_session=False)
        
        # Get all students (simplified: getting all users with role 'student')
        students = db.query(User).filter_by(role='student').all()
        
        assignments = []
        for student in students:
            slot = random.choice(slots)
            assignments.append(StudentExamSlot(exam_id=exam_id, student_id=student.id, slot_id=slot.id))
        
        if assignments:
            db.bulk_save_objects(assignments)
        db.commit()
        return JSONResponse(status_code=200, content={"message": f"Assigned {len(assignments)} students to slots"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# --- DELETE EXAM ---
"""

content = content.replace("# --- DELETE EXAM ---", new_routes)

with open('routes/main_routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
