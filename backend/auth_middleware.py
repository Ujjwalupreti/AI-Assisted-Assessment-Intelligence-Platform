from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from models import User
from database import get_db
from config import Config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)
SECRET_KEY = getattr(Config, 'SECRET_KEY', 'qis-dev-secret-key-change-in-production')
ALGORITHM = "HS256"

def get_token_from_request(request: Request, bearer_token: str = Depends(oauth2_scheme)) -> str:
    """Extract token from Authorization Bearer header or fallback to access_token cookie."""
    if bearer_token:
        return bearer_token
    # Check cookie fallback
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user(token: str = Depends(get_token_from_request), db: Session = Depends(get_db)) -> User:
    """Validate access token, check expiration, verify user existence and active status."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id") or payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Security: Inactive user accounts must not be able to authenticate
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact an administrator."
        )

    return user

def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user email has been verified before proceeding."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email address must be verified before performing this action."
        )
    return current_user

def get_teacher_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user has teacher or admin role."""
    if current_user.role not in ['teacher', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher privileges required")
    return current_user

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user has admin role."""
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
