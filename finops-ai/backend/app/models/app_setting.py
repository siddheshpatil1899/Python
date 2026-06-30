from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True, nullable=False)

    data_fetch_mode = Column(String, nullable=False, default="manual")
    fetch_frequency = Column(String, nullable=False, default="daily")
    fetch_time = Column(String, nullable=False, default="02:00")

    enabled_modules = Column(JSON, nullable=True)
    notify_emails = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )