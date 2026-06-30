from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import global_exception_handler

from app.models.cost_record import CostRecord
from app.models.waste_finding import WasteFinding
from app.models.anomaly import AnomalyFinding
from app.models.forecast import CostForecast
from app.models.chat_message import ChatMessage
from app.models.warehouse import CostDailyAggregate, WarehouseRefreshLog
from app.models.password_reset import PasswordResetToken

from app.models.tenant import Tenant
from app.models.cloud_account import CloudAccount
from app.models.cloud_resource import CloudResource
from app.models.resource_metric import ResourceMetric
from app.models.pricing import Pricing

from app.models.user import User
from app.models.app_setting import AppSetting

from app.api.v1_router import api_v1_router

from app.api.routes_health import router as health_router
from app.api.routes_cost import router as cost_router
from app.api.routes_waste import router as waste_router
from app.api.routes_anomaly import router as anomaly_router
from app.api.routes_forecast import router as forecast_router
from app.api.routes_chat import router as chat_router
from app.api.routes_warehouse import router as warehouse_router


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="FinOps AI backend for cost visibility, waste detection, anomaly detection, forecasting, chatbot, warehouse reporting, authentication, and settings.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(Exception, global_exception_handler)


# New professional API routes
app.include_router(api_v1_router)


# Legacy routes kept so old frontend/API URLs continue working
app.include_router(health_router)
app.include_router(cost_router)
app.include_router(waste_router)
app.include_router(anomaly_router)
app.include_router(forecast_router)
app.include_router(chat_router)
app.include_router(warehouse_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "FinOps AI backend is running",
        "version": "1.0.0",
        "docs_url": "/docs",
        "api_v1_prefix": settings.API_V1_PREFIX,
    }