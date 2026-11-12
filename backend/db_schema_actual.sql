CREATE TABLE user (
	id INTEGER NOT NULL, 
	enrollment_id VARCHAR(20), 
	username VARCHAR(80) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(500), 
	role VARCHAR(20), 
	is_active BOOLEAN, 
	PRIMARY KEY (id), 
	UNIQUE (enrollment_id), 
	UNIQUE (username), 
	UNIQUE (email)
)
CREATE TABLE ai_job (
	id INTEGER NOT NULL, 
	job_type VARCHAR(50) NOT NULL, 
	target_id INTEGER NOT NULL, 
	status VARCHAR(50), 
	result_data TEXT, 
	error_message TEXT, 
	created_at DATETIME, 
	completed_at DATETIME, total INTEGER DEFAULT 0, processed INTEGER DEFAULT 0, successful INTEGER DEFAULT 0, failed INTEGER DEFAULT 0, failed_question_ids TEXT, 
	PRIMARY KEY (id)
)
CREATE TABLE exam (
	id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	duration_minutes INTEGER NOT NULL, 
	start_date DATETIME NOT NULL, 
	end_date DATETIME, 
	password_hash VARCHAR(500), 
	is_visible BOOLEAN, 
	blueprint_json TEXT, 
	creator_id INTEGER, creation_mode VARCHAR(50) DEFAULT 'manual', 
	PRIMARY KEY (id), 
	FOREIGN KEY(creator_id) REFERENCES user (id)
)
CREATE TABLE audit_log (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	action VARCHAR(255) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id INTEGER NOT NULL, 
	details TEXT, 
	timestamp DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
)
CREATE TABLE question (
	id INTEGER NOT NULL, 
	exam_id INTEGER NOT NULL, 
	text TEXT NOT NULL, 
	option_a TEXT, 
	option_b TEXT, 
	option_c TEXT, 
	option_d TEXT, 
	correct_option VARCHAR(255), 
	topic VARCHAR(100), 
	difficulty VARCHAR(20), 
	bloom_level VARCHAR(50), 
	ai_quality_score FLOAT, 
	is_subjective BOOLEAN, 
	reference_answer TEXT, 
	rubric TEXT, 
	max_marks FLOAT, is_archived BOOLEAN DEFAULT 0, subject VARCHAR(100), subtopic VARCHAR(100), question_type VARCHAR(50) DEFAULT 'MCQ', created_by INTEGER REFERENCES user(id), status VARCHAR(50) DEFAULT 'ACTIVE', created_at DATETIME, source VARCHAR(50) DEFAULT 'MANUAL', duplicate_status VARCHAR(50) DEFAULT 'SAFE', 
	PRIMARY KEY (id), 
	FOREIGN KEY(exam_id) REFERENCES exam (id)
)
CREATE TABLE result (
	id INTEGER NOT NULL, 
	exam_id INTEGER, 
	student_id INTEGER, 
	score FLOAT, 
	total_marks FLOAT, 
	total_questions INTEGER, 
	date_taken DATETIME, 
	tab_switches INTEGER, 
	audio_warnings INTEGER, 
	id_card_url VARCHAR(500), 
	face_photo_url VARCHAR(500), 
	mid_exam_photo_url VARCHAR(500), 
	PRIMARY KEY (id), 
	FOREIGN KEY(exam_id) REFERENCES exam (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
)
CREATE TABLE exam_attempt (
	id INTEGER NOT NULL, 
	exam_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	start_time DATETIME, 
	end_time DATETIME, 
	status VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(exam_id) REFERENCES exam (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
)
CREATE TABLE exam_analysis (
	id INTEGER NOT NULL, 
	exam_id INTEGER NOT NULL, 
	total_questions INTEGER, 
	quality_score FLOAT, 
	duplicate_count INTEGER, 
	bloom_distribution TEXT, 
	difficulty_distribution TEXT, 
	topic_distribution TEXT, 
	blueprint_score FLOAT, 
	status VARCHAR(50), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(exam_id) REFERENCES exam (id)
)
CREATE TABLE answer (
	id INTEGER NOT NULL, 
	attempt_id INTEGER NOT NULL, 
	question_id INTEGER NOT NULL, 
	selected_option VARCHAR(255), 
	answer_text TEXT, 
	is_correct BOOLEAN, 
	marks_awarded FLOAT, 
	ai_suggested_marks FLOAT, 
	ai_explanation TEXT, 
	ai_confidence FLOAT, 
	ai_model_name VARCHAR(100), 
	review_status VARCHAR(50), 
	teacher_feedback TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(attempt_id) REFERENCES exam_attempt (id), 
	FOREIGN KEY(question_id) REFERENCES question (id)
)
CREATE TABLE question_version (
	id INTEGER NOT NULL, 
	question_id INTEGER NOT NULL, 
	version_number INTEGER NOT NULL, 
	text TEXT NOT NULL, 
	option_a TEXT, 
	option_b TEXT, 
	option_c TEXT, 
	option_d TEXT, 
	correct_option VARCHAR(255), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(question_id) REFERENCES question (id)
)
CREATE TABLE proctoring_event (
	id INTEGER NOT NULL, 
	attempt_id INTEGER NOT NULL, 
	timestamp DATETIME, 
	event_type VARCHAR(100) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	confidence FLOAT, 
	frame_timestamp VARCHAR(50), 
	bounding_box VARCHAR(255), 
	model_name VARCHAR(100), 
	PRIMARY KEY (id), 
	FOREIGN KEY(attempt_id) REFERENCES exam_attempt (id)
)
CREATE TABLE question_ai_analysis (
	id INTEGER NOT NULL, 
	question_id INTEGER NOT NULL, 
	model_name VARCHAR(100), 
	model_version VARCHAR(50), 
	topic_label VARCHAR(100), 
	topic_confidence FLOAT, 
	bloom_label VARCHAR(50), 
	bloom_confidence FLOAT, 
	difficulty_label VARCHAR(20), 
	difficulty_confidence FLOAT, 
	quality_score FLOAT, 
	question_type VARCHAR(50), 
	question_type_confidence FLOAT, 
	quality_issues TEXT, 
	quality_suggestions TEXT, 
	duplicate_risk FLOAT, 
	review_status VARCHAR(50), 
	analysis_method VARCHAR(100), 
	created_at DATETIME, analysis_json TEXT, teacher_review_status VARCHAR(50) DEFAULT 'PENDING', teacher_accepted_at DATETIME, is_current BOOLEAN DEFAULT 1, quality_status VARCHAR(50), clarity_score FLOAT, completeness_score FLOAT, specificity_score FLOAT, duplicate_similarity FLOAT, analysis_source VARCHAR(50), analysis_status VARCHAR(50), teacher_override BOOLEAN DEFAULT 0, updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(question_id) REFERENCES question (id)
)
CREATE TABLE question_embedding (
	id INTEGER NOT NULL, 
	question_id INTEGER NOT NULL, 
	embedding_data TEXT NOT NULL, 
	embedding_model VARCHAR(100) NOT NULL, 
	created_at DATETIME, embedding_dimension INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(question_id) REFERENCES question (id)
)
CREATE TABLE evaluation_review (
	id INTEGER NOT NULL, 
	answer_id INTEGER NOT NULL, 
	teacher_id INTEGER NOT NULL, 
	original_marks FLOAT NOT NULL, 
	new_marks FLOAT NOT NULL, 
	comments TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(answer_id) REFERENCES answer (id), 
	FOREIGN KEY(teacher_id) REFERENCES user (id)
)
CREATE TABLE course_document (
	id INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	content_text TEXT NOT NULL, 
	course_name VARCHAR(100), 
	created_by INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES user (id)
)
CREATE TABLE document_chunk (
	id INTEGER NOT NULL, 
	document_id INTEGER NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	chunk_text TEXT NOT NULL, 
	embedding_json TEXT NOT NULL, 
	model_name VARCHAR(100), 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES course_document (id) ON DELETE CASCADE
)
CREATE TABLE duplicate_group (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        exam_id INTEGER REFERENCES exam(id),
                        status VARCHAR(50) DEFAULT 'PENDING',
                        similarity_threshold FLOAT DEFAULT 0.85,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        resolved_at DATETIME,
                        resolved_by INTEGER REFERENCES user(id)
                    )
CREATE TABLE sqlite_sequence(name,seq)
CREATE TABLE question_duplicate (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id INTEGER NOT NULL REFERENCES duplicate_group(id) ON DELETE CASCADE,
                        question_id INTEGER NOT NULL REFERENCES question(id),
                        similarity_score FLOAT NOT NULL,
                        is_primary BOOLEAN DEFAULT 0,
                        status VARCHAR(50) DEFAULT 'FLAGGED'
                    )
CREATE TABLE assessment_blueprint (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        exam_id INTEGER NOT NULL REFERENCES exam(id),
                        blueprint_json TEXT NOT NULL,
                        created_by INTEGER REFERENCES user(id),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
CREATE TABLE exam_slot (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        exam_id INTEGER NOT NULL REFERENCES exam(id),
                        slot_number INTEGER NOT NULL,
                        total_marks FLOAT DEFAULT 0.0,
                        quality_score FLOAT,
                        bloom_distribution TEXT,
                        difficulty_distribution TEXT,
                        topic_distribution TEXT,
                        blueprint_match_score FLOAT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
CREATE TABLE exam_slot_question (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slot_id INTEGER NOT NULL REFERENCES exam_slot(id) ON DELETE CASCADE,
                        question_id INTEGER NOT NULL REFERENCES question(id),
                        "order" INTEGER DEFAULT 0
                    )