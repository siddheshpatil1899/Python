from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models.app_setting import AppSetting
from app.models.user import User
from app.services.email_service import send_user_created_email


router = APIRouter(prefix="/settings", tags=["Settings"])


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str
    allowed_modules: list[str]


class UserUpdateRequest(BaseModel):
    full_name: str
    role: str
    is_active: bool
    allowed_modules: list[str]


class AppSettingRequest(BaseModel):
    tenant_id: str
    data_fetch_mode: str
    fetch_frequency: str
    fetch_time: str
    enabled_modules: list[str]
    notify_emails: list[str]


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.id.asc()).all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "allowed_modules": user.allowed_modules,
        }
        for user in users
    ]


@router.post("/users")
def create_user(
    request: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(User).filter(User.email == request.email).first()

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=request.email,
        full_name=request.full_name,
        password_hash=hash_password(request.password),
        role=request.role,
        is_active=True,
        allowed_modules=request.allowed_modules,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    send_user_created_email(
        full_name=request.full_name,
        email=request.email,
        password=request.password,
        role=request.role,
    )

    return {
        "message": "User created successfully",
        "id": user.id,
        "email": user.email,
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.full_name = request.full_name
    user.role = request.role
    user.is_active = request.is_active
    user.allowed_modules = request.allowed_modules

    db.commit()

    return {
        "message": "User updated successfully",
        "id": user.id,
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own admin account",
        )

    db.delete(user)
    db.commit()

    return {
        "message": "User removed successfully",
        "id": user_id,
    }


@router.get("/app")
def get_app_settings(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    setting = (
        db.query(AppSetting)
        .filter(AppSetting.tenant_id == tenant_id)
        .first()
    )

    if not setting:
        return {
            "tenant_id": tenant_id,
            "data_fetch_mode": "manual",
            "fetch_frequency": "daily",
            "fetch_time": "02:00",
            "enabled_modules": ["cost", "waste", "anomaly", "forecast", "warehouse"],
            "notify_emails": [],
        }

    return {
        "tenant_id": setting.tenant_id,
        "data_fetch_mode": setting.data_fetch_mode,
        "fetch_frequency": setting.fetch_frequency,
        "fetch_time": setting.fetch_time,
        "enabled_modules": setting.enabled_modules,
        "notify_emails": setting.notify_emails,
    }


@router.post("/app")
def save_app_settings(
    request: AppSettingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    setting = (
        db.query(AppSetting)
        .filter(AppSetting.tenant_id == request.tenant_id)
        .first()
    )

    if not setting:
        setting = AppSetting(
            tenant_id=request.tenant_id,
            data_fetch_mode=request.data_fetch_mode,
            fetch_frequency=request.fetch_frequency,
            fetch_time=request.fetch_time,
            enabled_modules=request.enabled_modules,
            notify_emails=request.notify_emails,
        )
        db.add(setting)
    else:
        setting.data_fetch_mode = request.data_fetch_mode
        setting.fetch_frequency = request.fetch_frequency
        setting.fetch_time = request.fetch_time
        setting.enabled_modules = request.enabled_modules
        setting.notify_emails = request.notify_emails

    db.commit()

    return {
        "message": "Settings saved successfully",
        "tenant_id": request.tenant_id,
    }