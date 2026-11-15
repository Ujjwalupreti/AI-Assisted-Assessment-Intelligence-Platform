"""
Database migration script: Multi-format answers, versioning, and integrity events.
Safely updates existing SQLite or MySQL databases without data loss.
"""
import sys
import os

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import engine, Base
from sqlalchemy import inspect, text

def run_migration():
    print("=== STARTING DATABASE MIGRATION: Multi-Format Answers & Integrity ===")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Existing tables: {existing_tables}")
    
    with engine.begin() as conn:
        # 1. Update 'answer' table if it exists
        if 'answer' in existing_tables:
            existing_columns = [c['name'] for c in inspector.get_columns('answer')]
            print(f"Existing columns in 'answer': {existing_columns}")
            
            new_columns = [
                ('answer_type', 'VARCHAR(50) DEFAULT "TEXT"'),
                ('structured_answer', 'TEXT'),
                ('file_reference', 'VARCHAR(500)'),
                ('file_hash', 'VARCHAR(64)'),
                ('version_number', 'INTEGER DEFAULT 1'),
                ('submission_status', 'VARCHAR(50) DEFAULT "SUBMITTED"'),
                ('created_at', 'DATETIME'),
                ('updated_at', 'DATETIME'),
                ('submitted_at', 'DATETIME')
            ]
            
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    print(f"Adding column '{col_name}' ({col_type}) to 'answer' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE answer ADD COLUMN {col_name} {col_type}"))
                        print(f"  Successfully added '{col_name}'")
                    except Exception as e:
                        print(f"  Note on adding '{col_name}': {e}")
                else:
                    print(f"  Column '{col_name}' already exists in 'answer'")

    # 2. Create any missing tables (like answer_version, answer_integrity_event)
    print("Creating new tables defined in models.py...")
    import models  # Ensure all model classes are registered in Base.metadata
    models.Base.metadata.create_all(bind=engine)
    
    # 3. Verify final schema
    inspector = inspect(engine)
    updated_tables = inspector.get_table_names()
    print(f"Updated tables in database: {updated_tables}")
    assert 'answer_version' in updated_tables, "Missing answer_version table"
    assert 'answer_integrity_event' in updated_tables, "Missing answer_integrity_event table"
    print("=== MIGRATION COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_migration()
