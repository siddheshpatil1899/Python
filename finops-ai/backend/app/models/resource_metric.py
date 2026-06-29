from sqlalchemy import Column, Integer, String, Float, Date

from app.core.database import Base


class ResourceMetric(Base):
    __tablename__ = "resource_metrics"

    id = Column(Integer, primary_key=True, index=True)

    tenant_id = Column(String, index=True, nullable=False)
    resource_id = Column(String, index=True, nullable=False)

    metric_name = Column(String, index=True, nullable=False)
    metric_date = Column(Date, index=True, nullable=False)
    value = Column(Float, nullable=False)