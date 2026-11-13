from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import Config
import os

# Create engine with production pool tuning for non-sqlite
db_uri = Config.SQLALCHEMY_DATABASE_URI
is_sqlite = "sqlite" in db_uri
engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 3600

try:
    engine = create_engine(db_uri, **engine_kwargs)
    with engine.connect() as conn:
        pass
except Exception as e:
    print(f"[database] Warning: Failed to connect to primary DB ({db_uri}): {e}")
    fallback_path = os.path.join(Config.BASE_DIR, 'instance', 'intranet_exam_db.db')
    os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
    fallback_uri = f"sqlite:///{fallback_path}"
    print(f"[database] Falling back to SQLite database: {fallback_uri}")
    engine = create_engine(fallback_uri, connect_args={"check_same_thread": False})

# Create SessionLocal class from sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()

from contextlib import contextmanager

# Dependency for FastAPI to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Context manager for non-FastAPI services/threads to avoid generator session leaks
@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
