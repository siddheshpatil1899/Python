from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.forecast import CostForecast
from app.services.forecast_engine import run_cost_forecast, get_forecast_summary


router = APIRouter(prefix="/forecast", tags=["Cost Forecasting"])


@router.post("/run")
def run_forecast(
    tenant_id: str = Query(...),
    horizon_days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    result = run_cost_forecast(
        db=db,
        tenant_id=tenant_id,
        horizon_days=horizon_days,
    )

    return result


@router.get("/daily")
def get_daily_forecast(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    latest_training_end_date = (
        db.query(CostForecast.training_end_date)
        .filter(CostForecast.tenant_id == tenant_id)
        .order_by(CostForecast.training_end_date.desc())
        .first()
    )

    if not latest_training_end_date:
        return []

    forecasts = (
        db.query(CostForecast)
        .filter(CostForecast.tenant_id == tenant_id)
        .filter(CostForecast.scope == "tenant")
        .filter(CostForecast.training_end_date == latest_training_end_date[0])
        .order_by(CostForecast.forecast_date.asc())
        .all()
    )

    return [
        {
            "id": item.id,
            "tenant_id": item.tenant_id,
            "scope": item.scope,
            "forecast_date": item.forecast_date,
            "predicted_cost": item.predicted_cost,
            "lower_bound": item.lower_bound,
            "upper_bound": item.upper_bound,
            "model_name": item.model_name,
            "confidence_score": item.confidence_score,
            "horizon_days": item.horizon_days,
            "training_start_date": item.training_start_date,
            "training_end_date": item.training_end_date,
            "evidence": item.evidence,
        }
        for item in forecasts
    ]


@router.get("/summary")
def forecast_summary(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return get_forecast_summary(db=db, tenant_id=tenant_id)