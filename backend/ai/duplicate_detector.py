"""
Facade module forwarding to modular generation subsystem.
"""
from ai.generation.duplicate_detector import *
from ai.generation.duplicate_detector import (
    _get_st_model,
    _risk_label,
    _get_thresholds,
    _no_duplicate,
    _difflib_fallback,
)
