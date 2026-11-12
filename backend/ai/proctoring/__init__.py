"""
AI Proctoring Subsystem: Frame Violation Analysis & Dynamic Integrity Scoring.
"""
from .proctoring_core import (
    process_frame_detections,
    create_event,
    calculate_integrity_score,
)

__all__ = [
    "process_frame_detections",
    "create_event",
    "calculate_integrity_score",
]
