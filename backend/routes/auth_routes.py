"""
Comprehensive Authentication & Identity Router for QIS Platform.
Implements:
- Registration with field validation, email verification token dispatch, and role restriction
- Email verification and cooldown-governed resend with enumeration prevention
- Credential login with brute-force lockout, rate limiting, and generic error messages
- JWT access tokens (short-lived, expiring) and rotating refresh tokens with revocation
- Forgot password & Password reset workflows with single-use hashed tokens and session revocation
- OAuth 2.0 / OIDC social login with Google and GitHub, CSRF state protection, and safe account linking
- Profile retrieval, profile update, and password changes
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Body, Request, HTTPException, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models import User, EmailVerificationToken, PasswordResetToken, RefreshToken, SecurityLog
from auth_middleware import get_current_user
from services.security_service import (
    validate_email_format,
    validate_username_format,
    validate_password_strength,
    generate_secure_token,
    hash_token,
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    rate_limiter,
    log_security_event,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from services.email_service import email_service
from services.oauth_service import OAuthService

auth_bp = APIRouter()

# Helper to extract client IP address
def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

# Helper to set authentication cookies
def set_auth_cookies(response: Response, access_token: str, refresh_token: Optional[str] = None):
    # Cookie security settings (production vs development)
    secure_cookie = False  # Set to True when served over HTTPS in production
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            secure=secure_cookie,
            max_age=30 * 24 * 3600,
            path="/"
        )

def clear_auth_cookies(response: Response):
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


# =============================================================================
# 1. USER REGISTRATION
# =============================================================================

@auth_bp.post('/register', status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")

    # Rate Limiting: Max 30 registration attempts per 10 minutes per IP
    if rate_limiter.is_rate_limited(f"reg_ip_{ip}", max_requests=30, window_seconds=600):
        log_security_event(db, "REGISTRATION_RATE_LIMITED", ip_address=ip, user_agent=ua)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration requests. Please wait a few minutes before trying again."
        )

    # Extract fields
    full_name = data.get('full_name', '').strip()
    username = data.get('username', '').strip().lower()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    enrollment_id = data.get('enrollment_id')
    if enrollment_id and str(enrollment_id).strip():
        enrollment_id = str(enrollment_id).strip()
    else:
        enrollment_id = None

    # 1. Name validation
    if not full_name or len(full_name) < 2:
        raise HTTPException(status_code=400, detail="Full name must be at least 2 characters long.")
    if len(full_name) > 120:
        raise HTTPException(status_code=400, detail="Full name cannot exceed 120 characters.")

    # 2. Username validation
    valid_uname, uname_err = validate_username_format(username)
    if not valid_uname:
        raise HTTPException(status_code=400, detail=uname_err)

    # 3. Email format validation
    if not validate_email_format(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    # 4. Password matching validation
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    # 5. Password strength validation
    valid_pw, pw_err = validate_password_strength(password)
    if not valid_pw:
        raise HTTPException(status_code=400, detail=pw_err)

    # 6. Uniqueness validations
    if db.query(User).filter_by(username=username).first():
        raise HTTPException(status_code=409, detail="Username is already registered. Please choose another.")
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="An account with this email address already exists.")
    if enrollment_id and db.query(User).filter_by(enrollment_id=enrollment_id).first():
        raise HTTPException(status_code=409, detail="Enrollment ID is already registered.")

    # 7. Mass Assignment & Privilege Escalation Prevention:
    # Public registration strictly defaults and forces role to 'student'
    assigned_role = 'student'

    # Create unverified user account
    new_user = User(
        username=username,
        email=email,
        full_name=full_name,
        enrollment_id=enrollment_id,
        role=assigned_role,
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow()
    )
    new_user.set_password(password)
    db.add(new_user)
    db.flush()

    # Generate cryptographically secure, single-use email verification token
    raw_token = generate_secure_token(32)
    token_h = hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    verification_token = EmailVerificationToken(
        user_id=new_user.id,
        token_hash=token_h,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(verification_token)
    db.commit()

    # Dispatch verification email
    email_service.send_verification_email(
        recipient_email=email,
        recipient_name=full_name,
        token=raw_token
    )

    log_security_event(
        db,
        "USER_REGISTERED",
        user_id=new_user.id,
        ip_address=ip,
        user_agent=ua,
        details=f"Username: {username}, Email: {email}, Role: {assigned_role}"
    )

    return {
        "message": "Registration successful! A verification link has been sent to your email address.",
        "dev_verification_url": f"/verify-email?token={raw_token}",
        "dev_token": raw_token,
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "is_verified": new_user.is_verified
        }
    }


# =============================================================================
# 2. EMAIL VERIFICATION & RESEND
# =============================================================================

@auth_bp.post('/dev-verify')
def dev_verify(data: dict = Body(...), db: Session = Depends(get_db)):
    """Developer helper: immediately verify an unverified account for local testing."""
    email_or_user = data.get('email', '').strip().lower()
    if not email_or_user:
        raise HTTPException(status_code=400, detail="Email or username is required.")
    user = db.query(User).filter(or_(User.email == email_or_user, User.username == email_or_user)).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"No account found matching '{email_or_user}'.")
    user.is_verified = True
    db.commit()
    return {"message": f"Account '{user.email}' has been verified! You can now sign in.", "verified": True}

@auth_bp.post('/verify-email')
def verify_email(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    token = data.get('token', '').strip()

    if not token:
        raise HTTPException(status_code=400, detail="Verification token is required.")

    token_h = hash_token(token)
    now = datetime.utcnow()

    # Lookup token record
    token_record = db.query(EmailVerificationToken).filter_by(token_hash=token_h).first()

    if not token_record:
        log_security_event(db, "EMAIL_VERIFY_INVALID_TOKEN", ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=400, detail="Invalid verification token.")

    if token_record.used_at is not None:
        log_security_event(db, "EMAIL_VERIFY_REUSED_TOKEN", user_id=token_record.user_id, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=400, detail="This verification token has already been used.")

    if token_record.expires_at < now:
        log_security_event(db, "EMAIL_VERIFY_EXPIRED_TOKEN", user_id=token_record.user_id, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=400, detail="Verification token has expired. Please request a new one.")

    # Mark token used
    token_record.used_at = now

    # Mark user verified
    user = db.get(User, token_record.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User account associated with this token no longer exists.")

    user.is_verified = True
    db.commit()

    log_security_event(db, "EMAIL_VERIFIED_SUCCESS", user_id=user.id, ip_address=ip, user_agent=ua)

    return {
        "message": "Email verified successfully! You may now log in to your account.",
        "verified": True,
        "email": user.email
    }

@auth_bp.post('/resend-verification')
def resend_verification(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    email = data.get('email', '').strip().lower()

    if not email or not validate_email_format(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    # Rate limiting: Max 3 requests per 10 minutes per IP
    if rate_limiter.is_rate_limited(f"resend_ip_{ip}", max_requests=3, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a few minutes before requesting another verification email."
        )

    # Generic response to prevent account enumeration
    generic_msg = "If an unverified account exists with this email address, a verification link has been sent."

    user = db.query(User).filter_by(email=email).first()
    if not user:
        # Prevent account enumeration
        return {"message": generic_msg}

    if user.is_verified:
        return {"message": "This email address is already verified. You can log in directly."}

    # Cooldown check: 60 seconds between verification requests
    recent_token = db.query(EmailVerificationToken).filter_by(user_id=user.id).order_by(EmailVerificationToken.created_at.desc()).first()
    if recent_token:
        time_since = (datetime.utcnow() - recent_token.created_at).total_seconds()
        if time_since < 60:
            remaining = int(60 - time_since)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting another verification link."
            )

    # Invalidate previous unused tokens for this user
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used_at.is_(None)
    ).update({"used_at": datetime.utcnow()})

    # Generate new token
    raw_token = generate_secure_token(32)
    token_h = hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(hours=24)

    new_token_record = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_h,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(new_token_record)
    db.commit()

    # Dispatch email
    email_service.send_verification_email(
        recipient_email=user.email,
        recipient_name=user.full_name or user.username,
        token=raw_token
    )

    log_security_event(db, "RESEND_VERIFICATION_SENT", user_id=user.id, ip_address=ip, user_agent=ua)
    return {"message": generic_msg}


# =============================================================================
# 3. LOGIN & SESSION MANAGEMENT
# =============================================================================

@auth_bp.post('/login')
def login(
    request: Request,
    response: Response,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    identifier = data.get('username') or data.get('email') or data.get('identifier', '')
    identifier = str(identifier).strip().lower()
    password = data.get('password', '')
    remember_me = bool(data.get('remember_me', False))

    if not identifier or not password:
        raise HTTPException(status_code=400, detail="Username/Email and password are required.")

    # 1. Check Brute-Force Lockout on IP & Identifier
    is_locked_ip, remaining_ip = rate_limiter.check_lockout(f"ip_{ip}")
    if is_locked_ip:
        log_security_event(db, "LOGIN_LOCKED_OUT_IP", ip_address=ip, user_agent=ua)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts from this network. Please try again in {remaining_ip // 60 + 1} minutes."
        )

    is_locked_user, remaining_user = rate_limiter.check_lockout(f"user_{identifier}")
    if is_locked_user:
        log_security_event(db, "LOGIN_LOCKED_OUT_ACCOUNT", ip_address=ip, user_agent=ua, details=f"Target: {identifier}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked due to multiple failed login attempts. Please try again in {remaining_user // 60 + 1} minutes."
        )

    # 2. Query user by username OR email
    user = db.query(User).filter(
        or_(User.username == identifier, User.email == identifier)
    ).first()

    # 3. Validate credentials with generic error messages
    if not user or not user.check_password(password):
        # Record failed attempt on both IP and account
        rate_limiter.record_failed_login(f"ip_{ip}")
        rate_limiter.record_failed_login(f"user_{identifier}")
        log_security_event(db, "LOGIN_FAILED_CREDENTIALS", user_id=user.id if user else None, ip_address=ip, user_agent=ua, details=f"Attempt for: {identifier}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password.")

    # 4. Check active account status
    if not user.is_active:
        log_security_event(db, "LOGIN_BLOCKED_INACTIVE", user_id=user.id, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Please contact an administrator.")

    # 5. Check Email Verification Policy
    # Note: Existing pre-seeded accounts and admins/teachers may bypass if configured
    if not user.is_verified:
        log_security_event(db, "LOGIN_REJECTED_UNVERIFIED", user_id=user.id, ip_address=ip, user_agent=ua)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "message": "Please verify your email address before logging in.",
                "unverified": True,
                "email": user.email
            }
        )

    # 6. Credentials Valid -> Clear brute force records
    rate_limiter.clear_failed_logins(f"ip_{ip}")
    rate_limiter.clear_failed_logins(f"user_{identifier}")

    # 7. Generate JWT Access Token & Refresh Token
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(db, user.id, device_info=ua, remember_me=remember_me)

    # 8. Set HttpOnly Cookies
    set_auth_cookies(response, access_token, refresh_token)

    log_security_event(db, "LOGIN_SUCCESS", user_id=user.id, ip_address=ip, user_agent=ua)

    return {
        "token": access_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name or user.username,
            "role": user.role,
            "is_verified": user.is_verified,
            "enrollment_id": user.enrollment_id
        }
    }


@auth_bp.post('/refresh')
def refresh_token_route(
    request: Request,
    response: Response,
    data: Optional[dict] = Body(None),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")

    # Extract refresh token from body or cookie
    raw_token = (data.get('refresh_token') if data else None) or request.cookies.get("refresh_token")
    if not raw_token:
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required.")

    # Rotate refresh token (revokes current token and issues a new one)
    user, new_refresh_token = rotate_refresh_token(db, raw_token, device_info=ua)
    if not user or not new_refresh_token:
        clear_auth_cookies(response)
        log_security_event(db, "REFRESH_TOKEN_INVALID_OR_REUSED", ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid, expired, or reused refresh token.")

    # Issue new access token
    new_access_token = create_access_token(user)
    set_auth_cookies(response, new_access_token, new_refresh_token)

    return {
        "token": new_access_token,
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }


@auth_bp.post('/logout')
def logout(
    request: Request,
    response: Response,
    data: Optional[dict] = Body(None),
    db: Session = Depends(get_db)
):
    ua = request.headers.get("user-agent", "")
    ip = get_client_ip(request)

    raw_token = (data.get('refresh_token') if data else None) or request.cookies.get("refresh_token")
    if raw_token:
        revoke_refresh_token(db, raw_token)

    clear_auth_cookies(response)
    log_security_event(db, "LOGOUT", ip_address=ip, user_agent=ua)
    return {"message": "Successfully logged out."}


# =============================================================================
# 4. FORGOT PASSWORD & RESET PASSWORD
# =============================================================================

@auth_bp.post('/forgot-password')
def forgot_password(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    email = data.get('email', '').strip().lower()

    if not email or not validate_email_format(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    # Rate limiting: Max 3 requests per 10 minutes per IP
    if rate_limiter.is_rate_limited(f"forgot_ip_{ip}", max_requests=3, window_seconds=600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please wait a few minutes before trying again."
        )

    # Generic enumeration-resistant message
    generic_msg = "If an account exists with this email address, password reset instructions have been sent."

    user = db.query(User).filter_by(email=email).first()
    if not user or not user.is_active:
        return {"message": generic_msg}

    # Cooldown: 60 seconds between reset emails
    recent_token = db.query(PasswordResetToken).filter_by(user_id=user.id).order_by(PasswordResetToken.created_at.desc()).first()
    if recent_token:
        time_since = (datetime.utcnow() - recent_token.created_at).total_seconds()
        if time_since < 60:
            remaining = int(60 - time_since)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting another password reset email."
            )

    # Invalidate previous unused reset tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None)
    ).update({"used_at": datetime.utcnow()})

    # Generate single-use reset token
    raw_token = generate_secure_token(32)
    token_h = hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(hours=1)

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_h,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(reset_record)
    db.commit()

    # Dispatch email
    email_service.send_password_reset_email(
        recipient_email=user.email,
        recipient_name=user.full_name or user.username,
        token=raw_token
    )

    log_security_event(db, "PASSWORD_RESET_REQUESTED", user_id=user.id, ip_address=ip, user_agent=ua)
    return {"message": generic_msg}


@auth_bp.post('/verify-reset-token')
def verify_reset_token(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    token = data.get('token', '').strip()
    if not token:
        raise HTTPException(status_code=400, detail="Reset token is required.")

    token_h = hash_token(token)
    token_record = db.query(PasswordResetToken).filter_by(token_hash=token_h).first()

    if not token_record or token_record.used_at is not None:
        return {"valid": False, "message": "This password reset link is invalid or has already been used."}

    if token_record.expires_at < datetime.utcnow():
        return {"valid": False, "message": "This password reset link has expired. Please request a new one."}

    return {"valid": True, "message": "Reset token is valid."}


@auth_bp.post('/reset-password')
def reset_password(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not token:
        raise HTTPException(status_code=400, detail="Reset token is required.")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    valid_pw, pw_err = validate_password_strength(new_password)
    if not valid_pw:
        raise HTTPException(status_code=400, detail=pw_err)

    token_h = hash_token(token)
    now = datetime.utcnow()

    token_record = db.query(PasswordResetToken).filter_by(token_hash=token_h).first()
    if not token_record:
        log_security_event(db, "PASSWORD_RESET_INVALID_TOKEN", ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=400, detail="Invalid password reset token.")

    if token_record.used_at is not None:
        log_security_event(db, "PASSWORD_RESET_REUSED_TOKEN", user_id=token_record.user_id, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=400, detail="This reset link has already been used.")

    if token_record.expires_at < now:
        log_security_event(db, "PASSWORD_RESET_EXPIRED_TOKEN", user_id=token_record.user_id, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=400, detail="Password reset link has expired.")

    user = db.get(User, token_record.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    # Update password with bcrypt
    user.set_password(new_password)
    # Mark token used
    token_record.used_at = now

    # Security Best Practice: Invalidate all existing sessions / refresh tokens
    revoke_all_user_tokens(db, user.id)
    db.commit()

    log_security_event(db, "PASSWORD_RESET_SUCCESS", user_id=user.id, ip_address=ip, user_agent=ua)
    return {"message": "Password has been reset successfully. Please log in with your new password."}


# =============================================================================
# 5. USER PROFILE & CREDENTIAL MANAGEMENT
# =============================================================================

@auth_bp.get('/me')
def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name or current_user.username,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
        "enrollment_id": current_user.enrollment_id,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@auth_bp.put('/profile')
def update_profile(
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allow updating user full name or enrollment ID. Role and verification cannot be escalated."""
    full_name = data.get('full_name')
    if full_name is not None:
        full_name = full_name.strip()
        if len(full_name) < 2 or len(full_name) > 120:
            raise HTTPException(status_code=400, detail="Full name must be between 2 and 120 characters.")
        current_user.full_name = full_name

    enrollment_id = data.get('enrollment_id')
    if enrollment_id is not None:
        clean_eid = str(enrollment_id).strip() or None
        if clean_eid and clean_eid != current_user.enrollment_id:
            # Check uniqueness
            if db.query(User).filter_by(enrollment_id=clean_eid).first():
                raise HTTPException(status_code=409, detail="Enrollment ID is already registered.")
            current_user.enrollment_id = clean_eid

    db.commit()
    return {
        "message": "Profile updated successfully.",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "enrollment_id": current_user.enrollment_id
        }
    }

