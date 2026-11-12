from app import create_app, db
from models import ExamAttempt, Result, Answer

app = create_app()
with app.app_context():
    attempts = ExamAttempt.query.all()
    deleted = 0
    for a in attempts:
        r = Result.query.filter_by(exam_id=a.exam_id, student_id=a.student_id).first()
        if not r:
            db.query(Answer).filter_by(attempt_id=a.id).delete()
            db.delete(a)
            deleted += 1
    db.commit()
    print(f'Deleted {deleted} orphaned attempts.')
