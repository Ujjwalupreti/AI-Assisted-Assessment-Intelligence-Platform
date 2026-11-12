The biggest problem is not that the UI is ugly or that one button is missing. The deeper problem is that **AI analysis is currently treated as a per-question metadata generator**, whereas your intended architecture needs an **Exam/Question Intelligence pipeline** that analyzes the entire question bank, enforces a blueprint, detects quality problems, recommends/generates missing fields, and gives the teacher actionable decisions.

---

# 1. What the current screen actually does

From the screenshot, the current workflow is:

```text
Yes. I reviewed the **QIS bug report against the uploaded backend files**. Your report is directionally correct, but several points need to be **reclassified or expanded**. There are also a few important bugs that your report currently misses.

The most important finding is:

> **QIS integration is currently inconsistent because there are two competing analysis contracts in the codebase: the new `analyze_question_qis()` contract and the legacy `analyze_question()` contract.**

That is a real blocking issue.

---

# 1. Executive verdict

I would classify the current state as:

**🔴 NOT STABLE — QIS integration should not be considered production-ready.**

### Severity summary

| Issue                                                                 | Severity     | Confirmed from files?                          |
| --------------------------------------------------------------------- | ------------ | ---------------------------------------------- |
| Legacy `analyze_question` import                                      | 🔴 Critical  | **Yes**                                        |
| Legacy response-schema parsing                                        | 🔴 Critical  | **Yes**                                        |
| QIS route/new schema                                                  | 🟢 Correct   | **Yes**                                        |
| New DB fields require migration                                       | 🔴 Critical* | Schema change confirmed                        |
| Encrypted ciphertext → QIS                                            | 🔴 Critical  | **Yes, conditional on encrypted payload path** |
| Synchronous batch AI                                                  | 🔴 High      | **Yes**                                        |
| LLM fallback falsely reports 0.8/GOOD                                 | 🔴 High      | **Yes**                                        |
| Hard-coded/stub ML models                                             | 🔴 Critical  | Needs `inference.py` confirmation              |
| Duplicate detection scalability                                       | 🟠 High      | **Yes**                                        |
| Duplicate detection cross-exam limitation                             | 🔴 High      | **Yes**                                        |
| MCQ LaTeX/Markdown normalization                                      | 🟠 Medium    | Plausible, not demonstrated by current code    |
| No transactional isolation in Analyze All                             | 🔴 High      | **Yes**                                        |
| `Analyze All` destroys previous analysis before success               | 🔴 High      | **Yes**                                        |
| QIS analysis is not persisted by `/analyze`                           | 🔴 High      | **Yes**                                        |
| `bulk_questions` does not persist QIS analysis                        | 🔴 High      | **Yes**                                        |
| AI-generated question bypasses QIS                                    | 🔴 High      | **Yes**                                        |
| Security/ownership check in QIS routes                                | 🔴 High      | Needs strengthening                            |
| AIJob model exists but is unused                                      | 🟠 High      | **Yes**                                        |
| No proper QIS review endpoint                                         | 🟠 High      | **Yes**                                        |
| Question embedding table exists but duplicate detector doesn't use it | 🟠 High      | **Yes**                                        |

* The migration requirement depends on whether the deployed DB has already been migrated.

---

# 2. 🔴 Confirmed critical bug: legacy Analyze All is broken

This is the most obvious integration failure.

`exam_intelligence_routes.py` still contains:

```python
from ai.pipeline import analyze_question
```

and then:

```python
res = analyze_question(q.text, [])
```

 

But the new `pipeline.py` exposes:

```python
def analyze_question_qis(...)
```

not the legacy function.

Your new QIS route correctly imports:

```python
from ai.pipeline import analyze_question_qis
```



### Result

When Flask imports:

```python
exam_intelligence_routes
```

the application can fail during startup with:

```text
ImportError:
cannot import name 'analyze_question'
```

This is actually **worse than "Analyze All crashes when clicked."**

Because `app.py` imports `exam_intelligence_routes` during application creation:

```python
from exam_intelligence_routes import intelligence_bp
```



So depending on Python/import state, **the entire Flask application may fail to start**, not merely the Analyze All endpoint.

### Priority

**P0 — fix immediately.**

---

# 3. 🔴 Confirmed second bug: old response schema is incompatible

Even if you change:

```python
analyze_question
```

to:

```python
analyze_question_qis
```

the route is still broken.

Old code expects:

```python
res['model_metadata'].get('model')
res['topic'].get('topic')
res['bloom'].get('level')
res['difficulty'].get('level')
res['quality'].get('score')
res['question_type'].get('question_type')
res['duplicate'].get('risk')
```



The new QIS schema is:

```text
classification
 ├── question_type
 ├── topic
 ├── bloom
 └── difficulty

quality
validation
alignment
recommendations
explanations
review_required
model_metadata
```

The new pipeline explicitly returns that structure. 

So changing only the import will produce errors such as:

```text
KeyError: 'topic'
KeyError: 'bloom'
KeyError: 'difficulty'
KeyError: 'model'
```

### Required

`Analyze All` must consume **the same `AnalysisResult` contract as every other QIS consumer**.

---

# 4. 🔴 Your code currently has TWO QIS entry paths

You now have:

### Legacy intelligence route

```text
POST /api/intelligence/<exam_id>/analyze-all
```

### New QIS route

```text
POST /api/ai/questions/analyze
POST /api/ai/questions/analyze-batch
POST /api/ai/questions/<id>/reanalyze
```

The new route correctly calls:

```python
analyze_question_qis(...)
```

and accepts:

```text
expected_topic
expected_bloom
expected_difficulty
```



The old route doesn't.

### This is an architectural problem.

You should have:

```text
                    QIS
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
     Single Analysis       Batch Analysis
          │                     │
          └──────────┬──────────┘
                     ▼
             analyze_question_qis()
```

Not:

```text
Old Analysis Pipeline ────────┐
                              ├── Question DB
