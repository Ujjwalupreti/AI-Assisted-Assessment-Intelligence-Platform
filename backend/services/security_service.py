"""
Security, Cryptography, and Rate Limiting Service for QIS Authentication.
Provides password validation, cryptographic token management, JWT token handling,
brute-force protection, and audit logging.
"""

import re
import os
import secrets
import hashlib
import threading
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, Dict, List
import jwt
from sqlalchemy.orm import Session
from config import Config
from models import User, RefreshToken, SecurityLog

# Configuration defaults
SECRET_KEY = getattr(Config, 'SECRET_KEY', 'qis-dev-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
REFRESH_TOKEN_EXPIRE_DAYS_STANDARD = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS_STANDARD', '7'))
REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER = int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER', '30'))

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")

# =============================================================================
# 1. VALIDATION UTILITIES
# =============================================================================

def validate_email_format(email: str) -> bool:
    """Validate RFC email address format."""
    if not email or len(email) > 120:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def validate_username_format(username: str) -> Tuple[bool, str]:
    """Validate username length and characters."""
    if not username:
        return False, "Username is required."
    clean = username.strip()
    if len(clean) < 3:
        return False, "Username must be at least 3 characters long."
    if len(clean) > 30:
        return False, "Username cannot exceed 30 characters."
    if not USERNAME_REGEX.match(clean):
        return False, "Username may only contain letters, numbers, and underscores."
    return True, ""

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password length and complexity requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must include at least one lowercase letter (a-z)."
    if not re.search(r"[0-9]", password):
        return False, "Password must include at least one number (0-9)."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+[\]\\/]", password):
        return False, "Password must include at least one special character (!@#$%^&* etc.)."
    return True, "Password meets complexity requirements."

# =============================================================================
# 2. CRYPTOGRAPHIC TOKENS
# =============================================================================

