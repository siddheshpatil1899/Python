from fastapi import FastAPI

from app.core.database import Base, engine

from app.models.cost_record import CostRecord
from app.models.waste_finding import WasteFinding
from app.models.tenant import Tenant
from app.models.cloud_account import CloudAccount
from app.models.cloud_resource import CloudResource
from app.models.resource_metric import ResourceMetric
from app.models.pricing import Pricing

from app.api.routes_cost import router as cost_router
from app.api.routes_waste import router as waste_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="FinOps AI")

app.include_router(cost_router)
app.include_router(waste_router)


@app.get("/")
def root():
    return {
        "message": "FinOps AI backend is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }