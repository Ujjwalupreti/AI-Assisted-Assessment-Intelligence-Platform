import os
import sys
import json

# Append backend path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
app = create_app()
from models import Question, QuestionAiAnalysis
from ai.pipeline import analyze_question_qis
from ai.qis_persistence import persist_qis_analysis

def test_analyze_all():
    with app.app_context():
        exam_id = 1
        questions = Question.query.filter_by(exam_id=exam_id).all()
        print(f"Found {len(questions)} questions")
        
        # Retain historical analysis instead of deleting previous entries
        
        analyzed_count = 0
        for q in questions:
            options = {
                "A": q.option_a or "",
                "B": q.option_b or "",
                "C": q.option_c or "",
                "D": q.option_d or ""
            }
            res = analyze_question_qis(
                question_text=q.text,
                options=options,
                correct_option=q.correct_option
            )
            
            persist_qis_analysis(q.id, res)
            analyzed_count += 1
            print(f"Analyzed {q.id}")
            
        db.commit()
        print(f"Analyzed {analyzed_count} questions successfully.")

if __name__ == "__main__":
    test_analyze_all()
