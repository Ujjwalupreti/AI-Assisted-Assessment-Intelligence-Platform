import time
import json
from collections import defaultdict
from models import ProctoringEvent, Result, ExamAttempt
from sqlalchemy.orm import Session

# In-memory store for lightweight temporal aggregation
# Dictionary structure:
# attempt_id -> {
#    "last_face_seen": timestamp,
#    "face_missing_start": timestamp,
#    "looking_away_start": timestamp,
#    "phone_detection_count": int,
#    "phone_first_seen": timestamp,
#    ...
# }
_attempt_states = defaultdict(lambda: {
    "last_face_seen": time.time(),
    "face_missing_start": None,
    "looking_away_start": None,
    "phone_detection_count": 0,
    "phone_first_seen": None,
    "book_detection_count": 0,
    "book_first_seen": None,
    "multiple_faces_count": 0,
    "multiple_faces_first_seen": None
})

# Thresholds
FACE_MISSING_THRESHOLD_SEC = 3.0
LOOKING_AWAY_THRESHOLD_SEC = 3.0
PHONE_PERSISTENCE_COUNT = 3      # frames needed to trigger event
BOOK_PERSISTENCE_COUNT = 3       # frames needed to trigger event
MULTIPLE_FACES_COUNT = 3         # frames needed to trigger event

def process_frame_detections(attempt_id: int, detections: dict, db: Session, base64_image: str = None) -> list:
    """
    Takes frame-level detections and applies temporal logic to generate meaningful events.
    """
    state = _attempt_states[attempt_id]
    current_time = time.time()
    events_generated = []
    
    face_count = detections.get("face_count", 1)
    objects = detections.get("objects", [])  # list of dicts {"class": "phone", "conf": 0.9}
    looking_away = detections.get("looking_away", False)

    # 1. Face Missing Logic
    if face_count == 0:
        if state["face_missing_start"] is None:
            state["face_missing_start"] = current_time
        elif (current_time - state["face_missing_start"]) >= FACE_MISSING_THRESHOLD_SEC:
            events_generated.append(create_event(attempt_id, "FACE_MISSING", "MEDIUM", 1.0, current_time - state["face_missing_start"], base64_image))
            state["face_missing_start"] = None # Reset after triggering
    else:
        state["face_missing_start"] = None
        state["last_face_seen"] = current_time

    # 2. Looking Away Logic
    if looking_away:
        if state["looking_away_start"] is None:
            state["looking_away_start"] = current_time
        elif (current_time - state["looking_away_start"]) >= LOOKING_AWAY_THRESHOLD_SEC:
            events_generated.append(create_event(attempt_id, "LOOKING_AWAY", "LOW", 1.0, current_time - state["looking_away_start"], base64_image))
            state["looking_away_start"] = None # Reset after triggering
    else:
        state["looking_away_start"] = None

    # 3. Multiple Faces Logic
    if face_count > 1:
        if state["multiple_faces_first_seen"] is None:
             state["multiple_faces_first_seen"] = current_time
        state["multiple_faces_count"] += 1
        
        if state["multiple_faces_count"] >= MULTIPLE_FACES_COUNT:
            events_generated.append(create_event(attempt_id, "MULTIPLE_FACES", "HIGH", 1.0, current_time - state["multiple_faces_first_seen"], base64_image))
            state["multiple_faces_count"] = 0
            state["multiple_faces_first_seen"] = None
    else:
        state["multiple_faces_count"] = 0
        state["multiple_faces_first_seen"] = None

    # 4. Object Detection (Phone/Book)
    phone_det = next((obj for obj in objects if obj["class"] == "phone"), None)
    book_det = next((obj for obj in objects if obj["class"] == "book"), None)

    if phone_det:
        if state["phone_first_seen"] is None:
            state["phone_first_seen"] = current_time
        state["phone_detection_count"] += 1
        if state["phone_detection_count"] >= PHONE_PERSISTENCE_COUNT:
            events_generated.append(create_event(attempt_id, "PHONE_DETECTED", "HIGH", phone_det["conf"], current_time - state["phone_first_seen"], base64_image))
            state["phone_detection_count"] = 0
            state["phone_first_seen"] = None
    else:
        state["phone_detection_count"] = 0
        state["phone_first_seen"] = None

    if book_det:
        if state["book_first_seen"] is None:
            state["book_first_seen"] = current_time
        state["book_detection_count"] += 1
        if state["book_detection_count"] >= BOOK_PERSISTENCE_COUNT:
            events_generated.append(create_event(attempt_id, "BOOK_DETECTED", "MEDIUM", book_det["conf"], current_time - state["book_first_seen"], base64_image))
            state["book_detection_count"] = 0
            state["book_first_seen"] = None
    else:
        state["book_detection_count"] = 0
        state["book_first_seen"] = None

    # Save events to database
    for evt in events_generated:
        db.add(evt)
    
    if events_generated:
        db.commit()

    return events_generated

def create_event(attempt_id, event_type, severity, confidence, duration_sec, evidence_base64=None):
    event = ProctoringEvent(
        attempt_id=attempt_id,
        event_type=event_type,
        severity=severity,
        confidence=confidence,
        duration_ms=int(duration_sec * 1000),
        evidence_url=evidence_base64, # Using DB for evidence storage as per MVP
        metadata_json=json.dumps({"notes": "Auto-generated by temporal aggregator"})
    )
    return event

def calculate_integrity_score(db: Session, attempt_id: int):
    events = db.query(ProctoringEvent).filter_by(attempt_id=attempt_id).all()
    
    score = 100.0
    
    # Simple weighted rules
    # High risk = -20
    # Medium risk = -10
    # Low risk = -5
    
    for evt in events:
        if evt.severity == 'HIGH':
            score -= 20
        elif evt.severity == 'MEDIUM':
            score -= 10
        elif evt.severity == 'LOW':
            score -= 5
            
    # Clamp score
    if score < 0:
        score = 0
        
    label = "GOOD"
    if score < 40:
        label = "CRITICAL REVIEW"
    elif score < 60:
        label = "HIGH RISK"
    elif score < 80:
        label = "REVIEW REQUIRED"
    elif score <= 100:
        label = "LOW CONCERN"
        
    return score, label
