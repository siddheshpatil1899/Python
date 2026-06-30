import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.core.auth import get_current_user
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.services.email_service import (
    send_password_reset_email,
    send_signup_notification_to_admin,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    requested_role: str = "viewer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def hash_reset_token(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is not active yet. Please contact admin.",
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "allowed_modules": user.allowed_modules,
        },
    }


@router.post("/signup")
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == request.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    allowed_roles = ["viewer", "analyst"]

    requested_role = (
        request.requested_role
        if request.requested_role in allowed_roles
        else "viewer"
    )

    user = User(
        email=request.email,
        full_name=request.full_name,
        password_hash=hash_password(request.password),
        role=requested_role,
        is_active=False,
        allowed_modules=["dashboard"],
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    send_signup_notification_to_admin(
        full_name=request.full_name,
        email=request.email,
        requested_role=requested_role,
    )

    return {
        "message": "Signup request submitted successfully. Please wait for admin approval.",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
        },
    }


@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == request.email).first()

    # Do not reveal whether email exists or not.
    safe_response = {
        "message": "If the email exists, a password reset link has been sent."
    }

    if not user:
        return safe_response

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw_token)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    reset_record = PasswordResetToken(
        user_id=user.id,
        email=user.email,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
    )

    db.add(reset_record)
    db.commit()

    reset_link = f"http://localhost:5173/?reset_token={raw_token}"

    send_password_reset_email(
        full_name=user.full_name,
        email=user.email,
        reset_link=reset_link,
    )

    response = safe_response.copy()

    if settings.ENVIRONMENT == "development":
        response["dev_reset_link"] = reset_link
        response["dev_reset_token"] = raw_token

    return response


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_reset_token(request.token)

    reset_record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )

    if not reset_record:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if reset_record.used:
        raise HTTPException(status_code=400, detail="Reset token already used")

    now = datetime.now(timezone.utc)

    expires_at = reset_record.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise HTTPException(status_code=400, detail="Reset token expired")

    user = db.query(User).filter(User.id == reset_record.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters",
        )

    user.password_hash = hash_password(request.new_password)

    reset_record.used = True
    reset_record.used_at = now

    db.commit()

    return {
        "message": "Password reset successfully. Please login with your new password."
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "allowed_modules": current_user.allowed_modules,
        "is_active": current_user.is_active,
    }