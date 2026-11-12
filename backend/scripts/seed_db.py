from app import create_app, db
from models import User

app = create_app()

with app.app_context():
    print("Seeding database...")
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@exam.com', role='admin')
        admin.set_password('adminpass')
        db.add(admin)
        db.commit()
        print("Admin user created.")
    else:
        print("Admin already exists.")
