from sqlalchemy import Column, Integer, String, Float, DateTime

from app.core.database import Base


class CloudResource(Base):
    __tablename__ = "cloud_resources"

    id = Column(Integer, primary_key=True, index=True)

    resource_id = Column(String, unique=True, index=True, nullable=False)
    resource_type = Column(String, index=True, nullable=False)

    instance_type = Column(String, nullable=True)
    volume_type = Column(String, nullable=True)
    lb_type = Column(String, nullable=True)

    size_gb = Column(Float, nullable=True)
    state = Column(String, index=True, nullable=True)
    state_changed_at = Column(DateTime(timezone=True), nullable=True)

    healthy_target_count = Column(Float, nullable=True)

    tenant_id = Column(String, index=True, nullable=False)
    account_id = Column(String, index=True, nullable=False)
    region = Column(String, index=True, nullable=True)

    refreshed_at = Column(DateTime(timezone=True), nullable=True)