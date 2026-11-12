import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Base and Environment
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    
    # Database Configuration using Absolute Path to Active Instance DB
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'intranet_exam_db.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'qis-dev-secret-key-change-in-production')
    
    # External AI Services (Google Gemini) - Safe lookup from environment
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
    
    # Frontend / CORS Configuration
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')

    # QIS Duplicate Detection Thresholds
    DUPLICATE_HIGH_THRESHOLD = float(os.environ.get('DUPLICATE_HIGH_THRESHOLD', '0.90'))
    DUPLICATE_MEDIUM_THRESHOLD = float(os.environ.get('DUPLICATE_MEDIUM_THRESHOLD', '0.80'))
    DUPLICATE_LOW_THRESHOLD = float(os.environ.get('DUPLICATE_LOW_THRESHOLD', '0.70'))
    
    # File Storage Paths
    UPLOAD_DIR = os.path.join(BASE_DIR, os.environ.get('UPLOAD_DIR', os.path.join('static', 'uploads')))
    YOLO_MODEL_PATH = os.path.join(BASE_DIR, 'yolov8n.pt')
