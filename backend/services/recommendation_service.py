"""
Recommendation Service.

Thin service layer that wraps the AI recommender with app context.
"""
from ai.assembly.recommender import generate_recommendations as _generate


def get_recommendations(exam_id: int, weights: dict = None) -> dict:
    """
    Get recommendations for an exam.
    Must be called within Flask app context.
    """
    return _generate(exam_id, weights=weights)
