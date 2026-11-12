"""
Canonical QIS AnalysisResult schemas.

IMPORTANT: All classification results use `label` and `confidence` consistently.
Previous inconsistencies (BloomResult.level, TopicResult.topic, DifficultyResult.level)
are fixed here. All modules must use these canonical types.
"""
from typing import TypedDict, List, Optional, Any, Dict


# --- Classification Results ---

class ClassificationResult(TypedDict):
    """Base classification result. All classifiers must return this structure."""
    label: str
    confidence: float
    method: str  # "ml_model" | "llm" | "heuristic_fallback" | "structural"


class TopicResult(TypedDict):
    label: str          # e.g. "Algorithms"
    confidence: float
    alternatives: List[Dict[str, Any]]  # [{"label": "Data Structures", "confidence": 0.05}]
    method: str


class BloomResult(TypedDict):
    label: str          # Remember | Understand | Apply | Analyze | Evaluate | Create
    confidence: float
    evidence: List[str]  # Keywords/reasoning supporting this classification
    method: str


class DifficultyResult(TypedDict):
    label: str          # Easy | Medium | Hard
    confidence: float
    reasoning_factors: List[str]
    method: str


class QuestionTypeResult(TypedDict):
    label: str          # MCQ | TRUE_FALSE | SHORT_ANSWER | LONG_ANSWER | NUMERICAL | CODING | FILL_IN_THE_BLANK
    confidence: float
    method: str


# --- Quality ---

class QualityIssue(TypedDict):
    severity: str   # low | medium | high
    type: str       # AMBIGUITY | GRAMMAR | INCOMPLETE | POOR_DISTRACTOR | DUPLICATE_OPTION
    message: str
    option: Optional[str]


class QualityDimensions(TypedDict):
    clarity: float
    completeness: float
    specificity: float
    grammar: float
    ambiguity: float


class QualityResult(TypedDict):
    overall_score: Optional[float]  # 0.0-1.0, None if LLM unavailable
    dimensions: Optional[QualityDimensions]
    status: str  # GOOD | WARNING | POOR | AI_UNAVAILABLE


# --- Validation ---

class MCQValidationResult(TypedDict):
    valid: bool
    issues: List[QualityIssue]


# --- Duplicate Detection ---

class SimilarQuestion(TypedDict):
    question_id: int
    similarity: float
    text_preview: str  # First 100 chars


class DuplicateResult(TypedDict):
    risk: float          # 0.0–1.0 cosine similarity score
    risk_label: str      # LOW | SIMILAR | HIGH_DUPLICATE_RISK
    is_duplicate: bool   # True if risk >= 0.85
    similar_question_id: Optional[int]
    similarity: float
    similar_questions: List[SimilarQuestion]  # Top-3
    method: str  # "sentence_transformer" | "difflib_fallback"


# --- Alignment ---

class AlignmentResult(TypedDict):
    topic: str      # MATCH | MISMATCH | NOT_CHECKED
    bloom: str      # MATCH | MISMATCH | NOT_CHECKED
    difficulty: str # MATCH | MISMATCH | NOT_CHECKED


# --- Explanations ---

class Explanations(TypedDict):
    topic: str
    bloom: str
    difficulty: str
    quality: str


# --- Recommendations ---

class Recommendation(TypedDict):
    issue: str
    severity: str       # LOW | MEDIUM | HIGH | CRITICAL
    why: str
    recommendation: str
    suggested_improvement: Optional[str]


# --- Review ---

class ReviewDecision(TypedDict):
    required: bool
    reasons: List[str]
    priority: str  # LOW | MEDIUM | HIGH


# --- Model Metadata ---

class ModelMetadata(TypedDict):
    model_name: str
    model_version: str
    embedding_model: str
    llm_model: str
    analysis_version: str
    llm_status: str  # USED | UNAVAILABLE | FAILED


# --- Canonical Analysis Result ---

class AnalysisResult(TypedDict):
    status: str     # FULL | PARTIAL | FAILED
    analysis_status: str  # COMPLETED | DEGRADED | FAILED
    warnings: List[str]
    errors: List[str]
    classification: Dict[str, Any]   # contains topic, bloom, difficulty, question_type
    quality: QualityResult
    validation: MCQValidationResult
    duplicate: DuplicateResult
    alignment: AlignmentResult
    recommendations: List[Recommendation]
    explanations: Explanations
    review: ReviewDecision
    model_metadata: ModelMetadata
