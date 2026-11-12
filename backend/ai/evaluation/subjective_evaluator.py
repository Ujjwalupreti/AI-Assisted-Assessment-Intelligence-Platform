import re
import json
from ai.core.llm_client import generate_json

def evaluate_subjective_answer(question_text, reference_answer, student_answer, max_marks=1.0, rubric=None, use_rag=False, course_name=None):
    """
    Evaluates a subjective answer using LLM grading with rubrics, confidence scoring, and optional RAG grounding.
    """
    if not student_answer or str(student_answer).strip() == "":
        return {
            "suggested_marks": 0.0,
            "explanation": "No answer provided by the student.",
            "confidence": 1.0,
            "model_name": "system",
            "review_status": "COMPLETED"
        }

    try:
        context_instruction = ""
        if use_rag:
            from ai.rag.retriever import retrieve_context
            # Use the question text as the query to find relevant syllabus info
            rag_context = retrieve_context(query=question_text, top_k=2)
            if rag_context:
                context_instruction = f"""
                --- KNOWLEDGE BASE CONTEXT ---
                Use the following context from the course syllabus to help determine the factual correctness of the student's answer:
                {rag_context}
                ------------------------------
                """

        prompt = f"""
        You are an expert AI grader. Evaluate the student's answer based on the reference answer and rubric.
        
        Question: {question_text}
        Reference Answer (Ideal): {reference_answer}
        Rubric (Strict constraints): {rubric if rubric else 'None provided. Evaluate primarily on Reference Answer.'}
        
        {context_instruction}
        
        Student Answer: {student_answer}
        Maximum Marks: {max_marks}
        
        Evaluate the answer strictly but fairly. Extract concepts from the student's answer and match them to the rubric/reference. Award partial marks appropriately.
        
        Return ONLY a JSON object with EXACTLY these keys:
        {{
            "suggested_marks": (float between 0 and {max_marks}),
            "explanation": "string explaining why these marks were awarded, pointing out missing or correct concepts according to the rubric",
            "confidence": (float between 0.0 and 1.0 representing your confidence in this grade. Use < 0.70 if the answer is highly ambiguous or hard to grade.)
        }}
        """
        
        data = generate_json(prompt, temperature=0.2)
        if data:
            # Enforce bounds
            marks = float(data.get('suggested_marks', 0.0))
            data['suggested_marks'] = max(0.0, min(marks, max_marks))
            data['model_name'] = 'gemini-1.5-flash-via-client'
            
            conf = float(data.get('confidence', 1.0))
            data['review_status'] = 'NEEDS_REVIEW' if conf < 0.70 else 'COMPLETED'
            return data
            
    except Exception as e:
        print(f"AI Grading Error: {e}")
        # fallback to simulation below
            
    # Fallback Tier 1: Local Dense Semantic Vector Model (SentenceTransformers all-MiniLM-L6-v2)
    if not reference_answer or str(reference_answer).strip() == "":
        return {
            "suggested_marks": 0.0,
            "explanation": "No reference answer provided by teacher. Requires manual grading.",
            "confidence": 0.0,
            "model_name": "manual_review_required",
            "review_status": "NEEDS_REVIEW"
        }

    try:
        from ai.generation.duplicate_detector import _get_st_model
        import torch
        from sentence_transformers import util

        st_model = _get_st_model()
        if st_model is not None:
            # 1. Holistic Semantic Similarity
            ref_emb = st_model.encode(str(reference_answer), convert_to_tensor=True)
            stu_emb = st_model.encode(str(student_answer), convert_to_tensor=True)
            cos_sim = float(util.cos_sim(stu_emb, ref_emb)[0][0])
            cos_sim = max(0.0, min(1.0, cos_sim))

            # 2. Rubric Concept Coverage (if rubric provided)
            rubric_coverage = cos_sim
            if rubric and str(rubric).strip():
                rubric_lines = [r.strip() for r in str(rubric).split("\n") if len(r.strip()) > 5]
                if rubric_lines:
                    # Break student answer into sentence clauses
                    student_clauses = [s.strip() for s in re.split(r'[.!?\n]', str(student_answer)) if len(s.strip()) > 5]
                    if not student_clauses:
                        student_clauses = [str(student_answer)]
                    
                    clause_embs = st_model.encode(student_clauses, convert_to_tensor=True)
                    rubric_embs = st_model.encode(rubric_lines, convert_to_tensor=True)
                    coverage_matrix = util.cos_sim(rubric_embs, clause_embs)
                    
                    # For each rubric requirement, find best matching clause in student answer
                    max_per_rubric = torch.max(coverage_matrix, dim=1).values
                    rubric_coverage = float(torch.mean(max_per_rubric))
                    rubric_coverage = max(0.0, min(1.0, rubric_coverage))

            # 3. Weighted Score Formula (60% semantic similarity + 40% rubric coverage)
            composite_ratio = (0.60 * cos_sim) + (0.40 * rubric_coverage)
            suggested_marks = round(max(0.0, min(float(max_marks), float(max_marks) * composite_ratio)), 2)

            # 4. Confidence Calibration
            confidence = round(0.40 + (0.45 * cos_sim), 2)
            review_status = "COMPLETED" if confidence >= 0.70 and cos_sim >= 0.65 else "NEEDS_REVIEW"

            explanation = (
                f"(Local Semantic Model: all-MiniLM-L6-v2) Semantic similarity: {cos_sim:.2f}, "
                f"Rubric alignment: {rubric_coverage:.2f}. "
            )
            if composite_ratio >= 0.80:
                explanation += "Strong conceptual mastery demonstrated across all key points."
            elif composite_ratio >= 0.50:
                explanation += "Partial correctness; key concepts present with some missing details."
            else:
                explanation += "Low semantic alignment with reference solution."

            return {
                "suggested_marks": suggested_marks,
                "explanation": explanation,
                "confidence": confidence,
                "model_name": "all-MiniLM-L6-v2-local",
                "review_status": review_status
            }
    except Exception as st_err:
        print(f"[subjective_evaluator] Local ST model failed: {st_err}")

    # Fallback Tier 2: String Heuristic (difflib)
    import difflib
        
    similarity = difflib.SequenceMatcher(None, str(reference_answer).lower(), str(student_answer).lower()).ratio()
    
    marks = 0.0
    if similarity > 0.8:
        marks = max_marks
    elif similarity > 0.5:
        marks = max_marks * 0.5
        
    explanation = "Excellent and complete answer." if marks == max_marks else \
                  "Partially correct. Missing some key details from the reference." if marks > 0 else \
                  "Incorrect or insufficient answer."
                  
    return {
        "suggested_marks": marks,
        "explanation": f"(Fallback — LLM unavailable) {explanation} Semantic similarity score: {similarity:.2f}",
        "confidence": 0.3,
        "model_name": "difflib_fallback",
        "review_status": "NEEDS_REVIEW"
    }
