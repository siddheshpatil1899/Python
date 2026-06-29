from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class CostRecord(Base):
    __tablename__ = "cost_records"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True, nullable=False)
    cloud_provider = Column(String, index=True, nullable=False)

    account_id = Column(String, index=True, nullable=False)
    service_name = Column(String, index=True, nullable=False)
    region = Column(String, index=True, nullable=True)

    usage_date = Column(Date, index=True, nullable=False)

    usage_quantity = Column(Float, nullable=True)
    usage_unit = Column(String, nullable=True)

    billed_cost = Column(Float, nullable=False)
    effective_cost = Column(Float, nullable=True)
    currency = Column(String, default="USD")

    resource_id = Column(String, index=True, nullable=True)
    tags = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())