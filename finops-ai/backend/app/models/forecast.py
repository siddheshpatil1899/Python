from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class CostForecast(Base):
    __tablename__ = "cost_forecasts"

    id = Column(Integer, primary_key=True, index=True)

    forecast_key = Column(String, unique=True, index=True, nullable=False)

    tenant_id = Column(String, index=True, nullable=False)

    scope = Column(String, index=True, nullable=False)
    cloud_provider = Column(String, index=True, nullable=True)
    account_id = Column(String, index=True, nullable=True)
    service_name = Column(String, index=True, nullable=True)
    region = Column(String, index=True, nullable=True)

    forecast_date = Column(Date, index=True, nullable=False)

    predicted_cost = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)

    model_name = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)

    horizon_days = Column(Integer, nullable=False)

    training_start_date = Column(Date, nullable=False)
    training_end_date = Column(Date, nullable=False)

    evidence = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())