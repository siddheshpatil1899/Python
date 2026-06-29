from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class WasteFinding(Base):
    __tablename__ = "waste_findings"

    id = Column(Integer, primary_key=True, index=True)

    finding_key = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=False)
    cloud_provider = Column(String, index=True, nullable=False)
    account_id = Column(String, index=True, nullable=False)

    rule_id = Column(String, index=True, nullable=False)
    rule_name = Column(String, nullable=False)

    service_name = Column(String, index=True, nullable=False)
    region = Column(String, index=True, nullable=True)
    resource_id = Column(String, index=True, nullable=True)

    severity = Column(String, index=True, nullable=False)
    status = Column(String, index=True, default="active")

    confidence_score = Column(Float, nullable=False)
    estimated_monthly_saving = Column(Float, nullable=False)

    current_monthly_cost = Column(Float, nullable=True)

    title = Column(String, nullable=False)
    explanation = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)

    evidence = Column(JSON, nullable=True)

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())