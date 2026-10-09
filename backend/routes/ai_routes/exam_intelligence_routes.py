import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import Exam, Question, QuestionAiAnalysis, ExamAnalysis, AIJob, User
from database import get_db
from auth_middleware import get_teacher_user
from ai.core.pipeline import analyze_question_qis
from ai.core.qis_persistence import persist_qis_analysis
from ai.question.question_generator import generate_candidate_question
from ai.exam.assessment_assembler import assemble_assessment
import threading

intelligence_bp = APIRouter()

@intelligence_bp.post('/assemble')
def preview_assembly(data: dict = Body(...), db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        topics = data.get("topics", {})
        difficulty = data.get("difficulty_distribution", {})
        count = data.get("question_count", 10)
        exam_type = data.get("exam_type", "Objective")
        bloom = data.get("bloom_distribution", None)
        
        result = assemble_assessment(db, topics, difficulty, count, exam_type, bloom)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@intelligence_bp.post('/{exam_id}/analyze-all', status_code=202)
def analyze_all_questions(exam_id: int, db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        exam = db.get(Exam, exam_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        questions = db.query(Question).filter_by(exam_id=exam_id).all()
        if not questions:
            raise HTTPException(status_code=400, detail="No questions in exam to analyze")
        
        # Create AIJob for tracking
        job = AIJob(
            job_type='BULK_ANALYZE_EXAM',
            target_id=exam_id,
            status='QUEUED',
            total=len(questions)
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Prepare data so thread doesn't need to query questions again
        q_data = [{
            'id': q.id, 'text': q.text, 'correct_option': q.correct_option,
            'option_a': q.option_a, 'option_b': q.option_b, 
            'option_c': q.option_c, 'option_d': q.option_d,
            'exam_id': exam_id
        } for q in questions]
        
        from tasks.qis_tasks import background_analyze_batch
        thread = threading.Thread(
            target=background_analyze_batch,
            args=(job.id, q_data),
            daemon=True
        )
        thread.start()
        
        return {"message": f"Analysis started for {len(questions)} questions.", "job_id": job.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@intelligence_bp.get('/{exam_id}/intelligence-report')
def get_intelligence_report(exam_id: int, db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        exam = db.get(Exam, exam_id)
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
            
        analyses = db.query(QuestionAiAnalysis).join(Question).filter(
            Question.exam_id == exam_id,
            QuestionAiAnalysis.is_current == True
        ).all()
        
        total = len(analyses)
        if total == 0:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=200, content=None)
            
        bloom_counts = {}
        difficulty_counts = {}
        topic_counts = {}
        total_quality = 0.0
        
        for a in analyses:
            if a.bloom_label:
                bloom_counts[a.bloom_label] = bloom_counts.get(a.bloom_label, 0) + 1
            if a.difficulty_label:
                difficulty_counts[a.difficulty_label] = difficulty_counts.get(a.difficulty_label, 0) + 1
            if a.topic_label:
                topic_counts[a.topic_label] = topic_counts.get(a.topic_label, 0) + 1
            total_quality += (a.quality_score or 0.0)
            
        quality_score = total_quality / total if total > 0 else 0
        
        # Calculate duplicate metrics
        high_risk_count = sum(1 for a in analyses if a.duplicate_risk and a.duplicate_risk >= 0.85)
        # Duplicate safety is percentage of questions that are NOT high risk
        duplicate_safety = 100 - ((high_risk_count / total) * 100) if total > 0 else 100
        duplicate_safety = round(duplicate_safety, 1)
        
        # Save to ExamAnalysis
        exam_analysis = db.query(ExamAnalysis).filter_by(exam_id=exam_id).first()
        if not exam_analysis:
            exam_analysis = ExamAnalysis(exam_id=exam_id)
            db.add(exam_analysis)
            
        exam_analysis.total_questions = total
        exam_analysis.quality_score = quality_score
        exam_analysis.bloom_distribution = json.dumps(bloom_counts)
        exam_analysis.difficulty_distribution = json.dumps(difficulty_counts)
        exam_analysis.topic_distribution = json.dumps(topic_counts)
        db.commit()
        
        # Compare with blueprint if it exists
        blueprint = json.loads(exam.blueprint_json) if exam.blueprint_json else None
        
        return {
            "total_questions": total,
            "average_quality": quality_score,
            "duplicate_safety": duplicate_safety,
            "bloom_distribution": bloom_counts,
            "difficulty_distribution": difficulty_counts,
            "topic_distribution": topic_counts,
            "blueprint": blueprint
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@intelligence_bp.post('/{exam_id}/generate-gap-questions')
def generate_gap_questions(exam_id: int, data: dict = Body(...), db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        topic = data.get("topic")
        bloom_level = data.get("bloom_level")
        difficulty = data.get("difficulty")
        use_rag = data.get("use_rag", False)
        
        if not topic or not bloom_level or not difficulty:
            raise HTTPException(status_code=400, detail="Missing required parameters")
            
        rag_context = None
        if use_rag:
            from ai.rag.retriever import retrieve_context
            # Use topic and potentially bloom/difficulty as query
            query = f"{topic} {bloom_level} {difficulty}"
            rag_context = retrieve_context(query=query, top_k=3)
            
        try:
            question_data = generate_candidate_question(topic, bloom_level, difficulty, rag_context)
            if not question_data:
                raise Exception("AI returned empty question data")
        except Exception as ai_e:
            raise HTTPException(status_code=500, detail=str(ai_e))
            
        #  Pass generated questions through QIS analysis before returning
        options = {
            "A": question_data.get("option_a", ""),
            "B": question_data.get("option_b", ""),
            "C": question_data.get("option_c", ""),
            "D": question_data.get("option_d", "")
        }
        
        qis_res = analyze_question_qis(
            question_text=question_data.get("text", ""),
            options=options,
            correct_option=question_data.get("correct_option")
        )
        
        # Attach the QIS analysis payload to the generated candidate question for frontend review
        question_data["ai_analysis"] = qis_res
            
        return question_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@intelligence_bp.post('/generate-standalone')
def generate_standalone(data: dict = Body(...), db: Session = Depends(get_db), teacher: User = Depends(get_teacher_user)):
    try:
        topic = data.get("topic")
        bloom_level = data.get("bloom_level")
        difficulty = data.get("difficulty")
        use_rag = data.get("use_rag", False)
        document_id = data.get("document_id")
        avoid_texts = data.get("avoid_texts", [])
        
        if not topic or not bloom_level or not difficulty:
            raise HTTPException(status_code=400, detail="Missing required parameters")
            
        rag_context = None
        if use_rag:
            from ai.rag.retriever import retrieve_context
            query = f"{topic} {bloom_level} {difficulty}"
            rag_context = retrieve_context(query=query, top_k=3, document_id=document_id)
            
        try:
            question_data = generate_candidate_question(topic, bloom_level, difficulty, rag_context, avoid_texts)
            if not question_data:
                raise Exception("AI returned empty question data")
        except Exception as ai_e:
            raise HTTPException(status_code=500, detail=str(ai_e))
            
        options = {
            "A": question_data.get("option_a", ""),
            "B": question_data.get("option_b", ""),
            "C": question_data.get("option_c", ""),
            "D": question_data.get("option_d", "")
        }
        
        qis_res = analyze_question_qis(
            question_text=question_data.get("text", ""),
            options=options,
            correct_option=question_data.get("correct_option")
        )
        
        question_data["ai_analysis"] = qis_res
            
        return question_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