New QIS Pipeline ─────────────┘
```

There should be **one canonical analysis contract**.

---

# 5. 🔴 Database migration: your report is correct, with one qualification

Your model now contains:

```python
ai_analysis_json
teacher_review_status
teacher_accepted_at
analysis_method
```



SQLAlchemy model changes do **not automatically alter an already-existing database table**.

So if the deployed DB does not have these columns:

```text
OperationalError
no such column: question_ai_analysis.ai_analysis_json
```

can occur.

### However

I would phrase your report as:

> **Migration is required unless the database has already been migrated or recreated from the current model.**

The uploaded files do not contain a migration script, so I cannot confirm whether your actual database has already been updated.

### P0

Use Flask-Migrate/Alembic rather than dropping the database.

---

# 6. 🔴 More serious: `/analyze` does not persist QIS analysis

This is a major issue missing from your report.

Your new QIS route does:

```python
result = analyze_question_qis(...)
return jsonify(result), 200
```



It **does not save** the result to `QuestionAiAnalysis`.

Compare that with `/reanalyze`, which explicitly does:

```python
analysis.ai_analysis_json = json.dumps(result)
analysis.model_name = ...
analysis.topic = ...
...
db.session.commit()
```



So you have:

```text
/analyze
    ↓
QIS
    ↓
JSON response
    ↓
NOT STORED
```

while:

```text
/reanalyze
    ↓
QIS
    ↓
DB
```

### Why this matters

The frontend may display the AI analysis, but:

* it isn't auditable
* it isn't available later
* teacher review state isn't preserved
* exam analytics won't necessarily see it
* model version isn't persisted

### Fix

Create one persistence function:

```python
persist_qis_analysis(question_id, result)
```

and use it consistently.

---

# 7. 🔴 `bulk_questions` also persists only the flattened result

Your bulk route calls:

```python
ai_meta = analyze_question_qis(...)
```

then writes:

```python
topic
difficulty
bloom_level
ai_quality_score
```

to `Question`. 

But it does not appear to persist:

```text
ai_analysis_json
alignment
validation
recommendations
explanations
review_required
model metadata
```

So you're losing most of the QIS result.

This defeats one of the reasons you introduced `QuestionAiAnalysis`.

---

# 8. 🔴 Encryption issue: your report is essentially correct

Your single-question endpoint does:

```python
text = data.get('text')
```

then:

```python
ai_meta = analyze_question_qis(text, options=options)
```



And only afterward saves that same `text` to the database. 

Therefore:

```text
Frontend encrypted text
        ↓
question_routes.py
        ↓
analyze_question_qis(encrypted_text)
        ↓
NLP/LLM
```

is indeed broken **if the frontend is sending ciphertext to this endpoint**.

The QIS pipeline requires meaningful plaintext because it directly sends `question_text` into:

```python
predict_topic(question_text)
predict_bloom(question_text)
predict_difficulty(question_text, ...)
predict_question_type(question_text)
```



---

# 9. But there is an architectural decision you must make

Your current system is trying to achieve:

```text
Zero-knowledge encrypted question storage
```

and:

```text
Server-side AI analysis
```

These requirements conflict.

You need to explicitly choose:

### Recommended for this project

```text
Teacher
  ↓
HTTPS
  ↓
Backend
  ↓
QIS
  ↓
Encrypted-at-rest storage
```

In other words:

> **Do not claim zero-knowledge encryption.**

Instead implement:

* TLS in transit
* server-side authorization
* encryption at rest
* database encryption where appropriate
* controlled QIS access
* audit logging

This is a much more defensible architecture for your academic project.

---

# 10. 🔴 Batch processing problem is confirmed

Your `/analyze-batch` route literally does:

```python
for q in questions:
    res = analyze_question_qis(...)
```



And each QIS call invokes:

```python
generate_json(prompt)
```



So:

```text
50 questions
      ↓
50 QIS calls
      ↓
50 LLM calls
```

assuming the LLM is available.

Your report's performance concern is therefore valid.

---

# 11. 🟠 But don't batch the LLM blindly

Your suggested:

> "Ask LLM to explain 10 questions at once."

can work, but I would **not make that the primary architecture**.

Better:

```text
POST /analyze-batch
        ↓
Create AIJob
        ↓
202 Accepted
        ↓
Worker
        │
        ├── Q1 → ML
        ├── Q2 → ML
        ├── Q3 → ML
        └── ...
        ↓
LLM explanation batches
        ↓
Persist results
        ↓
COMPLETED
```

And interestingly, your database already contains an `AIJob` model:

```python
job_type
target_id
status
result_data
error_message
created_at
completed_at
```



So the architecture has already started moving toward asynchronous jobs.

**The problem is that the job model isn't being used.**

---

# 12. 🔴 Analyze All has a dangerous transactional design

Current code:

```python
QuestionAiAnalysis.query.filter(...).delete(...)
```

then:

```python
for q in questions:
    ...
```



Suppose you have:

```text
100 questions
```

and:

```text
Q1-Q60 → successful
Q61 → exception
```

The transaction rolls back if the exception occurs, which helps, but you're still performing a huge synchronous transaction.

More importantly, you are **deleting existing analysis before establishing that the new analysis can complete successfully**.

A safer design is:

```text
Create analysis_job
        ↓
Analyze
        ↓
Validate all results
        ↓
Commit new analysis version
        ↓
Mark old version inactive
```

Or use versioned analysis records.

---

# 13. 🔴 Duplicate detection is currently incomplete

Your duplicate detector uses SentenceTransformer:

```python
all-MiniLM-L6-v2
```

and cosine similarity. 

That's good for an MVP.

But it does:

```python
embeddings2 = model.encode(texts)
```

for all existing questions **on every new question**. 

That means:

```text
Q1 → encode existing questions
Q2 → encode existing questions
Q3 → encode existing questions
...
```

For 5000 questions, this becomes very inefficient.

And your model already contains:

```python
QuestionEmbedding
```



but the detector doesn't appear to use that persistent embedding table.

### Better

```text
Question
 ↓
Embedding Service
 ↓
QuestionEmbedding
 ↓
Vector Index
 ↓
Top-K similarity
```

For your current scale, even PostgreSQL + pgvector would be a reasonable direction.

---

# 14. 🔴 Duplicate detection has another important conceptual flaw

The current route:

```python
existing_q_records =
Question.query.filter_by(exam_id=exam_id)
```

means duplicate checking is limited to the **same exam**. 

That detects:

> "Is this question duplicated within this exam?"

But a real Question Intelligence system should also detect:

> "Is this question already present in my question bank?"

You need two levels:

```text
Duplicate Scope

