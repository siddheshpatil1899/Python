from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class CostDailyAggregate(Base):
    __tablename__ = "cost_daily_aggregates"

    id = Column(Integer, primary_key=True, index=True)

    aggregate_key = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=False)

    aggregate_level = Column(String, index=True, nullable=False)
    cloud_provider = Column(String, index=True, nullable=True)
    account_id = Column(String, index=True, nullable=True)
    service_name = Column(String, index=True, nullable=True)
    region = Column(String, index=True, nullable=True)

    usage_date = Column(Date, index=True, nullable=False)

    total_billed_cost = Column(Float, nullable=False)
    total_effective_cost = Column(Float, nullable=False)
    total_usage_quantity = Column(Float, nullable=True)
    record_count = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WarehouseRefreshLog(Base):
    __tablename__ = "warehouse_refresh_logs"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)

    source_record_count = Column(Integer, default=0)
    aggregate_record_count = Column(Integer, default=0)

    message = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)