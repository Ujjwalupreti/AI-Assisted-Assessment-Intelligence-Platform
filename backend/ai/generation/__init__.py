"""
AI Generation & Deduplication Subsystem: Vector Deduplication, Embedding Services & Synthesis.
"""
from .duplicate_detector import (
    detect_duplicates,
    _get_st_model,
    _risk_label,
    group_duplicates,
    archive_duplicates,
)
from .question_generator import generate_candidate_question
from .embedding_service import (
    EmbeddingService,
    embedding_service,
    get_embedding,
)

# Backward-compatibility alias
embed_text = get_embedding

__all__ = [
    "detect_duplicates",
    "_get_st_model",
    "_risk_label",
    "group_duplicates",
    "archive_duplicates",
    "generate_candidate_question",
    "EmbeddingService",
    "embedding_service",
    "get_embedding",
    "embed_text",
]
