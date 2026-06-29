from sqlalchemy import Column, Integer, String, Float, DateTime

from app.core.database import Base


class Pricing(Base):
    __tablename__ = "pricing"

    id = Column(Integer, primary_key=True, index=True)

    provider = Column(String, index=True, nullable=False)
    sku = Column(String, index=True, nullable=False)
    region = Column(String, index=True, nullable=False)

    hourly_rate = Column(Float, nullable=True)
    price_per_gb_month = Column(Float, nullable=True)
    monthly_base_rate = Column(Float, nullable=True)

    updated_at = Column(DateTime(timezone=True), nullable=True)