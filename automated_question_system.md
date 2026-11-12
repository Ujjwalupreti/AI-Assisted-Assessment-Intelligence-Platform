# Automated Question System

The automated question system in this project is a comprehensive suite built around the **Question Intelligence System (QIS)**. It not only generates questions but also rigorously analyzes, classifies, validates, and manages duplicates for them. 

The system operates via a well-defined workflow, coordinating between API routes and dedicated AI service modules.

## Workflow Overview

1. **Question Request**: The system receives a request for a new question based on specific criteria (Topic, Bloom's Taxonomy Level, Difficulty) and optional Retrieval-Augmented Generation (RAG) context.
2. **LLM Generation**: A prompt is built and sent to the Large Language Model to generate the question structure (Text, Options, Correct Answer, Explanation).
3. **QIS Pipeline Analysis**: Before the generated question is returned or saved, it is immediately routed through the QIS pipeline. The pipeline validates the question, classifies its attributes, checks for formatting issues, calculates a quality score, and checks against the existing repository to prevent duplicates.
4. **Assessment / Slot Assembly**: Approved questions can be assembled into full assessments or divided into balanced slots (variants) based on an exam blueprint.

---

## Core Files and Functions

### 1. Question Generation
- **Route File**: `backend/routes/exam_intelligence_routes.py`
  - **Endpoint**: `/{exam_id}/generate-gap-questions`
  - **Function**: Receives generation requests. If `use_rag` is true, it retrieves syllabus context via the RAG retriever. It then calls `generate_candidate_question()` and subsequently passes the newly generated question through `analyze_question_qis()` to attach AI analysis metadata directly into the response payload.
- **Service File**: `backend/ai/question_generator.py`
  - **Function**: `generate_candidate_question(topic, bloom_level, difficulty, rag_context)` constructs the LLM prompt and enforces a strict JSON schema output containing the question text, options, and explanation.

### 2. Question Intelligence System (QIS) Analysis
> [!IMPORTANT]
> The QIS Pipeline is the "Single Source of Truth". All generated questions must pass through this pipeline to ensure they meet quality and uniqueness standards.

- **Orchestrator**: `backend/ai/pipeline.py`
  - **Function**: `analyze_question_qis(...)` runs the question through several checks:
    - **Ciphertext Guard**: Validates that the input isn't encrypted (e.g., base64).
    - **Classification**: Uses dedicated classifier modules to predict Topic, Bloom's Level, Difficulty, and Question Type.
    - **MCQ Validation**: Runs deterministic checks on the options.
    - **Quality Analysis**: Generates an overall score and flags specific issues.
    - **Duplicate Detection**: Computes semantic similarity against existing questions.
    - **Blueprint Alignment**: Verifies if the question aligns with the expected exam blueprint.
- **Dedicated Classifiers and Analyzers**:
  - `backend/ai/topic_classifier.py`: Classifies the subject topic.
  - `backend/ai/bloom_classifier.py`: Predicts the cognitive complexity (Bloom's Taxonomy).
  - `backend/ai/difficulty_estimator.py`: Estimates whether the question is Easy, Medium, or Hard.
  - `backend/ai/quality_analyzer.py`: Checks for grammatical/structural quality.
  - `backend/ai/mcq_validator.py`: Ensures all options are present and a correct option is identified.
  - `backend/ai/duplicate_detector.py`: Calculates risk percentage of the question being a duplicate of an existing one.
- **Route File**: `backend/routes/qis_routes.py`
  - Exposes endpoints like `/analyze` (real-time single question) and `/analyze-batch` (background queued jobs for entire exams).

### 3. Assessment Assembly & Slot Division
> [!TIP]
> The automated system doesn't just create individual questions; it generates entire assessments and balanced variants (slots) automatically.

- **Assembly Service**: `backend/ai/assessment_assembler.py`
  - Used by `/assemble` in the intelligence routes to create a full exam preview based on desired distributions of topic, difficulty, and bloom level.
- **Slot Divider Service**: `backend/ai/slot_divider.py`
  - **Function**: `generate_slots()` automatically distributes questions into different variants (slots) ensuring fairness. It balances metrics like total marks, quality score, and topic distribution across all slots.

### 4. Recommendations
- **Service**: `backend/ai/recommender.py`
  - Calculates the gap between the generated questions and the target exam blueprint, offering automated recommendations on what type of questions need to be generated next to satisfy the exam's structural requirements. Exposed via `/exam/{exam_id}/recommendations`.
