from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_settings import router as settings_router
from app.api.routes_health import router as health_router
from app.api.routes_cost import router as cost_router
from app.api.routes_waste import router as waste_router
from app.api.routes_anomaly import router as anomaly_router
from app.api.routes_forecast import router as forecast_router
from app.api.routes_chat import router as chat_router
from app.api.routes_warehouse import router as warehouse_router


api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(settings_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(cost_router)
api_v1_router.include_router(waste_router)
api_v1_router.include_router(anomaly_router)
api_v1_router.include_router(forecast_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(warehouse_router)