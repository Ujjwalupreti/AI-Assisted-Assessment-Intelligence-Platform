from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import Config
from database import Base, engine
import models # MUST import models so metadata is registered

# Ensure tables are created
Base.metadata.create_all(bind=engine)

def create_app():
    app = FastAPI(title="AI Exam Project", description="FastAPI Backend for Exam System", version="1.0.0")

    # Enable CORS
    origins = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["user-id"]
    )

    # Import API Routers
    from routes.exams.main_routes import auth_bp, exam_bp
    from routes.exams.exam_conduct_routes import conduct_bp
    from routes.exams.proctoring_routes import proctor_bp
    from routes.exams.question_routes import question_bp
    from routes.exams.attempt_routes import attempt_bp
    from routes.analytics.analytics_routes import analytics_bp
    from routes.users.students_routes import student_bp
    from routes.users.admin_routes import admin_bp

    from routes.ai_routes.exam_intelligence_routes import intelligence_bp
    from routes.ai_routes.qis_routes import qis_bp
    from routes.ai_routes.rag_routes import rag_bp

    # Register Routers
    app.include_router(auth_bp, prefix='/api/auth', tags=['auth'])
    app.include_router(exam_bp, prefix='/api/exams', tags=['exams'])
    app.include_router(conduct_bp, prefix='/api/exams', tags=['exam-conduct'])
    app.include_router(proctor_bp, prefix='/api/exams', tags=['proctoring'])
    app.include_router(question_bp, prefix='/api/exams', tags=['questions'])

    app.include_router(intelligence_bp, prefix='/api/intelligence', tags=['intelligence'])
    app.include_router(attempt_bp, prefix='/api/attempts', tags=['attempts'])
    app.include_router(student_bp, prefix='/api/students', tags=['students'])
    app.include_router(admin_bp, prefix='/api/admin', tags=['admin'])
    app.include_router(analytics_bp, prefix='/api/analytics', tags=['analytics'])
    app.include_router(qis_bp, prefix='/api/ai/questions', tags=['qis'])
    app.include_router(rag_bp, prefix='/api/rag', tags=['rag'])

    @app.get('/api/ping')
    def ping():
        return {"status": "ok"}

    return app

app = create_app()

if __name__ == '__main__':
    import uvicorn
    print(" Server Starting on Port 5001...")
    uvicorn.run("app:app", host='0.0.0.0', port=5001, reload=True)