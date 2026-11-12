"""
QIS AI/ML Modular Architecture Package.

Subsystems:
- core: Schemas, Gemini client wrapper, pipeline orchestration, persistence
- classifiers: Bloom's taxonomy, difficulty estimation, topic classification, MCQ validator
- generation: Duplicate detection, embedding service, generative question synthesis
- assembly: Blueprint assessment assembler, exam slot divider, recommendation engine
- evaluation: Subjective evaluator with 60:40 dense semantic vector formula
- proctoring: Real-time vision violation processing and rolling integrity scoring
- rag: Syllabus extraction, chunk embedding, and semantic vector retrieval
"""
from .core import *
from .classifiers import *
from .generation import *
from .assembly import *
from .evaluation import *
from .proctoring import *
from .rag import *