1. Within Exam
2. Within Teacher Question Bank
3. Institution-wide Question Bank
```

with authorization/privacy constraints.

---

# 15. 🟠 MCQ validator is basic, but your LaTeX observation is valid

The current validator does:

```python
val.strip().lower()
```

before duplicate detection. 

So:

```text
$x^2 + 2x + 1$
```

and a semantically equivalent but syntactically different expression can bypass simple string equality.

Your report correctly identifies this limitation.

But this is **not currently a crash-level bug**.

### Priority

🟠 P2 for MVP
🔴 P1 if mathematical question support is a core requirement.

---

# 16. 🔴 LLM fallback is definitely dangerous

This is one of your strongest findings.

When LLM generation fails:

```python
overall_score = 0.8
status = "GOOD"
```

is returned. 

That means:

```text
LLM unavailable
      ↓
Quality = 0.8
Status = GOOD
```

This is semantically wrong.

The teacher cannot distinguish:

```text
AI says question is good
```

from:

```text
AI was unavailable
```

### Correct behavior

```json
{
  "status": "UNAVAILABLE",
  "overall_score": null,
  "review_required": true,
  "reason": "LLM quality analysis unavailable"
}
```

or:

```text
quality.status = "AI_UNAVAILABLE"
```

Never fabricate a positive AI score.

---

# 17. 🔴 Another hidden problem: fallback quality differs between modules

You have:

### `pipeline.py`

fallback:

```text
0.8 / GOOD
```



### `quality_analyzer.py`

fallback:

```text
0.5
Could not perform AI quality analysis.
```



This means different parts of the codebase have different failure semantics.

You need **one QIS failure policy**.

---

# 18. 🔴 Question type classification has a major fallback issue

`question_type_classifier.py` falls back to:

```python
{
    "question_type": "SUBJECTIVE",
    "confidence": 0.2
}
```



But your pipeline then checks:

```python
type_res['label'] == 'MCQ'
```



This raises a potential **schema inconsistency**.

Your schema expects:

```text
QuestionTypeResult:
label
confidence
```



but the standalone classifier returns:

```text
question_type
confidence
```

This needs to be checked/fixed in `ml/inference.py`.

### This is an additional issue your report missed.

---

# 19. 🔴 Your `AnalysisResult` schema and actual pipeline contract need stricter validation

The schema defines:

```text
classification
quality
validation
alignment
recommendations
explanations
review_required
model_metadata
```



But the pipeline merely builds dictionaries and uses `.get()` heavily.

There is no strong runtime validation that:

```text
overall_score ∈ [0,1]
confidence ∈ [0,1]
Bloom ∈ valid enum
difficulty ∈ valid enum
question_type ∈ valid enum
```

You should validate the final result before persisting it.

For example:

```text
QIS
 ↓
AnalysisResult validation
 ↓
Persistence
```

not:

```text
QIS
 ↓
DB
```

---

# 20. 🔴 Alignment is too simplistic

Current alignment is:

```python
expected.lower() != predicted.lower()
```



So:

```text
Expected: Data Structures
Predicted: Algorithms
```

→ mismatch.

Fine.

But:

```text
Expected: Graph Algorithms
Predicted: Graph Theory
```

→ mismatch.

Even though semantically they may be related.

More importantly, it doesn't calculate:

```text
alignment confidence
alignment score
severity
```

It only gives:

```text
MATCH
MISMATCH
```

For QIS, I'd recommend:

```json
{
  "topic": {
    "status": "MISMATCH",
    "similarity": 0.61,
    "confidence": 0.82
  }
}
```

---

# 21. 🔴 `Analyze All` doesn't pass options

The legacy route currently calls:

```python
res = analyze_question(q.text, [])
```



Therefore even after migrating it to QIS, you should not simply do:

```python
analyze_question_qis(q.text)
```

because QIS needs:

```text
question
options
correct answer
expected metadata
```

for meaningful analysis.

Otherwise MCQ validation cannot properly operate.

---

# 22. 🔴 Generated questions bypass QIS

Your question generator produces:

```text
question
A
B
C
D
correct_option
explanation
```



But after generation, there is no mandatory:

```text
Generated Question
       ↓
QIS
       ↓
Validation
       ↓
Duplicate Detection
       ↓
Quality
       ↓
Blueprint Alignment
       ↓
Teacher Approval
```

This is a major gap.

An LLM-generated question should **never be considered exam-ready immediately**.

---

# 23. 🔴 The new `AIJob` model is currently dead infrastructure

You already have:

```text
AIJob
QUEUED
PROCESSING
COMPLETED
FAILED
```



But `/analyze-batch` doesn't create an `AIJob`.

It simply performs the work synchronously:

```python
for q in questions:
    ...
```



Therefore you have already designed part of the asynchronous architecture but haven't connected it.

This is good news:

> **You don't need to redesign the database to support async QIS jobs; you already have a starting point.**

---

# 24. 🔴 `QuestionAiAnalysis` should have a uniqueness constraint

Currently:

```python
id
question_id
...
```

but I don't see a unique constraint on:

```text
question_id
```

The reanalysis code does:

```python
.first()
```

and creates a new row if none exists. 

You should decide whether you want:

### One current analysis

```text
UNIQUE(question_id)
```

or:

### Analysis history

```text
question_id
analysis_version
model_version
created_at
```

For your project, I recommend **history/versioning** because AI model versions matter.

---

# 25. 🟠 Your database design actually has useful foundations

This part is important.

You already have:

```text
QuestionAiAnalysis
QuestionEmbedding
AIJob
ExamAnalysis
AuditLog
EvaluationReview
QuestionVersion
```



That means the architecture is **ahead of the implementation**.

You're not missing the conceptual entities.

You're missing the connections between them.

---

# 26. Recommended final QIS architecture

I would restructure the backend as:

```text
                  QIS API
                    │
        ┌───────────┴───────────┐
        │                       │
      Single                  Batch
        │                       │
        │                    AIJob
        │                       │
        └──────────┬────────────┘
                   ▼
             QIS Pipeline
                   │
       ┌───────────┼────────────┐
       ▼           ▼            ▼
   ML Models   Validators    Retrieval
       │           │            │
       │           │        Duplicate
       │           │        Detection
       ▼           ▼            ▼
   Topic        MCQ         Embedding
   Bloom        Rules       Search
   Difficulty
   Type
       │
       └──────────┬───────────┘
                  ▼
             Alignment
                  │
                  ▼
            LLM Explainability
                  │
                  ▼
          Result Schema Validation
                  │
                  ▼
          QuestionAiAnalysis
                  │
                  ▼
           Teacher Review