def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a high-entropy URL-safe cryptographic token."""
    return secrets.token_urlsafe(nbytes)

def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of a raw token for secure database storage."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

# =============================================================================
# 3. JWT ACCESS TOKEN MANAGEMENT
# =============================================================================

def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token containing standard claims and user claims."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name or user.username,
        "is_verified": bool(user.is_verified),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token, strictly checking expiration and signature."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# =============================================================================
# 4. REFRESH TOKEN ROTATION & REVOCATION
# =============================================================================

def create_refresh_token(db: Session, user_id: int, device_info: Optional[str] = None, remember_me: bool = False) -> str:
    """Generate a secure refresh token, store its SHA-256 hash in DB, and return raw token."""
    raw_token = generate_secure_token(48)
    token_h = hash_token(raw_token)
    days = REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER if remember_me else REFRESH_TOKEN_EXPIRE_DAYS_STANDARD
    expires_at = datetime.utcnow() + timedelta(days=days)

    refresh_obj = RefreshToken(
        user_id=user_id,
        token_hash=token_h,
        device_info=device_info[:255] if device_info else None,
        expires_at=expires_at
    )
    db.add(refresh_obj)
    db.commit()
    return raw_token

def rotate_refresh_token(db: Session, raw_token: str, device_info: Optional[str] = None) -> Tuple[Optional[User], Optional[str]]:
    """
    Validate an incoming refresh token. If valid, revoke it, issue a new one (rotation),
    and return the associated User and new raw refresh token.
    If a revoked token is replayed, revoke all tokens for that user to mitigate replay attacks.
    """
    token_h = hash_token(raw_token)
    now = datetime.utcnow()

    token_record = db.query(RefreshToken).filter_by(token_hash=token_h).first()
    if not token_record:
        return None, None

    # Check for token reuse / replay attack
    if token_record.revoked_at is not None:
        # Potential theft! Revoke all tokens for this user
        revoke_all_user_tokens(db, token_record.user_id)
        return None, None

    # Check expiration
    if token_record.expires_at < now:
        return None, None

    user = db.get(User, token_record.user_id)
    if not user or not user.is_active:
        return None, None

    # Revoke current token
    token_record.revoked_at = now

    # Issue new rotated token preserving remaining duration policy
    new_raw_token = generate_secure_token(48)
    new_token_h = hash_token(new_raw_token)
    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=new_token_h,
        device_info=device_info[:255] if device_info else token_record.device_info,
        expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS_STANDARD)
    )
    db.add(new_refresh)
    db.commit()
    return user, new_raw_token

def revoke_refresh_token(db: Session, raw_token: str) -> bool:
    """Revoke a single refresh token."""
    if not raw_token:
        return False
    token_h = hash_token(raw_token)
    token_record = db.query(RefreshToken).filter_by(token_hash=token_h).first()
    if token_record and token_record.revoked_at is None:
        token_record.revoked_at = datetime.utcnow()
        db.commit()
        return True
    return False

def revoke_all_user_tokens(db: Session, user_id: int):
    """Revoke all active refresh tokens for a user (e.g. after password reset or full logout)."""
    now = datetime.utcnow()
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": now})
    db.commit()

# =============================================================================
# 5. BRUTE FORCE PROTECTION & RATE LIMITING
# =============================================================================

class MemoryRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter & lockout manager."""
    def __init__(self):
        self._lock = threading.Lock()
        self._requests: Dict[str, List[float]] = {}
        self._failed_logins: Dict[str, List[float]] = {}
        self._lockouts: Dict[str, float] = {}

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if `key` has exceeded `max_requests` in `window_seconds`."""
        now = datetime.utcnow().timestamp()
        with self._lock:
            timestamps = self._requests.get(key, [])
            # Purge expired timestamps
            cutoff = now - window_seconds
            timestamps = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= max_requests:
                self._requests[key] = timestamps
                return True
            timestamps.append(now)
            self._requests[key] = timestamps
            return False

    def record_failed_login(self, identifier: str, max_attempts: int = 5, lockout_seconds: int = 900) -> Tuple[bool, int]:
        """
        Record a failed login for IP or username.
        If threshold reached, locks out identifier for `lockout_seconds` (default 15 mins).
        Returns (is_locked, remaining_seconds).
        """
        now = datetime.utcnow().timestamp()
        with self._lock:
            # Check existing lockout
            locked_until = self._lockouts.get(identifier, 0)
            if locked_until > now:
                return True, int(locked_until - now)

            attempts = self._failed_logins.get(identifier, [])
            # Window for attempts: 15 minutes
            cutoff = now - lockout_seconds
            attempts = [t for t in attempts if t > cutoff]
            attempts.append(now)
            self._failed_logins[identifier] = attempts

            if len(attempts) >= max_attempts:
                lock_until = now + lockout_seconds
                self._lockouts[identifier] = lock_until
                return True, lockout_seconds
            return False, 0

    def check_lockout(self, identifier: str) -> Tuple[bool, int]:
        """Check if an identifier is currently locked out."""
        now = datetime.utcnow().timestamp()
        with self._lock:
            locked_until = self._lockouts.get(identifier, 0)
            if locked_until > now:
                return True, int(locked_until - now)
            return False, 0

    def clear_failed_logins(self, identifier: str):
        """Clear failed login attempts and lockout upon successful authentication."""
        with self._lock:
            self._failed_logins.pop(identifier, None)
            self._lockouts.pop(identifier, None)

# Global singleton rate limiter instance
rate_limiter = MemoryRateLimiter()

# =============================================================================
# 6. SECURITY AUDIT LOGGING
# =============================================================================

def log_security_event(
    db: Session,
    event_type: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None
):
    """Persist a security event to the security_log table."""
    try:
        log_entry = SecurityLog(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address[:45] if ip_address else None,
            user_agent=user_agent[:255] if user_agent else None,
            details=details,
            timestamp=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"[SecurityLog Warning] Failed to persist security event: {e}")
        try:
            db.rollback()
        except Exception:
            pass

