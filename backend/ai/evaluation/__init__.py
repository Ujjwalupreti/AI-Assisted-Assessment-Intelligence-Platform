"""
AI Evaluation Subsystem: Subjective Grading, Semantic Similarity & Rubric Matching.
"""
from .subjective_evaluator import evaluate_subjective_answer
from .evaluation_dispatcher import evaluate_answer
from .math_evaluator import evaluate_math_answer
from .automata_evaluator import evaluate_automata_answer

__all__ = [
    "evaluate_subjective_answer",
    "evaluate_answer",
    "evaluate_math_answer",
    "evaluate_automata_answer"
]
