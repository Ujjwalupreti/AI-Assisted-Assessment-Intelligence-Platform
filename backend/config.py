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
    
    # Security & JWT Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('JWT_SECRET', 'qis-dev-secret-key-change-in-production')
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
    REFRESH_TOKEN_EXPIRE_DAYS_STANDARD = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS_STANDARD', '7'))
    REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER', '30'))
    
    # External AI Services (Google Gemini) - Safe lookup from environment
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
    
    # Frontend / CORS Configuration
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')

    # Email Service Configuration
    EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
    EMAIL_FROM = os.environ.get('EMAIL_FROM', 'no-reply@qis-assessment.com')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('true', '1')

    # OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', '').strip()
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '').strip()

    # QIS Duplicate Detection Thresholds
    DUPLICATE_HIGH_THRESHOLD = float(os.environ.get('DUPLICATE_HIGH_THRESHOLD', '0.90'))
    DUPLICATE_MEDIUM_THRESHOLD = float(os.environ.get('DUPLICATE_MEDIUM_THRESHOLD', '0.80'))
    DUPLICATE_LOW_THRESHOLD = float(os.environ.get('DUPLICATE_LOW_THRESHOLD', '0.70'))
    
    # File Storage Paths
    UPLOAD_DIR = os.path.join(BASE_DIR, os.environ.get('UPLOAD_DIR', os.path.join('static', 'uploads')))
    YOLO_MODEL_PATH = os.path.join(BASE_DIR, 'yolov8n.pt')
