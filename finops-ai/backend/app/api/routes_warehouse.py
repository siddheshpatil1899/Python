from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.warehouse import CostDailyAggregate, WarehouseRefreshLog
from app.services.warehouse_service import refresh_warehouse, get_warehouse_health


router = APIRouter(prefix="/warehouse", tags=["Warehouse"])


@router.post("/refresh")
def refresh(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return refresh_warehouse(db=db, tenant_id=tenant_id)


@router.get("/health")
def health(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    return get_warehouse_health(db=db, tenant_id=tenant_id)


@router.get("/daily-cost")
def daily_cost(
    tenant_id: str = Query(...),
    aggregate_level: str = Query(default="tenant"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(CostDailyAggregate)
        .filter(CostDailyAggregate.tenant_id == tenant_id)
        .filter(CostDailyAggregate.aggregate_level == aggregate_level)
        .order_by(CostDailyAggregate.usage_date.asc())
        .all()
    )

    return [
        {
            "usage_date": item.usage_date,
            "aggregate_level": item.aggregate_level,
            "cloud_provider": item.cloud_provider,
            "account_id": item.account_id,
            "service_name": item.service_name,
            "region": item.region,
            "total_billed_cost": item.total_billed_cost,
            "total_effective_cost": item.total_effective_cost,
            "total_usage_quantity": item.total_usage_quantity,
            "record_count": item.record_count,
        }
        for item in rows
    ]


@router.get("/service-cost")
def service_cost(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            CostDailyAggregate.service_name,
            CostDailyAggregate.cloud_provider,
            func.sum(CostDailyAggregate.total_billed_cost).label("total_cost"),
            func.sum(CostDailyAggregate.record_count).label("record_count"),
        )
        .filter(CostDailyAggregate.tenant_id == tenant_id)
        .filter(CostDailyAggregate.aggregate_level == "service")
        .group_by(
            CostDailyAggregate.service_name,
            CostDailyAggregate.cloud_provider,
        )
        .order_by(func.sum(CostDailyAggregate.total_billed_cost).desc())
        .all()
    )

    return [
        {
            "service_name": row.service_name,
            "cloud_provider": row.cloud_provider,
            "total_cost": round(float(row.total_cost or 0), 2),
            "record_count": int(row.record_count or 0),
        }
        for row in rows
    ]


@router.get("/refresh-logs")
def refresh_logs(
    tenant_id: str = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(WarehouseRefreshLog)
        .filter(WarehouseRefreshLog.tenant_id == tenant_id)
        .order_by(WarehouseRefreshLog.started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": item.id,
            "tenant_id": item.tenant_id,
            "status": item.status,
            "source_record_count": item.source_record_count,
            "aggregate_record_count": item.aggregate_record_count,
            "message": item.message,
            "started_at": item.started_at,
            "finished_at": item.finished_at,
        }
        for item in logs
    ]