```

---

# 27. What I would fix first

## Phase 1 — Make the application boot

### Fix 1

Change:

```python
from ai.pipeline import analyze_question
```

to the new QIS architecture.

But don't simply rename it.

Refactor the whole `Analyze All` endpoint to use `AnalysisResult`.

---

### Fix 2

Replace all old parsing:

```python
res['topic']
res['bloom']
res['difficulty']
```

with:

```python
res['classification']['topic']
res['classification']['bloom']
res['classification']['difficulty']
```

---

### Fix 3

Make one persistence function:

```python
save_qis_analysis(question, result)
```

Used by:

```text
/analyze
/analyze-batch
/reanalyze
/bulk_questions
/analyze-all
```

---

# 28. Phase 2 — Fix the security contradiction

Do **not** do:

```text
encrypted ciphertext
      ↓
QIS
```

Choose:

```text
plaintext over HTTPS
      ↓
QIS
      ↓
encrypted-at-rest DB
```

and remove the misleading "zero knowledge" claim.

---

# 29. Phase 3 — Fix LLM reliability

Replace:

```python
if not llm_output:
    quality = 0.8
```

with:

```text
LLM unavailable
      ↓
quality.status = AI_UNAVAILABLE
      ↓
quality score = null
      ↓
review_required = true
```

This is mandatory.

---

# 30. Phase 4 — Connect AIJob

Your endpoint should become:

```http
POST /api/ai/questions/analyze-batch
```

Response:

```json
{
  "job_id": 123,
  "status": "QUEUED"
}
```

Then:

```http
GET /api/ai/questions/jobs/123
```

returns:

```json
{
  "status": "PROCESSING",
  "processed": 37,
  "total": 100
}
```

Finally:

```json
{
  "status": "COMPLETED",
  "processed": 100,
  "failed": 0
}
```

---

# 31. Phase 5 — Make QIS authoritative

There should be exactly one path for question intelligence:

```text
Create Question
      ↓
QIS
      ↓
Persist QIS Result
      ↓
Teacher Review
      ↓
Publish
```

Bulk:

```text
Bulk Import
      ↓
AIJob
      ↓
QIS
      ↓
Teacher Review
      ↓
Publish
```

Generated:

```text
LLM Generate
      ↓
QIS
      ↓
Validation
      ↓
Duplicate Check
      ↓
Teacher Review
      ↓
Question Bank
```

Reanalysis:

```text
Existing Question
      ↓
QIS
      ↓
New Analysis Version
      ↓
Teacher Review
```

---

# 32. Final corrected bug list

If I were converting your report into the **official engineering issue list**, I would use this:

### 🔴 P0 — Blocking

1. Legacy `analyze_question` import in `exam_intelligence_routes.py`.
2. Legacy QIS response-schema parsing.
3. QIS classification schema inconsistency (`label` vs `question_type`).
4. Database migration for `QuestionAiAnalysis`.
5. Encrypted ciphertext being sent into backend QIS, if encrypted payload path is active.
6. LLM failure producing fabricated `0.8 / GOOD`.
7. QIS analysis not persisted by `/analyze`.
8. QIS analysis not fully persisted by bulk upload.
9. `Analyze All` does not provide options/correct answer to QIS.
10. Generated questions bypass QIS validation.

### 🟠 P1 — High

11. Synchronous batch processing.
12. Unused `AIJob` architecture.
13. Duplicate detection recomputes all embeddings.
14. Duplicate detection restricted to current exam.
15. No persistent embedding/index workflow.
16. No versioned QIS analysis.
17. No unique/version strategy for `QuestionAiAnalysis`.
18. No atomic job-oriented Analyze All workflow.
19. Alignment only supports exact string MATCH/MISMATCH.
20. Weak final `AnalysisResult` validation.
21. No proper QIS teacher-review API workflow.

### 🟡 P2 — Medium

22. LaTeX/Markdown normalization.
23. Advanced MCQ semantic validation.
24. Better fallback classifier behavior.
25. Better LLM batching.
26. More sophisticated semantic topic alignment.
27. Model evaluation/monitoring.

---

## One particularly important correction to your original report

I would **not** say:

> "The QIS is technically non-functional because the ML team hasn't trained the models."

unless the uploaded `ml/inference.py` confirms that.

The `pipeline.py` clearly calls:

```python
qis_inference.predict_topic()
qis_inference.predict_bloom()
qis_inference.predict_difficulty()
qis_inference.predict_question_type()
```



So the correct engineering statement is:

> **The QIS pipeline is structurally integrated with an ML inference layer, but its production validity depends on whether `ml/inference.py` is backed by real trained models rather than stubs.**

That distinction matters when you present this project to your faculty or in your documentation.

### Bottom line

Your bug report identified the **four most obvious problems**, but after examining the uploaded code, I would expand it to approximately **27 actionable issues**.

The **first three things I would fix are**:

```text
1. Unify legacy + QIS pipeline
2. Make QIS persistence consistent
3. Remove synchronous/fake-fallback AI behavior
```

After those, the next architectural step should be to connect your existing `AIJob`, `QuestionEmbedding`, `QuestionAiAnalysis`, and `ExamAnalysis` models into a coherent QIS pipeline rather than adding more independent endpoints. 
```

That is **Question-Level AI Metadata Extraction**.

It is not yet:

```text
Teacher creates Exam
       ↓
Define Exam Blueprint
       ↓
Analyze entire Question Bank
       ↓
Classify all questions
       ↓
Detect duplicates
       ↓
Detect quality problems
       ↓
Check Bloom distribution
       ↓
Check difficulty distribution
       ↓
Recommend questions
       ↓
Generate missing fields
       ↓
Teacher reviews
       ↓
Publish Exam
```

That distinction is extremely important.

---

# 2. Why your screenshot's AI result is weak

The screenshot shows:

> **What is Data analysis?**

and the system gives approximately:

```text
Topic:          General IT
Difficulty:     Easy
Bloom:          Remember
AI Quality:     0.3/1.0
Duplicate Risk: 37%
```

This result is actually **explained directly by your current `ai_services.py`**.

## Bloom

The code does not use an ML classifier.

It creates keyword sets:

```text
evaluate → Evaluate
create   → Create
analyze  → Analyze
apply    → Apply
explain  → Understand
...
```

and selects the first matching category.

Since:

