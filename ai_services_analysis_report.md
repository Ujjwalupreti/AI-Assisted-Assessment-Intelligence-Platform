# AI/ML Services Analysis Report

This report outlines the current AI/ML capabilities implemented in the **AI-Assisted Assessment Intelligence Platform (AAIP)**, the underlying technology stack used, and the features that are currently missing or simulated.

## Current Tech Stack for AI Services
The backend is built with **Python/Flask** and leverages several specialized AI libraries and APIs:
- **`sentence-transformers`**: Provides access to robust NLP deep-learning models (specifically `all-MiniLM-L6-v2`) to generate dense vector embeddings for text.
- **`scikit-learn` & `torch`**: Support libraries for tensor operations and machine learning capabilities.
- **`google.generativeai`**: The official SDK for integrating Google's Gemini Large Language Models via API.
- **`difflib`**: A standard Python library used as a lightweight fallback for text similarity when heavier ML models are unavailable or fail.

## Present & Working AI Features

### 1. Intelligent Question Classification (`analyze_question`)
**Status:** **ACTIVE (Advanced Heuristic)**
When a teacher adds a new question (manually or via bulk CSV), the platform automatically analyzes the question text to deduce critical pedagogical metadata without human intervention.
- **Bloom's Taxonomy Prediction**: Evaluates the linguistic structure and verb usage to categorize the question into cognitive levels (Remember, Understand, Apply, Analyze, Evaluate, Create).
- **Difficulty Prediction**: Correlates the predicted Bloom's level with the complexity of the sentence (average word length, total word count) to assign an Easy, Medium, or Hard difficulty.
- **Quality Scoring**: Assigns an "AI Quality Score" by penalizing extreme lengths and poorly formatted text, rewarding well-structured questions.

### 2. Semantic Duplicate Detection (`check_duplicate`)
**Status:** **ACTIVE (Deep Learning Model)**
When a teacher creates a question, the system checks it against all existing questions in the database to prevent redundancy.
- **How it works:** It uses `SentenceTransformer` to encode both the new question and existing questions into numerical vectors (embeddings). It then calculates the **Cosine Similarity** between these vectors. 
- **Advantage:** Unlike simple text matching, this approach understands *meaning*. If a teacher writes "Explain the process of photosynthesis" and another writes "Describe how plants make their own food", the ML model will flag them as duplicates because they share a high semantic similarity, even if they share zero keywords.

### 3. Subjective Answer Evaluation (`evaluate_subjective_answer`)
**Status:** **ACTIVE (LLM Integration / Simulated Fallback)**
During exam submission, subjective (essay-style) questions are automatically graded by an AI rather than requiring manual teacher grading.
- **How it works:** The system constructs a prompt containing the Question, the Reference Answer (Ideal), the Student's Answer, and the Maximum Marks.
- **LLM Engine:** It attempts to use the **Google Gemini 1.5 Flash** model (if the `GOOGLE_API_KEY` is present in the environment) to rigorously evaluate the answer. The model awards partial, fractional marks based on the concepts present in the student's text and provides a textual explanation justifying the grade.
- **Fallback:** If the API key is missing or the network fails, it falls back to a simplistic SequenceMatcher to simulate partial grading (0%, 50%, or 100% of max marks).

## Missing or Incomplete AI/ML Features

While the core question intelligence and text-based evaluation are present, several advanced AI components are currently missing or simulated:

### 1. Computer Vision / Proctoring Engine
**Status:** **MISSING**
- Currently, there is no AI-driven computer vision model analyzing webcam feeds. True proctoring would require an ML model (like MediaPipe or YOLO) running on the frontend or a background worker to detect multiple faces, gaze tracking (looking away from the screen), or mobile phone detection.

### 2. Audio/Speech Recognition (Environment Analysis)
**Status:** **MISSING**
- The system cannot currently detect "extra voice in surrounding" as requested in your previous requirements. Implementing this would require a browser-based audio analyzer (like Web Audio API combined with a lightweight Voice Activity Detection ML model) to flag unauthorized talking.

### 3. True ML-Based Classification (Non-Heuristic)
**Status:** **SIMULATED**
- The `analyze_question` function currently uses a highly advanced *heuristic* (rules-based logic analyzing word lengths and vocabulary intersections) rather than a pre-trained classification model. While highly effective, a true ML classifier trained on thousands of exam questions would yield more accurate Bloom's Taxonomy predictions.

### 4. Adaptive Testing Pipeline
**Status:** **MISSING**
- The system does not yet alter the difficulty of subsequent questions based on the student's real-time performance (Computer Adaptive Testing). 

## Conclusion
The platform has a strong foundation for textual AI services (Semantic Embeddings and LLM Grading). The primary area requiring immediate attention to achieve a full "Proctoring" system is the integration of browser-based or worker-based **Computer Vision (CV) and Audio Analysis** for anti-cheating mechanisms.
