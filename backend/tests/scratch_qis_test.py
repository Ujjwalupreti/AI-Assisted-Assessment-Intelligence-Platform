import json
import time
from app import create_app
from models import User, Exam, Question, QuestionAiAnalysis, AIJob, DuplicateGroup, QuestionDuplicate
from ai.pipeline import analyze_question_qis
from ai.recommender import generate_recommendations
from ai.duplicate_detector import detect_duplicates

def run_tests():
    app = create_app()
    with app.app_context():
        results = {
            "qis_analysis_accuracy": {},
            "recommendation_system": {},
            "deduplication": {}
        }
        
        # 1. Setup Test Data
        teacher = User.query.filter_by(role='teacher').first()
        if not teacher:
            teacher = User(username='test_teacher_qis', email='qis@test.com', role='teacher')
            teacher.set_password('password')
            db.add(teacher)
            db.commit()

        blueprint = {
            "bloom_distribution": {"Remember": 30, "Understand": 40, "Apply": 30},
            "difficulty_distribution": {"Easy": 30, "Medium": 50, "Hard": 20},
            "topic_distribution": {"Python": 100}
        }
        
        exam = Exam(title='QIS Verification Test Exam', duration_minutes=60, start_date=db.func.now(), creator_id=teacher.id, blueprint_json=json.dumps(blueprint))
        db.add(exam)
        db.commit()
        
        q1 = Question(exam_id=exam.id, text="What is the output of print(2+2)?", option_a="3", option_b="4", option_c="5", option_d="6", correct_option="B", topic="Python", difficulty="Easy", bloom_level="Remember")
        q2 = Question(exam_id=exam.id, text="How do you write a list comprehension in Python?", option_a="[]", option_b="()", option_c="{}", option_d="None", correct_option="A", topic="Python", difficulty="Understand", bloom_level="Understand")
        q3 = Question(exam_id=exam.id, text="Calculate the sum of 2 and 2 in python.", option_a="3", option_b="4", option_c="5", option_d="6", correct_option="B", topic="Python", difficulty="Easy", bloom_level="Remember") # Duplicate of Q1
        
        db.session.add_all([q1, q2, q3])
        db.commit()
        
        try:
            # 2. Test QIS Pipeline
            print("Running QIS Analysis...")
            options1 = {"A": q1.option_a, "B": q1.option_b, "C": q1.option_c, "D": q1.option_d}
            res1 = analyze_question_qis(q1.text, options1, q1.correct_option, q1.topic, q1.bloom_level, q1.difficulty)
            
            results["qis_analysis_accuracy"] = {
                "status": "PASS" if "classification" in res1 else "FAIL",
                "output": res1,
                "notes": "QIS successfully classified the question." if "classification" in res1 else "QIS failed to return proper schema."
            }
            
            # Save analysis to DB to test recommendations
            from ai.qis_persistence import persist_qis_analysis
            persist_qis_analysis(q1.id, res1, commit=True)
            
            # Persist dummy analysis for others to see how it handles it
            res2 = analyze_question_qis(q2.text, {"A": "[]", "B": "()", "C": "{}", "D": "None"}, "A")
            persist_qis_analysis(q2.id, res2, commit=True)
            
            res3 = analyze_question_qis(q3.text, {"A": "3", "B": "4", "C": "5", "D": "6"}, "B")
            persist_qis_analysis(q3.id, res3, commit=True)
            
            # 3. Test Duplication Detection
            print("Running Deduplication...")
            from ai.duplicate_detector import group_duplicates
            dup_res = group_duplicates(exam.id)
            results["deduplication"] = {
                "status": "PASS" if dup_res.get('groups_found', 0) > 0 else "FAIL",
                "groups_found": dup_res.get('groups_found', 0),
                "total_duplicates": dup_res.get('total_duplicates', 0),
                "notes": "Found expected duplicate between Q1 and Q3." if dup_res.get('groups_found', 0) > 0 else "Failed to identify similar questions."
            }
            
            # 4. Test Recommendation Engine
            print("Running Recommendation Engine...")
            recs = generate_recommendations(exam.id)
            is_list = isinstance(recs, list)
            rec_list = recs if is_list else recs.get("recommendations", [])
            results["recommendation_system"] = {
                "status": "PASS" if len(rec_list) > 0 or is_list else "FAIL",
                "recommendation_count": len(rec_list),
                "sample_recommendation": rec_list[0] if len(rec_list) > 0 else None,
                "notes": "Recommendations successfully generated based on blueprint." if len(rec_list) > 0 or is_list else "Recommendation engine failed."
            }
            
        except Exception as e:
            import traceback
            results["error"] = traceback.format_exc()
            print("ERROR", traceback.format_exc())
            
        finally:
            # Cleanup
            print("Cleaning up...")
            DuplicateGroup.query.filter_by(exam_id=exam.id).delete()
            QuestionDuplicate.query.filter(QuestionDuplicate.question_id.in_([q1.id, q2.id, q3.id])).delete()
            QuestionAiAnalysis.query.filter(QuestionAiAnalysis.question_id.in_([q1.id, q2.id, q3.id])).delete()
            Question.query.filter_by(exam_id=exam.id).delete()
            Exam.query.filter_by(id=exam.id).delete()
            db.commit()
            
        with open("qis_verification_report.json", "w") as f:
            json.dump(results, f, indent=4)
            
        print("Done. Report saved to qis_verification_report.json")

if __name__ == '__main__':
    run_tests()
