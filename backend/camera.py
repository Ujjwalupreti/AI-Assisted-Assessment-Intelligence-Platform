import cv2
import numpy as np
import base64
from ultralytics import YOLO

# Load YOLO globally so it doesn't reload every frame
try:
    yolo_model = YOLO('yolov8n.pt')
except Exception as e:
    print(f"Failed to load YOLO model: {e}")
    yolo_model = None

# Load Haar cascade globally
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

class ProctoringCamera:
    """
    Handles frame analysis for exam proctoring using OpenCV and YOLO.
    """
    
    @staticmethod
    def analyze_base64_frame(base64_string: str) -> dict:
        """
        Analyzes a base64 encoded image frame for multiple faces or cell phones.
        Returns a dictionary with face_count, phones_detected, and a status message.
        """
        if not base64_string:
            return {"face_count": 0, "phones_detected": 0, "status": "No image provided"}
            
        try:
            # Decode base64 to numpy array
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            img_data = base64.b64decode(base64_string)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {"face_count": 0, "phones_detected": 0, "status": "Invalid image format"}

            # Face Detection (Haar Cascade is faster for simple counting)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            face_count = len(faces)
            
            # Object Detection (YOLO for phones, books, etc)
            phones_detected = 0
            if yolo_model:
                results = yolo_model(frame, verbose=False)
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        # In COCO dataset, class 67 is cell phone
                        if cls_id == 67:
                            phones_detected += 1
                            
            # Determine status
            status = "OK"
            if face_count == 0:
                status = "NO_FACE_DETECTED"
            elif face_count > 1:
                status = "MULTIPLE_FACES_DETECTED"
            elif phones_detected > 0:
                status = "PHONE_DETECTED"
                
            return {
                "face_count": face_count,
                "phones_detected": phones_detected,
                "status": status
            }
            
        except Exception as e:
            print(f"Error analyzing frame in camera.py: {e}")
            return {"face_count": 0, "phones_detected": 0, "status": "ERROR"}

    @staticmethod
    def capture_frame_from_webcam(camera_index: int = 0):
        """
        Directly grabs a frame from a connected webcam if running locally.
        """
        cap = cv2.VideoCapture(camera_index)
        ret, frame = cap.read()
        cap.release()
        if ret:
            return frame
        return None
