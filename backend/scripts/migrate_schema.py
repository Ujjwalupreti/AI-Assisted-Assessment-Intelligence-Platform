import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'intranet_exam_db.db')
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'intranet_exam_db.db')
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path} either. Looking in root.")
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'intranet_exam_db.db')

print(f"Using DB at: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def column_exists(table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns

try:
    if not column_exists("exam", "creation_mode"):
        cursor.execute("ALTER TABLE exam ADD COLUMN creation_mode VARCHAR(50) DEFAULT 'manual'")
        print("Added creation_mode to exam.")
    
    if not column_exists("question", "source"):
        cursor.execute("ALTER TABLE question ADD COLUMN source VARCHAR(50) DEFAULT 'MANUAL'")
        print("Added source to question.")
        
    if not column_exists("question", "duplicate_status"):
        cursor.execute("ALTER TABLE question ADD COLUMN duplicate_status VARCHAR(50) DEFAULT 'SAFE'")
        print("Added duplicate_status to question.")
        
    conn.commit()
    print("Migration successful.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
