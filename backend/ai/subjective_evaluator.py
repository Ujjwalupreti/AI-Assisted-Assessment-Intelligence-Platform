import re
import json
from .llm_client import generate_json

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
            
    # Simulation (Fallback)
    import difflib
    
    if not reference_answer or str(reference_answer).strip() == "":
        return {
            "suggested_marks": 0.0,
            "explanation": "(Simulated AI) No reference answer provided by teacher. Requires manual grading.",
            "confidence": 0.0,
            "model_name": "difflib_simulation",
            "review_status": "NEEDS_REVIEW"
        }
        
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
