"""
Migration script for Authentication & Security models.
Safely adds new columns to `user` table and creates authentication tables.
Preserves all existing data.
"""

import os
import sys
import shutil
from datetime import datetime

# Add backend directory to path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import inspect, text
from database import engine, SessionLocal, Base
from models import User, EmailVerificationToken, PasswordResetToken, RefreshToken, OAuthAccount, SecurityLog

def run_migration():
    print("=" * 70)
    print("Starting Authentication System Database Migration...")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 70)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"Existing tables in database ({len(existing_tables)}): {', '.join(existing_tables)}")

    # 1. Migrate `user` table columns
    user_columns = [col['name'] for col in inspector.get_columns('user')]
    print(f"Existing columns in 'user': {user_columns}")

    columns_to_add = [
        ('full_name', 'VARCHAR(120)'),
        ('is_verified', 'BOOLEAN DEFAULT 0'),
        ('created_at', 'DATETIME'),
        ('updated_at', 'DATETIME')
    ]

    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            if col_name not in user_columns:
                print(f"  -> Adding column '{col_name}' ({col_type}) to 'user' table...")
                conn.execute(text(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            else:
                print(f"  -> Column '{col_name}' already exists in 'user' table.")

        # Ensure existing accounts are marked as verified so existing users are not locked out
        print("  -> Ensuring existing accounts are marked as verified (is_verified = 1)...")
        conn.execute(text("UPDATE user SET is_verified = 1 WHERE is_verified IS NULL OR is_verified = 0"))
        # Set default created_at for existing users if NULL
        conn.execute(text("UPDATE user SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
        conn.commit()

    # 2. Create any missing tables defined in Base metadata
    print("\nEnsuring all authentication & security tables exist...")
    Base.metadata.create_all(bind=engine)

    # Re-inspect tables
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()
    print(f"Updated tables in database ({len(new_tables)}): {', '.join(new_tables)}")

    # Verify all expected auth tables exist
    expected_tables = ['email_verification_token', 'password_reset_token', 'refresh_token', 'oauth_account', 'security_log']
    for t in expected_tables:
        if t in new_tables:
            print(f"  [OK] Table '{t}' verified.")
        else:
            print(f"  [ERROR] Table '{t}' NOT found!")

    # Verify existing users are intact
    db = SessionLocal()
    users = db.query(User).all()
    print(f"\nUser table integrity check: {len(users)} users active.")
    for u in users:
        print(f"  User id={u.id}, username='{u.username}', email='{u.email}', role='{u.role}', verified={u.is_verified}")
    db.close()

    print("=" * 70)
    print("Authentication Database Migration Complete!")
    print("=" * 70)

if __name__ == '__main__':
    run_migration()

