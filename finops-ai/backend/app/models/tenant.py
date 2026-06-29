from sqlalchemy import Column, String, Float, DateTime

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    plan_tier = Column(String, nullable=True)
    monthly_budget = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)