from .llm_client import generate_json

def generate_candidate_question(topic: str, bloom_level: str, difficulty: str, rag_context: str = None):
    """
    Generates a candidate MCQ based on the blueprint gap.
    Optionally grounds the generation in provided rag_context.
    """
    context_instruction = ""
    if rag_context:
        context_instruction = f"""
    --- KNOWLEDGE BASE CONTEXT ---
    You must base your question ONLY on the information provided in the context below. 
    Use the terminology, concepts, and facts strictly from this context.
    
    Context:
    {rag_context}
    ------------------------------
    """

    prompt = f"""
    Generate an exam question matching the following criteria:
    Topic: {topic}
    Bloom's Level: {bloom_level}
    Difficulty: {difficulty}
    
    {context_instruction}
    
    Return ONLY a JSON object with this schema:
    {{
        "text": "The question text",
        "option_a": "Option A text",
        "option_b": "Option B text",
        "option_c": "Option C text",
        "option_d": "Option D text",
        "correct_option": "A, B, C, or D",
        "explanation": "Why this is correct"
    }}
    """
    
    return generate_json(prompt, temperature=0.7)
