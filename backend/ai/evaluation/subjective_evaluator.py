"""
Subjective Evaluator facade for backwards compatibility.
Delegates to the modular evaluation dispatcher.
"""
from ai.evaluation.evaluation_dispatcher import evaluate_answer

def evaluate_subjective_answer(
    question_text,
    reference_answer,
    student_answer,
    max_marks=1.0,
    rubric=None,
    use_rag=False,
    course_name=None,
    answer_type="TEXT",
    structured_answer=None,
    file_reference=None
):
    """
    Evaluates subjective answers across text, math, automata, and file attachments.
    """
    return evaluate_answer(
        question_text=question_text,
        student_answer=student_answer,
        reference_answer=reference_answer,
        max_marks=max_marks,
        rubric=rubric,
        answer_type=answer_type,
        structured_answer=structured_answer,
        file_reference=file_reference,
        use_rag=use_rag,
        course_name=course_name
    )
