"""
Authentication and JWT Security Services for Users & Admins
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import hmac
from jose import JWTError, jwt
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.db.models import User

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password[:72].encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password[:72].encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    mins = expires_minutes or settings.JWT_EXPIRE_MINUTES
    expire = datetime.utcnow() + timedelta(minutes=mins)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        return None

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency for strictly protected user routes."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required."
        )
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
    user_id = payload.get("sub")
    role = payload.get("role", "student")

    # If it's the admin token
    if role == "admin" and user_id == settings.ADMIN_USERNAME:
        # Return synthetic admin user object
        admin_user = User(
            id="admin-001",
            username=settings.ADMIN_USERNAME,
            email="admin@gcet.edu.in",
            full_name="System Administrator",
            role="admin",
            department="Administration"
        )
        return admin_user

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Fallback query by username
        user = db.query(User).filter(User.username == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user

def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """Dependency for public routes that optionally accept user context."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    role = payload.get("role", "student")

    if role == "admin" and user_id == settings.ADMIN_USERNAME:
        return {
            "id": "admin-001",
            "username": settings.ADMIN_USERNAME,
            "full_name": "System Administrator",
            "email": "admin@gcet.edu.in",
            "role": "admin",
            "phone": None,
            "department": "Administration",
            "student_id": None
        }

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = db.query(User).filter(User.username == user_id).first()
    if user:
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "phone": user.phone,
            "department": user.department,
            "student_id": user.student_id
        }
    return None