> "What is Data analysis?"

doesn't contain one of the configured trigger verbs, it remains:

```text
Remember
```

So the screenshot is not evidence of an intelligent Bloom classifier. It is evidence of a **rule-based classifier**.

---

# 3. Why "Data analysis" becomes General IT

Your topic classifier only contains four topic groups:

```text
Databases
Algorithms
Networking
Web Development
```

with manually defined keywords.

There is no:

```text
Data Science
Machine Learning
Artificial Intelligence
Statistics
Operating Systems
Computer Architecture
Cyber Security
Cloud Computing
...
```

Therefore:

```text
Data analysis
     ↓
No matching keyword
     ↓
General IT
```

This is a clear limitation.

### Fix

Don't hardcode the topic taxonomy in `ai_services.py`.

Instead:

```text
Subject / Course
       ↓
Topic taxonomy
       ↓
Embedding / classifier
       ↓
Topic
       ↓
Confidence
```

For example:

```json
{
  "topic": "Data Analysis",
  "confidence": 0.94
}
```

---

# 4. Why AI Quality = 0.3

This is another very important discovery.

The quality score is **not actually evaluating the quality of the question**.

The code essentially evaluates question length and presence of `?`.

For:

> What is Data analysis?

the question is short, so the system gives a low base score and then adds a small bonus for `?`.

That explains the screenshot's:

```text
AI Quality: 0.3/1.0
```

### This is not sufficient.

A useful Question Quality Engine should evaluate:

```text
Grammar
Clarity
Ambiguity
Completeness
Learning objective alignment
Bloom alignment
Options quality
Correct answer validity
Duplicate similarity
Difficulty
Distractor quality
Topic relevance
```

Then produce something like:

```text
Question Quality: 72/100

Issues:
⚠ Question is too broad
⚠ Learning objective unclear
⚠ Difficulty may be too low

Suggestion:
"Explain three major steps involved in data analysis."
```

That is useful to a teacher.

---

# 5. The biggest missing feature: Exam-Level AI Analysis

You correctly identified:

> "I can't apply the Bloom filter on all questions in the exam."

This is a **major architecture gap**.

The current model stores:

```text
topic
difficulty
bloom_level
ai_quality_score
```

for individual questions.

But the `Exam` model already contains an extremely important field:

```text
blueprint_json
```

which is intended to define expected topic/difficulty/Bloom distributions.

### The problem

The database has the foundation for an Exam Blueprint, but the current UI/AI workflow shown in the screenshot isn't using that capability.

You should exploit this.

---

# 6. What the next UI should look like

Instead of only:

```text
AI Analyze
```

you need an:

## `Analyze Entire Exam` button

For example:

```text
┌───────────────────────────────────────────────┐
│ Manage Questions — Exam #1                    │
│                                               │
│ [Analyze Entire Exam] [Generate Questions]    │
│ [Exam Blueprint]      [Check Balance]         │
└───────────────────────────────────────────────┘
```

Click:

### Analyze Entire Exam

Then:

```text
Analyzing 50 questions...

✓ Topic classification
✓ Bloom classification
✓ Difficulty estimation
✓ Duplicate detection
✓ Quality analysis
✓ MCQ option validation
✓ Blueprint comparison

Completed: 50/50
```

Then show:

```text
EXAM INTELLIGENCE REPORT
──────────────────────────────

Questions: 50

Bloom Distribution
Remember      40%
Understand    30%
Apply         20%
Analyze       10%
Evaluate       0%
Create         0%

⚠ Bloom imbalance detected

Difficulty
Easy          60%
Medium        30%
Hard          10%

⚠ Too many Easy questions

Duplicates
Potential duplicates: 4

Quality
Excellent: 12
Good:      25
Needs Review: 13
```

**This is the kind of output that makes the AI useful to the teacher.**

---

# 7. The intended Question Intelligence pipeline

Your next architecture should become:

```text
                    QUESTION BANK
                         │
                         ▼
                Question Normalizer
                         │
                         ▼
                 AI Question Engine
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
   Classifier        Embedding Engine    Quality Engine
       │                 │                 │
       ├─ Topic          ├─ Duplicate      ├─ Grammar
       ├─ Bloom          ├─ Similarity     ├─ Clarity
       └─ Difficulty     └─ Search         ├─ Ambiguity
                                           └─ Completeness
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                Question Metadata
                         │
                         ▼
                  Exam Analyzer
                         │
                         ▼
                  Exam Blueprint
                         │
                         ▼
                 Gap / Risk Analysis
                         │
                         ▼
                 Teacher Dashboard
```

---

# 8. AI should also auto-fill fields

You are correct about this.

Currently the teacher still has to manually provide:

```text
Option A
Option B
Option C
Option D
Correct Answer
```

The AI could assist with these.

For example:

### Teacher enters

> What is normalization in DBMS?

Click:

**Generate Question**

AI proposes:

```text
Question:
What is the primary purpose of normalization in a relational database?

A. Increase data redundancy
B. Reduce data redundancy
C. Increase duplicate records
D. Remove primary keys

Correct Answer:
B

Topic:
Databases

Bloom:
Understand

Difficulty:
Easy

Quality:
88%

Suggested Marks:
2
```

But **do not automatically publish these fields**.

The workflow should be:

```text
AI generates
      ↓
Teacher reviews
      ↓
Teacher edits if necessary
      ↓
Approve
      ↓
Save
```

This is important academically.

---

# 9. Don't make AI generate everything with one button

I recommend separating the operations.

### Button 1

**Analyze Question**

For existing question:

```text
Question
 ↓
Topic
Bloom
Difficulty
Quality
Duplicate
```

### Button 2

**Generate MCQ**

```text
Question/Topic
 ↓
Options
Correct answer
Explanation
```

### Button 3

**Improve Question**

```text
Existing question
 ↓
AI identifies problems
 ↓
Improved version
```

### Button 4

**Analyze Entire Exam**

```text
All questions
 ↓
Distribution
Quality
Duplicates
Blueprint
```

### Button 5

**Generate Missing Questions**

```text
Blueprint
+
Existing questions
 ↓
Identify gaps
 ↓
Generate candidates
```

This is much more powerful than making one giant AI button.

---

# 10. Your current AI architecture is partly correct

## What is correct

You have:

```text
React
   ↓
Flask REST API
   ↓
AI service
   ↓
ML/LLM
   ↓
SQLAlchemy
   ↓
Database
```

