from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Dropping existing database schema...")
    db.drop_all()
    print("Creating database schema...")
    db.create_all()
    print("Schema created successfully.")
