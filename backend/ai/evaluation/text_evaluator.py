"""
Specialized Descriptive Text Answer Evaluator.
Implements:
Tier 1: Constrained LLM + Reference Answer + Rubric + RAG Grounding
Tier 2: SentenceTransformers ('all-MiniLM-L6-v2') 60/40 Cosine Similarity & Rubric Clause Coverage
Tier 3: difflib.SequenceMatcher emergency fallback
"""
import re
from typing import Dict, Any, List
from ai.core.llm_client import generate_json

def evaluate_text_answer(
    question_text: str,
    reference_answer: str,
    student_answer: str,
    max_marks: float = 1.0,
    rubric: str = None,
    use_rag: bool = False,
    course_name: str = None
) -> Dict[str, Any]:
    max_marks = float(max_marks)
    
    # Empty check
    if not student_answer or str(student_answer).strip() == "":
        return {
            "suggested_marks": 0.0,
            "max_marks": max_marks,
            "explanation": "No answer provided by the student.",
            "confidence": 1.0,
            "review_status": "COMPLETED",
            "evaluation_method": "ZERO_INPUT_CHECK",
            "model_name": "system",
            "issues": ["EMPTY_ANSWER"]
        }

    # Tier 1: Grounded LLM Grading
    try:
        context_instruction = ""
        if use_rag:
            from ai.rag.retriever import retrieve_context
            rag_context = retrieve_context(query=question_text, top_k=2)
            if rag_context:
                context_instruction = f"""
                --- KNOWLEDGE BASE CONTEXT ---
                Use the following context from the course syllabus to help determine factual correctness:
                {rag_context}
                ------------------------------
                """

        # Delimiter isolation against prompt injection
        prompt = f"""
        You are an expert AI grader. Evaluate the student's answer based on the reference answer and rubric.
        
        Question: {question_text}
        Reference Answer (Ideal): {reference_answer}
        Rubric: {rubric if rubric else 'Evaluate strictly against Reference Answer key concepts.'}
        
        {context_instruction}
        
        <<<STUDENT_ANSWER_START>>>
        {student_answer}
        <<<STUDENT_ANSWER_END>>>
        
        Maximum Marks: {max_marks}
        
        Evaluate the answer strictly but fairly. Extract concepts from the student's answer and match them to the rubric/reference. Award partial marks appropriately.
        
        Return ONLY a JSON object with EXACTLY these keys:
        {{
            "suggested_marks": (float between 0.0 and {max_marks}),
            "explanation": "string explaining why these marks were awarded, pointing out missing or correct concepts according to the rubric",
            "confidence": (float between 0.0 and 1.0. Use < 0.70 if ambiguous or creative answer requires teacher review)
        }}
        """

        data = generate_json(prompt, temperature=0.2)
        if data and isinstance(data, dict) and 'suggested_marks' in data:
            raw_marks = float(data.get('suggested_marks', 0.0))
            # Mathematical Clamping
            clamped_marks = max(0.0, min(raw_marks, max_marks))
            conf = float(data.get('confidence', 0.85))
            conf = max(0.0, min(conf, 1.0))
            review_status = "NEEDS_REVIEW" if conf < 0.70 else "COMPLETED"

            return {
                "suggested_marks": round(clamped_marks, 2),
                "max_marks": max_marks,
                "explanation": str(data.get('explanation', 'AI evaluation complete.')),
                "confidence": conf,
                "review_status": review_status,
                "evaluation_method": "LLM_RUBRIC_RAG",
                "model_name": "gemini-1.5-flash-client",
                "issues": []
            }
    except Exception as e:
        print(f"[text_evaluator] LLM Tier 1 fallback: {e}")

    # Missing reference fallback
    if not reference_answer or str(reference_answer).strip() == "":
        return {
            "suggested_marks": 0.0,
            "max_marks": max_marks,
            "explanation": "No reference answer configured. Manual teacher review required.",
            "confidence": 0.0,
            "review_status": "NEEDS_REVIEW",
            "evaluation_method": "MANUAL_REQUIRED",
            "model_name": "none",
            "issues": ["NO_REFERENCE_ANSWER"]
        }

    # Tier 2: Local SentenceTransformer Embedding & Clause Coverage
    try:
        from ai.generation.duplicate_detector import _get_st_model
        import torch
        from sentence_transformers import util

        st_model = _get_st_model()
        if st_model is not None:
            ref_emb = st_model.encode(str(reference_answer), convert_to_tensor=True)
            stu_emb = st_model.encode(str(student_answer), convert_to_tensor=True)
            cos_sim = float(util.cos_sim(stu_emb, ref_emb)[0][0])
            cos_sim = max(0.0, min(1.0, cos_sim))

            # Clause-level rubric coverage
            rubric_coverage = cos_sim
            if rubric and str(rubric).strip():
                rubric_lines = [r.strip() for r in str(rubric).split("\n") if len(r.strip()) > 5]
                if rubric_lines:
                    student_clauses = [s.strip() for s in re.split(r'[.!?\n]', str(student_answer)) if len(s.strip()) > 5]
                    if not student_clauses:
                        student_clauses = [str(student_answer)]
                    clause_embs = st_model.encode(student_clauses, convert_to_tensor=True)
                    rubric_embs = st_model.encode(rubric_lines, convert_to_tensor=True)
                    coverage_matrix = util.cos_sim(rubric_embs, clause_embs)
                    max_per_rubric = torch.max(coverage_matrix, dim=1).values
                    rubric_coverage = float(torch.mean(max_per_rubric))
                    rubric_coverage = max(0.0, min(1.0, rubric_coverage))

            composite_ratio = (0.60 * cos_sim) + (0.40 * rubric_coverage)
            suggested_marks = round(max(0.0, min(max_marks, max_marks * composite_ratio)), 2)
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
                "max_marks": max_marks,
                "explanation": explanation,
                "confidence": confidence,
                "review_status": review_status,
                "evaluation_method": "LOCAL_VECTOR_SEMANTIC",
                "model_name": "all-MiniLM-L6-v2",
                "issues": []
            }
    except Exception as st_err:
        print(f"[text_evaluator] Local ST model failed: {st_err}")

    # Tier 3: SequenceMatcher fallback
    import difflib
    similarity = difflib.SequenceMatcher(None, str(reference_answer).lower(), str(student_answer).lower()).ratio()
    
    marks = 0.0
    if similarity > 0.8:
        marks = max_marks
    elif similarity > 0.5:
        marks = round(max_marks * 0.5, 2)
        
    explanation = "Excellent match." if marks == max_marks else \
                  "Partially matched reference answer." if marks > 0 else \
                  "Low text similarity with reference."
                  
    return {
        "suggested_marks": marks,
        "max_marks": max_marks,
        "explanation": f"(Heuristic Fallback) {explanation} Token similarity score: {similarity:.2f}",
        "confidence": 0.35,
        "review_status": "NEEDS_REVIEW",
        "evaluation_method": "STRING_HEURISTIC_DIFFLIB",
        "model_name": "difflib",
        "issues": ["TIER3_DIFFLIB_FALLBACK"]
    }