The Flask application uses blueprints for exams, questions, attempts, students, admin and analytics.

Your AI service contains:

```text
Rule-based question analysis
SentenceTransformer
Gemini
```

Your database also already has fields for:

```text
Bloom
Difficulty
Topic
Quality
Reference Answer
Rubric
Max Marks
AI marks
AI explanation
AI confidence
AI model
Teacher feedback
```

So **you do not need to throw away the project.**

---

# 11. But the architecture is not yet what we designed

The intended architecture was:

```text
                  EXAMINATION PLATFORM
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   Question Intelligence  Proctoring    Evaluation
          │                │                │
          ▼                ▼                ▼
       ML/NLP              CV             LLM
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                  Assessment Analytics
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
       Student          Question          Exam
       Analytics        Analytics        Analytics
```

The current implementation is closer to:

```text
              EXAM PLATFORM
                   │
       ┌───────────┼────────────┐
       ▼           ▼            ▼
    Question    Proctoring    Grading
       │           │            │
       ▼           ▼            ▼
    Heuristic    YOLO         Gemini
       │           │            │
       └───────────┼────────────┘
                   ▼
                Result
```

The **Assessment Intelligence layer is still missing/weak.**

---

# 12. Major AI problems in `ai_services.py`

## Problem 1 — Bloom is heuristic

The code explicitly describes itself as a heuristic and says a real production system would use a trained classifier.

### Fix

For MVP:

```text
SentenceTransformer
+
classification layer
```

or an LLM classification prompt.

For later:

```text
Labeled Question Dataset
        ↓
Transformer
        ↓
Fine-tuning
        ↓
Bloom Classifier
```

You do **not** need to train from scratch.

---

# 13. Problem 2 — Difficulty prediction is not real difficulty

Current:

```text
Bloom
+
word count
+
average word length
```

determines difficulty.

That's not sufficient.

### Better

Initially:

```text
AI predicted difficulty
```

Then after students attempt the exam:

```text
Actual correct rate
+
average time
+
discrimination
+
skip rate
```

becomes empirical difficulty.

So:

```text
Predicted Difficulty
        +
Actual Performance
        ↓
Final Question Difficulty
```

---

# 14. Problem 3 — Topic classifier is extremely limited

Only four topics are configured.

### Fix

Make topic configuration database-driven:

```text
Course
 ├── DBMS
 ├── Operating Systems
 ├── Algorithms
 ├── Networks
 ├── AI
 ├── ML
 └── Data Analytics
```

Then use semantic classification.

---

# 15. Problem 4 — `is_subjective` detection is unreliable

This line is particularly weak:

```text
"?" not in text
+
Bloom level
```

determines whether a question is subjective.

For example:

> Explain normalization?

could be subjective.

But:

> What is the difference between TCP and UDP?

could also be subjective.

### Fix

The question type should be explicitly selected or AI-classified:

```text
MCQ
TRUE_FALSE
SHORT_ANSWER
LONG_ANSWER
CODING
NUMERICAL
```

with confidence.

---

# 16. Problem 5 — Duplicate detection is computationally inefficient

The embedding implementation encodes:

```text
new question
+
all existing questions
```

during the request.

For:

```text
10 questions
```

fine.

For:

```text
10,000 questions
```

not ideal.

### Fix

Create:

```text
Question
 ↓
Embedding
 ↓
FAISS
```

and search Top-K.

```text
New question
 ↓
Embedding
 ↓
FAISS
 ↓
Top 5 similar
```

---

# 17. Problem 6 — Fallback can hide AI failure

If SentenceTransformer fails, it silently falls back to `difflib`.

That is dangerous from an analytics perspective because the UI can make it look like:

```text
AI duplicate detection
```

when actually:

```text
String similarity
```

was used.

### Fix

Return:

```json
{
  "similarity": 0.37,
  "method": "embedding",
  "model": "all-MiniLM-L6-v2"
}
```

or:

```json
{
  "similarity": 0.37,
  "method": "fallback",
  "model": null
}
```

---

# 18. Problem 7 — AI grading is still too dependent on LLM output

Gemini receives the question, reference answer, rubric and student answer.

That's a good foundation.

But you need:

```text
LLM
 ↓
JSON Schema
 ↓
Marks validation
 ↓
Confidence validation
 ↓
Rubric validation
 ↓
Teacher review
```

The current code does some JSON extraction and confidence-based review, which is an improvement, but it still lacks a strong schema/business validation layer.

---

# 19. Database architecture: surprisingly good foundation

Your `Question` model already contains the fields you need for the next stage:

```text
topic
difficulty
bloom_level
ai_quality_score
is_subjective
reference_answer
rubric
max_marks
```

And `Exam` already contains:

```text
blueprint_json
```

So I would **not redesign the database yet**.

Instead, add the missing intelligence tables.

---

# 20. Recommended new database tables

## `question_ai_analysis`

```text
id
question_id
model_name
model_version
topic
topic_confidence
bloom_level
bloom_confidence
difficulty
difficulty_confidence
quality_score
analysis_method
created_at
```

## `question_embedding`

```text
id
question_id
model_name
embedding
created_at
```

For MVP, FAISS can maintain the index separately rather than storing raw vectors in SQLite.

---

## `exam_analysis`

```text
id
exam_id
total_questions
quality_score
duplicate_count
bloom_distribution
difficulty_distribution
topic_distribution
blueprint_score
status
created_at
```

---

## `ai_job`

```text
id
job_type
exam_id
status
progress
model
started_at
completed_at
error
```

---

## `proctoring_event`

Your model already has the beginning of this concept.

Extend it with:

```text
confidence
evidence_path
frame_timestamp
bounding_box
model_name
```

---

# 21. Major backend security problems

There are also problems unrelated to AI that should be fixed before calling this production-ready.

## Hardcoded secret keys

Your configuration contains:

```text
SECRET_KEY = 'super-secret-hardcoded-key-123'
JWT_SECRET_KEY = 'super-secret-jwt-key-456'
```

This should be:

```python
SECRET_KEY = os.environ["SECRET_KEY"]
JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
```

with secrets stored in environment/secret management.

---

# 22. Authorization bug in student management

This is more serious.

`bulk_add` uses only:

```text
@auth_required
```

not:

```text
@teacher_required
```

Likewise delete student only requires authentication.

