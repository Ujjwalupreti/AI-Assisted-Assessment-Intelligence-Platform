from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    enrollment_id = Column(String(20), unique=True, nullable=True) 
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(500)) 
    role = Column(String(20), default='student') 
    is_active = Column(Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class AIJob(Base):
    __tablename__ = 'ai_job'
    id = Column(Integer, primary_key=True)
    job_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=False)
    status = Column(String(50))
    result_data = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime)
    completed_at = Column(DateTime)
    total = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    successful = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    failed_question_ids = Column(Text)

class Exam(Base):
    __tablename__ = 'exam'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True) 
    password_hash = Column(String(500), nullable=True) 
    is_visible = Column(Boolean, default=True)
    blueprint_json = Column(Text, nullable=True)
    creator_id = Column(Integer, ForeignKey('user.id'))
    creation_mode = Column(String(50), default='manual')
    
    # Exam Settings
    cutoff_type = Column(String(20), default='percentage')
    cutoff_value = Column(Float, default=50.0)
    description = Column(Text)
    tags = Column(Text)
    
    # Pooling & Slotting
    slotting_enabled = Column(Boolean, default=False)
    pooling_enabled = Column(Boolean, default=False)
    pool_size = Column(Integer)
    questions_per_student = Column(Integer)
    randomize_questions = Column(Boolean, default=True)

    def set_password(self, pw):
        if pw:
            self.password_hash = generate_password_hash(pw)
        else:
            self.password_hash = None

    def check_password(self, pw):
        if not self.password_hash:
            return True
        if not pw:
            return False
        return check_password_hash(self.password_hash, pw)

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Question(Base):
    __tablename__ = 'question'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'), nullable=False)
    text = Column(Text, nullable=False)
    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)
    correct_option = Column(String(255))
    topic = Column(String(100))
    difficulty = Column(String(20))
    bloom_level = Column(String(50))
    ai_quality_score = Column(Float)
    is_subjective = Column(Boolean, default=False)
    reference_answer = Column(Text)
    rubric = Column(Text)
    max_marks = Column(Float)
    is_archived = Column(Boolean, default=False)
    subject = Column(String(100))
    subtopic = Column(String(100))
    question_type = Column(String(50), default='MCQ')
    created_by = Column(Integer, ForeignKey('user.id'))
    status = Column(String(50), default='ACTIVE')
    created_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50), default='MANUAL')
    duplicate_status = Column(String(50), default='SAFE')

class Result(Base):
    __tablename__ = 'result'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'))
    student_id = Column(Integer, ForeignKey('user.id'))
    score = Column(Float)
    total_marks = Column(Float)
    total_questions = Column(Integer)
    date_taken = Column(DateTime, default=datetime.utcnow)
    tab_switches = Column(Integer, default=0)
    audio_warnings = Column(Integer, default=0)
    id_card_url = Column(String(500))
    face_photo_url = Column(String(500))
    mid_exam_photo_url = Column(String(500))
    integrity_score = Column(Float, default=100.0)
    integrity_label = Column(String(50), default="GOOD")
    teacher_decision = Column(String(50), default="PENDING")

class ExamAttempt(Base):
    __tablename__ = 'exam_attempt'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(50))
    assigned_questions_json = Column(Text)

