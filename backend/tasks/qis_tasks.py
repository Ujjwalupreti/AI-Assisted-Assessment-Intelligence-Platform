"""
QIS Background Tasks.

Extracts the background analysis thread logic.
Adds proper job tracking and percentage updates.
"""
import traceback
from models import AIJob, Question
from database import SessionLocal
from ai.core.pipeline import analyze_question_qis
from ai.core.qis_persistence import persist_qis_analysis

def background_analyze_batch(job_id, questions_data):
    """
    Run QIS analysis on a batch of questions in a background thread.
    Updates AIJob progress.
    """
    db = SessionLocal()
    try:
        job = db.get(AIJob, job_id)
        if not job:
            return

        try:
            job.status = 'IN_PROGRESS'
            db.commit()

            total = len(questions_data)
            completed = 0
            
            # Fetch all existing questions once to pass for duplicate detection
            existing_questions = []
            if total > 0 and 'exam_id' in questions_data[0]:
                exam_id = questions_data[0]['exam_id']
                qs = db.query(Question).filter_by(exam_id=exam_id).all()
                existing_questions = [{"id": q.id, "text": q.text} for q in qs if not q.text.startswith("U2F")]

            for q_data in questions_data:
                q_id = q_data['id']
                q_text = q_data.get('text', '')
                
                # Re-check ciphertext just in case, though pipeline handles it
                if not q_text or q_text.startswith("U2F"):
                    completed += 1
                    job.completed = completed
                    db.commit()
                    continue

                options = {}
                for opt in ['A', 'B', 'C', 'D']:
                    opt_val = q_data.get(f'option_{opt.lower()}')
                    if opt_val:
                        options[opt] = opt_val

                # Run analysis
                try:
                    qis_metadata = analyze_question_qis(
                        question_text=q_text,
                        options=options,
                        correct_option=q_data.get('correct_option'),
                        existing_questions=existing_questions
                    )

                    # Persist results
                    persist_qis_analysis(db, q_id, qis_metadata)
                except Exception as e:
                    print(f"[qis_tasks] Error analyzing question {q_id}: {e}")

                completed += 1
                job.completed = completed
                
                # We'll just rely on completed / total
                if completed % 5 == 0 or completed == total:
                    db.commit()

            job.status = 'COMPLETED'
            db.commit()

        except Exception as e:
            print(f"[qis_tasks] Job {job_id} failed: {e}")
            traceback.print_exc()
            job.status = 'FAILED'
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()