Therefore, based strictly on this file, **any authenticated user could potentially invoke these endpoints**.

### Fix

```python
@teacher_required
```

or preferably an explicit authorization policy:

```text
Admin → manage all students
Teacher → manage assigned students
Student → cannot manage students
```

---

# 23. Student deletion is dangerous

The code explicitly says:

> "For now, we just delete them."

and deletes the user.

But the student may have:

```text
ExamAttempt
Answer
Result
ProctoringEvent
AuditLog
```

associated with them.

### Fix

Use soft deletion:

```text
is_active = false
```

instead of deleting the record.

Academic records should remain auditable.

---

# 24. Authentication itself is okay as an MVP, but needs hardening

The middleware correctly:

```text
Authorization: Bearer token
 ↓
JWT decode
 ↓
Find User
 ↓
g.user
```

and has teacher/admin role decorators.

But the implementation uses the application's `SECRET_KEY` for JWT decoding rather than the separate `JWT_SECRET_KEY` configured in `config.py`.

That configuration should be made consistent.

---

# 25. Proctoring has a serious false-positive problem

Your camera service detects:

```text
person
phone
book
```

and uses the person's horizontal position to call something:

```text
looking_away
```

if they are outside a center box.

This is **not actual gaze detection**.

A student can turn their head slightly while still looking at the screen, and the system could flag them.

### Fix

Use:

```text
Face detection
 ↓
Facial landmarks
 ↓
Head pose estimation
 ↓
Gaze estimation
```

and treat it as a probabilistic signal, not an immediate cheating verdict.

---

# 26. Critical proctoring error: failures return `"safe"`

This is one of the most important bugs.

If image decoding fails:

```text
return "safe"
```

and if YOLO isn't available, the system can still leave the status as safe.

That means:

```text
AI failed
   ↓
System says SAFE
```

which is logically wrong.

### Fix

Use:

```text
AI_UNAVAILABLE
INVALID_FRAME
PROCESSING_ERROR
```

instead.

Never interpret:

```text
AI failure = student safe
```

---

# 27. Proctoring result isn't being converted into an event

You have a `ProctoringEvent` model, but the camera function returns only a status string:

```text
safe
missing
multiple
looking_away
phone_detected
book_detected
```

The next phase should convert:

```text
YOLO detection
 ↓
Proctoring Event
 ↓
Database
 ↓
Risk Engine
```

Example:

```json
{
  "event_type": "PHONE_DETECTED",
  "severity": "HIGH",
  "confidence": 0.92
}
```

---

# 28. Attempt architecture is currently extremely incomplete

`attempt_routes.py` currently has essentially only:

```text
GET /my_attempts
```

which returns exam IDs from results.

That is nowhere near the intended examination lifecycle.

You need endpoints such as:

```text
POST   /attempts/start
GET    /attempts/{id}
POST   /attempts/{id}/answer
POST   /attempts/{id}/proctor-event
POST   /attempts/{id}/submit
GET    /attempts/{id}/result
GET    /attempts/{id}/analytics
```

---

# 29. Your current architecture is missing the actual Analytics Engine

This is probably the biggest missing module relative to the project name.

You have an `analytics_bp` registered in `app.py`.

But the uploaded implementation does not include `analytics_routes.py`, so I **cannot verify its actual functionality from the files you provided**.

Therefore I would not claim that assessment analytics is implemented.

The next architecture should explicitly contain:

```text
analytics/
├── exam_analytics.py
├── question_analytics.py
├── student_analytics.py
├── integrity_analytics.py
└── blueprint_analyzer.py
```

---

# 30. What the next development phase should be

I recommend **not jumping directly into YOLO improvements or model training**.

Your immediate priority should be:

## Phase 1 — Question Intelligence

### Step 1

Make AI analysis work for **every question**.

```text
Manual question
+
CSV question
+
Existing question
```

all must go through the same pipeline.

---

### Step 2

Create:

```text
POST /api/exams/{exam_id}/questions/analyze-all
```

Pipeline:

```text
Exam
 ↓
Get all questions
 ↓
AI analysis
 ↓
Save metadata
 ↓
Return summary
```

---

### Step 3

Create:

```text
GET /api/exams/{exam_id}/question-analysis
```

Response:

```json
{
  "total": 50,
  "bloom": {
    "Remember": 20,
    "Understand": 15,
    "Apply": 10,
    "Analyze": 5
  },
  "difficulty": {
    "Easy": 30,
    "Medium": 15,
    "Hard": 5
  },
  "duplicates": 3,
  "needs_review": 8
}
```

---

# 31. Phase 2 — Exam Blueprint

Teacher selects:

```text
Exam: Data Structures

Questions: 30

Difficulty:
Easy: 20%
Medium: 50%
Hard: 30%

Bloom:
Remember: 10%
Understand: 20%
Apply: 30%
Analyze: 25%
Evaluate: 15%
```

Store this in your existing:

```text
Exam.blueprint_json
```

field.

Then compare:

```text
Required Distribution
        vs
Actual Distribution
```

---

# 32. Phase 3 — Question Recommendations

Now the system can say:

```text
Exam requires:

Analyze:
8 questions

Current:
3 questions

Missing:
5 questions
```

Then:

```text
[Generate 5 Candidate Questions]
```

AI creates candidates.

Teacher:

```text
Approve
Edit
Reject
```

---

# 33. Phase 4 — Better Question AI

Replace:

```text
keyword rules
```

with:

```text
Question
 ↓
LLM / embedding classifier
 ↓
Structured JSON
```

Example:

```json
{
  "topic": "Data Analysis",
  "topic_confidence": 0.94,
  "bloom_level": "Understand",
  "bloom_confidence": 0.89,
  "difficulty": "Easy",
  "difficulty_confidence": 0.81,
  "quality_score": 0.86,
  "question_type": "MCQ"
}
```

You can still use the heuristic implementation as a fallback.

---

# 34. Phase 5 — Auto-fill

For an incomplete question:

```text
Question
 ↓
AI
 ├── Topic
 ├── Bloom
 ├── Difficulty
 ├── Question Type
 ├── Option A
 ├── Option B
 ├── Option C
 ├── Option D
 ├── Correct Answer
 ├── Explanation
 └── Suggested Marks
```

But:

> **AI-generated fields should be "Suggested", not automatically trusted.**

---

# 35. Phase 6 — Exam Intelligence Dashboard