class ExamAnalysis(Base):
    __tablename__ = 'exam_analysis'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'), nullable=False)
    total_questions = Column(Integer)
    quality_score = Column(Float)
    duplicate_count = Column(Integer)
    bloom_distribution = Column(Text)
    difficulty_distribution = Column(Text)
    topic_distribution = Column(Text)
    blueprint_score = Column(Float)
    status = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class Answer(Base):
    __tablename__ = 'answer'
    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey('exam_attempt.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    selected_option = Column(String(255))
    answer_text = Column(Text)
    is_correct = Column(Boolean)
    marks_awarded = Column(Float)
    ai_suggested_marks = Column(Float)
    ai_explanation = Column(Text)
    ai_confidence = Column(Float)
    ai_model_name = Column(String(100))
    review_status = Column(String(50))
    teacher_feedback = Column(Text)

class QuestionVersion(Base):
    __tablename__ = 'question_version'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    version_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)
    correct_option = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class ProctoringEvent(Base):
    __tablename__ = 'proctoring_event'
    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey('exam_attempt.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    confidence = Column(Float)
    frame_timestamp = Column(String(50))
    bounding_box = Column(String(255))
    model_name = Column(String(100))
    duration_ms = Column(Integer, default=0)
    evidence_url = Column(Text) 
    metadata_json = Column(Text)

class QuestionAiAnalysis(Base):
    __tablename__ = 'question_ai_analysis'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    model_name = Column(String(100))
    model_version = Column(String(50))
    topic_label = Column(String(100))
    topic_confidence = Column(Float)
    bloom_label = Column(String(50))
    bloom_confidence = Column(Float)
    difficulty_label = Column(String(20))
    difficulty_confidence = Column(Float)
    quality_score = Column(Float)
    question_type = Column(String(50))
    question_type_confidence = Column(Float)
    quality_issues = Column(Text)
    quality_suggestions = Column(Text)
    duplicate_risk = Column(Float)
    review_status = Column(String(50))
    analysis_method = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    analysis_json = Column(Text)
    teacher_review_status = Column(String(50), default='PENDING')
    teacher_accepted_at = Column(DateTime)
    is_current = Column(Boolean, default=True)
    quality_status = Column(String(50))
    clarity_score = Column(Float)
    completeness_score = Column(Float)
    specificity_score = Column(Float)
    duplicate_similarity = Column(Float)
    analysis_source = Column(String(50))
    analysis_status = Column(String(50))
    teacher_override = Column(Boolean, default=False)
    updated_at = Column(DateTime)

class QuestionEmbedding(Base):
    __tablename__ = 'question_embedding'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    embedding_data = Column(Text, nullable=False)
    embedding_model = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding_dimension = Column(Integer)

class EvaluationReview(Base):
    __tablename__ = 'evaluation_review'
    id = Column(Integer, primary_key=True)
    answer_id = Column(Integer, ForeignKey('answer.id'), nullable=False)
    teacher_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    original_marks = Column(Float, nullable=False)
    new_marks = Column(Float, nullable=False)
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class CourseDocument(Base):
    __tablename__ = 'course_document'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content_text = Column(Text, nullable=False)
    course_name = Column(String(100))
    created_by = Column(Integer, ForeignKey('user.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

class ExamTimeSlot(Base):
    __tablename__ = 'exam_time_slot'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'), nullable=False)
    slot_name = Column(String(100), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class StudentExamTimeSlot(Base):
    __tablename__ = 'student_exam_time_slot'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    slot_id = Column(Integer, ForeignKey('exam_time_slot.id'), nullable=False)

class DocumentChunk(Base):
    __tablename__ = 'document_chunk'
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('course_document.id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=False)
    model_name = Column(String(100))

class DuplicateGroup(Base):
    __tablename__ = 'duplicate_group'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'))
    status = Column(String(50), default='PENDING')
    similarity_threshold = Column(Float, default=0.85)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    resolved_by = Column(Integer, ForeignKey('user.id'))

class QuestionDuplicate(Base):
    __tablename__ = 'question_duplicate'
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('duplicate_group.id', ondelete='CASCADE'), nullable=False)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    similarity_score = Column(Float, nullable=False)
    is_primary = Column(Boolean, default=False)
    status = Column(String(50), default='FLAGGED')

class AssessmentBlueprint(Base):
    __tablename__ = 'assessment_blueprint'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'), nullable=False)
    blueprint_json = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey('user.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

class ExamSlot(Base):
    __tablename__ = 'exam_slot'
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exam.id'), nullable=False)
    slot_number = Column(Integer, nullable=False)
    total_marks = Column(Float, default=0.0)
    quality_score = Column(Float)
    bloom_distribution = Column(Text)
    difficulty_distribution = Column(Text)
    topic_distribution = Column(Text)
    blueprint_match_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExamSlotQuestion(Base):
    __tablename__ = 'exam_slot_question'
    id = Column(Integer, primary_key=True)
    slot_id = Column(Integer, ForeignKey('exam_slot.id', ondelete='CASCADE'), nullable=False)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    order = Column(Integer, default=0)
