from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON

from app.core.database import Base


class CloudAccount(Base):
    __tablename__ = "cloud_accounts"

    id = Column(String, primary_key=True, index=True)

    tenant_id = Column(String, index=True, nullable=False)
    provider = Column(String, index=True, nullable=False)
    account_id = Column(String, index=True, nullable=False)

    role_arn = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    auth_metadata = Column(JSON, nullable=True)

    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0)
    last_error = Column(String, nullable=True)
    needs_reauth = Column(Boolean, default=False)