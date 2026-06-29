from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class AnomalyFinding(Base):
    __tablename__ = "anomaly_findings"

    id = Column(Integer, primary_key=True, index=True)

    anomaly_key = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=False)
    cloud_provider = Column(String, index=True, nullable=False)
    account_id = Column(String, index=True, nullable=False)

    anomaly_date = Column(Date, index=True, nullable=False)

    level = Column(String, index=True, nullable=False)
    service_name = Column(String, index=True, nullable=True)
    region = Column(String, index=True, nullable=True)

    severity = Column(String, index=True, nullable=False)
    status = Column(String, index=True, default="active")

    current_cost = Column(Float, nullable=False)
    baseline_cost = Column(Float, nullable=False)
    delta_cost = Column(Float, nullable=False)
    delta_percent = Column(Float, nullable=False)

    anomaly_score = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)

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