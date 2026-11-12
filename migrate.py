import sqlite3

conn = sqlite3.connect('backend/instance/intranet_exam_db.db')
cursor = conn.cursor()

def add_column(table, column_name, column_def):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_def}")
        print(f"Added {column_name} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"{column_name} already exists in {table}")
        else:
            print(f"Error adding {column_name} to {table}: {e}")

# Exam columns
add_column("exam", "cutoff_type", "VARCHAR(20) DEFAULT 'percentage'")
add_column("exam", "cutoff_value", "FLOAT DEFAULT 50.0")
add_column("exam", "description", "TEXT")
add_column("exam", "tags", "TEXT")
add_column("exam", "slotting_enabled", "BOOLEAN DEFAULT 0")
add_column("exam", "pooling_enabled", "BOOLEAN DEFAULT 0")
add_column("exam", "pool_size", "INTEGER")
add_column("exam", "questions_per_student", "INTEGER")
add_column("exam", "randomize_questions", "BOOLEAN DEFAULT 1")

# Exam attempt columns
add_column("exam_attempt", "assigned_questions_json", "TEXT")

conn.commit()
conn.close()
print("Migration complete!")