This should become the teacher's major AI screen.

```text
┌─────────────────────────────────────────────┐
│ EXAM INTELLIGENCE                           │
├─────────────────────────────────────────────┤
│ Questions: 50       Quality: 78/100         │
│                                             │
│ Bloom Distribution                          │
│ █████ Remember       30%                    │
│ ████ Understand      25%                    │
│ ███ Apply            20%                    │
│ ██ Analyze           15%                    │
│ █ Evaluate           10%                    │
│                                             │
│ Difficulty                                  │
│ Easy       40%                              │
│ Medium     40%                              │
│ Hard       20%                              │
│                                             │
│ ⚠ 3 possible duplicates                    │
│ ⚠ 7 questions need review                  │
│ ⚠ Analyze questions below target            │
│                                             │
│ [Fix Automatically] [Review Issues]         │
└─────────────────────────────────────────────┘
```

Now the teacher gets **actionable intelligence**, not just four dropdown values.

---

# 36. Priority table for your next development

| Priority | Feature                      |    Current | Action         |
| -------- | ---------------------------- | ---------: | -------------- |
| 🔴 P0    | Analyze all exam questions   |         ❌ | Build          |
| 🔴 P0    | Bulk CSV → AI pipeline      |    ❌/weak | Build          |
| 🔴 P0    | Exam Blueprint               |  DB exists | Implement      |
| 🔴 P0    | Bloom distribution           |         ❌ | Implement      |
| 🔴 P0    | Difficulty distribution      |         ❌ | Implement      |
| 🔴 P0    | Duplicate report             |    Partial | Implement      |
| 🔴 P0    | Question quality report      |       Weak | Redesign       |
| 🔴 P0    | AI confidence                |    Partial | Add everywhere |
| 🔴 P0    | Teacher review               |    Partial | Strengthen     |
| 🟠 P1    | Auto-fill topic              |       Weak | Improve        |
| 🟠 P1    | Auto-fill Bloom              |       Weak | Improve        |
| 🟠 P1    | Auto-fill difficulty         |       Weak | Improve        |
| 🟠 P1    | Generate MCQ options         |         ❌ | Build          |
| 🟠 P1    | Generate correct answer      |         ❌ | Build          |
| 🟠 P1    | Improve question             |         ❌ | Build          |
| 🟠 P1    | Semantic duplicate search    |    Partial | FAISS          |
| 🟠 P1    | Question type classification |       Weak | Build          |
| 🟡 P2    | Actual question difficulty   |         ❌ | Analytics      |
| 🟡 P2    | Question discrimination      |         ❌ | Analytics      |
| 🟡 P2    | Student analytics            | ❌/unknown | Build          |
| 🟡 P2    | Learning recommendations     | ❌/unknown | Build          |
| 🟡 P2    | Proctoring risk engine       |         ❌ | Build          |
| 🟡 P2    | Proctoring evidence          |    Partial | Build          |
| 🟡 P2    | Audio intelligence           |         ❌ | Optional       |

---

# 37. One important thing: don't train a model yet

For this stage, **do not start training your own Bloom/Difficulty model**.

Your current problem is architectural:

```text
AI analysis
       ↓
single question
       ↓
metadata
       ↓
database
```

You need:

```text
AI analysis
       ↓
question bank
       ↓
exam blueprint
       ↓
distribution analysis
       ↓
recommendation
       ↓
teacher decision
```

First make the pipeline useful.

Then improve the model.

For your 4–5 month project, I would use:

```text
                 AI LAYER

Question Classification
        ↓
SentenceTransformer / LLM

Duplicate Detection
        ↓
SentenceTransformer + FAISS

Question Generation
        ↓
Gemini API

Subjective Evaluation
        ↓
Gemini + Rubric

Proctoring
        ↓
YOLO + OpenCV
```

No model-from-scratch training is necessary for the MVP.

---

# 38. Final architecture you should implement next

```text
                         TEACHER
                            │
                            ▼
                    EXAM CREATION
                            │
                            ▼
                    EXAM BLUEPRINT
                            │
            ┌───────────────┴────────────────┐
            │                                │
            ▼                                ▼
      EXISTING QUESTIONS                AI GENERATION
            │                                │
            └───────────────┬────────────────┘
                            ▼
                  QUESTION INTELLIGENCE
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
    Topic AI             Bloom AI           Difficulty AI
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                    Quality Analyzer
                            │
                  ┌─────────┴─────────┐
                  ▼                   ▼
             Duplicate             MCQ Validator
             Detection             / Generator
                  │                   │
                  └─────────┬─────────┘
                            ▼
                    EXAM ANALYZER
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
             Bloom       Difficulty    Topic
            Balance       Balance     Balance
                │           │           │
                └───────────┼───────────┘
                            ▼
                     AI INSIGHTS
                            │
                            ▼
                    TEACHER REVIEW
                            │
                      APPROVE / EDIT
                            │
                            ▼
                       PUBLISH EXAM
```

Then during examination:

```text
STUDENT
   │
   ▼
EXAM ATTEMPT
   │
   ├──────────────► ANSWER DATA
   │                    │
   │                    ▼
   │               AI EVALUATION
   │
   ├──────────────► WEBCAM
   │                    │
   │                    ▼
   │              YOLO / CV MODEL
   │                    │
   │                    ▼
   │              PROCTOR EVENTS
   │
   └──────────────► BEHAVIOR EVENTS
                        │
                        ▼
                  RISK ENGINE
                        │
                        ▼
                 ASSESSMENT DATA
                        │
                        ▼
                 ANALYTICS ENGINE
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
   Student Report   Question Report   Exam Report
```

---

## Bottom line

**Your current project is not wrong. It is simply one or two architectural levels below the project you are trying to present.**

The current interface is essentially:

> **"AI-assisted question metadata entry."**

The target should be:

> **"AI-assisted assessment design and intelligence."**

The most important next change is therefore **not adding another model**. It is changing the workflow from:

**`AI Analyze → fill fields → Add Question`**

to:

**`Exam Blueprint → Analyze All Questions → Detect Problems → Generate/Recommend → Compare Against Blueprint → Teacher Review → Publish → Analyze Actual Student Performance`**

Your existing `Exam.blueprint_json`, question AI fields, rubric fields, AI evaluation fields, question versioning, review history, audit log, and proctoring event model already provide a surprisingly good foundation for that transition.

**That should be the next phase of development.**
