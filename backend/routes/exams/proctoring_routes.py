from fastapi import APIRouter, Depends, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from auth_middleware import get_current_user
from models import User
import os
import base64
import numpy as np

# cv2, numpy, and YOLO are imported lazily inside analyze_frame only
# to avoid blocking all API routes during startup
_yolo_model = None
_face_cascade = None

def _get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'yolov8n.pt')
            _yolo_model = YOLO(model_path)
        except Exception as e:
            print("WARNING: Error loading YOLO model. Object detection disabled:", e)
            _yolo_model = False
    return _yolo_model if _yolo_model else None

def _get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        import cv2
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    return _face_cascade

proctor_bp = APIRouter()

# ==========================================================
# 🚨 BULLETPROOF AI PROCTORING ENDPOINT (DEVICE-INDEPENDENT)
# ==========================================================
from ai.proctoring.proctoring_core import process_frame_detections

@proctor_bp.post('/analyze_frame')
def analyze_frame(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        import cv2
        import numpy as np
        
        if not data or 'frame' not in data:
            return JSONResponse(status_code=200, content={"status": "safe", "events": []})
            
        base64_frame = data.get('frame')
        attempt_id = data.get('attempt_id')
        if not base64_frame or not attempt_id:
            return JSONResponse(status_code=200, content={"status": "safe", "events": []})
            
        # Decode Base64 to OpenCV image
        header, encoded = base64_frame.split(",", 1)
        encoded = encoded.strip()
        encoded += "=" * ((4 - len(encoded) % 4) % 4)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return JSONResponse(status_code=200, content={"status": "safe", "events": []})

        high_res_img = img.copy()

        # Resize for Face Detection
        original_height, original_width = img.shape[:2]
        max_width = 640
        if original_width > max_width:
            scale = max_width / original_width
            img = cv2.resize(img, (max_width, int(original_height * scale)))

        height, width, _ = img.shape
        center_x_min = width // 4
        center_x_max = 3 * (width // 4)

        # 🧠 FACE DETECTION
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        face_cascade = _get_face_cascade()
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=4, minSize=(30, 30))

        looking_away = False
        for (x, y, w, h) in faces:
            face_center_x = x + (w // 2)
            if face_center_x < center_x_min or face_center_x > center_x_max:
                looking_away = True

        # 📱 YOLO OBJECT DETECTION
        objects = []
        yolo_model = _get_yolo_model()
        if yolo_model:
            results = yolo_model.predict(high_res_img, classes=[67, 73], conf=0.15, verbose=False)
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    if cls_id == 67:
                        objects.append({"class": "phone", "conf": conf})
                    elif cls_id == 73:
                        objects.append({"class": "book", "conf": conf})

        detections = {
            "face_count": len(faces),
            "looking_away": looking_away,
            "objects": objects
        }

        # Temporal Aggregation
        new_events = process_frame_detections(attempt_id, detections, db, base64_frame)

        # Format events for response
        events_json = []
        for e in new_events:
            events_json.append({
                "type": e.event_type,
                "severity": e.severity,
                "confidence": e.confidence
            })

        # Backward compatibility for status
        current_status = "safe"
        if len(faces) == 0: current_status = "missing"
        elif len(faces) > 1: current_status = "multiple"
        elif looking_away: current_status = "looking_away"
        elif any(obj['class'] == 'phone' for obj in objects): current_status = "phone_detected"
        elif any(obj['class'] == 'book' for obj in objects): current_status = "book_detected"

        return JSONResponse(status_code=200, content={
            "status": current_status,
            "events": events_json,
            "detections": detections
        })
        
    except Exception as e:
        print(f"🚨 CRITICAL AI ERROR: {e}")
        return JSONResponse(status_code=200, content={"status": "safe", "events": []})

# --- 🚀 EXPLICIT PROCTORING EVENT LOGGING ---
from models import ProctoringEvent

@proctor_bp.post('/proctoring_event')
def log_proctoring_event(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), data: dict = Body(None), request: Request = None):
    try:
        if not data or not data.get('attempt_id') or not data.get('event_type'):
            return JSONResponse(status_code=400, content={"message": "Missing required fields"})

        attempt = db.query(ExamAttempt).filter_by(id=data['attempt_id'], student_id=current_user.id).first()
        if not attempt:
            return JSONResponse(status_code=404, content={"message": "Attempt not found"})

        new_event = ProctoringEvent(
            attempt_id=attempt.id,
            event_type=data['event_type'],
            severity=data.get('severity', 'MEDIUM'),
            confidence=data.get('confidence', 1.0),
            duration_ms=data.get('duration_ms', 0)
        )
        db.add(new_event)
        db.commit()
        return JSONResponse(status_code=201, content={"message": "Event logged"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# --- 🔎 GET PROCTORING EVENTS TIMELINE ---
from models import ExamAttempt
@proctor_bp.get('/{exam_id}/proctoring_events/{student_id}')
def get_proctoring_events(exam_id, student_id, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        user = db.get(User, current_user.id)
        if user.role != 'teacher':
            return JSONResponse(status_code=403, content={"message": "Unauthorized"})

        attempt = db.query(ExamAttempt).filter_by(exam_id=exam_id, student_id=student_id).order_by(ExamAttempt.id.desc()).first()
        if not attempt:
            return JSONResponse(status_code=404, content={"message": "No attempt found"})

        events = db.query(ProctoringEvent).filter_by(attempt_id=attempt.id).order_by(ProctoringEvent.timestamp.asc()).all()
        
        event_data = []
        for e in events:
            event_data.append({
                'id': e.id,
                'timestamp': e.timestamp.isoformat() if e.timestamp else None,
                'event_type': e.event_type,
                'severity': e.severity,
                'confidence': e.confidence,
                'duration_ms': e.duration_ms,
                'evidence_url': e.evidence_url
            })
            
        return JSONResponse(status_code=200, content=event_data)
    except Exception as e:
        print(f"GET EVENTS ERROR: {e}")
        return JSONResponse(status_code=500, content={"message": "Error fetching events"})