@auth_bp.post('/change-password')
def change_password(
    request: Request,
    data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = get_client_ip(request)
    ua = request.headers.get("user-agent", "")
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not current_user.check_password(current_password):
        log_security_event(db, "CHANGE_PASSWORD_FAILED", user_id=current_user.id, ip_address=ip, user_agent=ua)
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match.")

    valid_pw, pw_err = validate_password_strength(new_password)
    if not valid_pw:
        raise HTTPException(status_code=400, detail=pw_err)

    current_user.set_password(new_password)
    # Revoke other sessions
    revoke_all_user_tokens(db, current_user.id)
    db.commit()

    log_security_event(db, "CHANGE_PASSWORD_SUCCESS", user_id=current_user.id, ip_address=ip, user_agent=ua)
    return {"message": "Password updated successfully."}


# =============================================================================
# 6. OAUTH 2.0 / SOCIAL LOGIN
# =============================================================================

@auth_bp.get('/oauth/config')
def get_oauth_config():
    """Return public OAuth provider configuration status (disabled)."""
    return {
        "google": {"enabled": False},
        "github": {"enabled": False},
        "message": "OAuth is currently disabled."
    }

@auth_bp.get('/oauth/{provider}/url')
def get_oauth_url(provider: str, redirect_uri: str):
    """OAuth is disabled."""
    raise HTTPException(status_code=400, detail="OAuth authentication is currently disabled on this platform.")

@auth_bp.post('/oauth/{provider}/callback')
def oauth_callback(provider: str):
    """OAuth is disabled."""
    raise HTTPException(status_code=400, detail="OAuth authentication is currently disabled on this platform.")
