import os
import sys
import pytest
from unittest.mock import patch
from datetime import datetime

# Append backend path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import Question, QuestionAiAnalysis, Exam, User
from ai.mcq_validator import normalize_option, validate_mcq
from ai.pipeline import analyze_question_qis
from ai.qis_persistence import persist_qis_analysis

def test_mcq_validator_normalization():
    assert normalize_option("A. Apple ") == "apple"
    assert normalize_option("b) Banana.") == "banana"
    assert normalize_option("  1. Cherry  ") == "cherry"
    assert normalize_option("D. ") == ""

    # Test duplication detection
    res = validate_mcq("Which?", {"A": "Apple", "B": " apple.", "C": "Orange"})
    assert res["valid"] == False
    assert any(iss["type"] == "duplicate_options" for iss in res["issues"])

@patch('ai.pipeline.generate_json', return_value=None)
def test_pipeline_llm_failure(mock_generate_json):
    # Simulate LLM failure returning None
    res = analyze_question_qis("What is 2+2?", options={"A": "4", "B": "5"})
    
    # Assert ML pipeline worked
    assert res["classification"]["question_type"]["label"] == "MCQ"
    
    # Assert LLM Fallback
    assert res["quality"]["status"] == "AI_UNAVAILABLE"
    assert res["quality"]["overall_score"] is None
    assert res["review_required"] == True
    assert "LLM quality analysis unavailable" in res["explanations"]["quality"]

def test_persist_qis_analysis():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    
    with app.app_context():
        # Setup mock db
        db.create_all()
        
        # We need a dummy user and exam to satisfy foreign keys
        u = User(username="test", email="test@test.com")
        db.add(u)
        db.commit()
        
        e = Exam(title="Test", duration_minutes=10, start_date=datetime.utcnow(), creator_id=u.id) 
        db.add(e)
        db.commit()
        
        q = Question(exam_id=e.id, text="EncryptedMock")
        db.add(q)
        db.commit()
        
        res = {
            "classification": {
                "question_type": {"label": "MCQ", "confidence": 0.9},
                "topic": {"label": "Math", "confidence": 0.9},
                "bloom": {"label": "Understand", "confidence": 0.9},
                "difficulty": {"label": "Easy", "confidence": 0.9}
            },
            "quality": {
                "overall_score": 0.9,
                "status": "GOOD"
            },
            "duplicate": {"risk": 0.1},
            "model_metadata": {"model_name": "test", "model_version": "1.0", "analysis_method": "hybrid"}
        }
        
        analysis = persist_qis_analysis(q.id, res)
        db.commit()
        
        saved_q = db.session.get(Question, q.id)
        assert saved_q.topic == "Math"
        assert saved_q.difficulty == "Easy"
        assert saved_q.bloom_level == "Understand"
        assert saved_q.ai_quality_score == 0.9
        assert saved_q.is_subjective == False
        
        saved_analysis = QuestionAiAnalysis.query.filter_by(question_id=q.id).first()
        assert saved_analysis.topic == "Math"
        assert saved_analysis.teacher_review_status == "PENDING"
        assert saved_analysis.ai_analysis_json is not None
        
        db.session.remove()
        db.drop_all()
