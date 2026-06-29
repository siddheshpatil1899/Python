from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.cost_record import CostRecord


router = APIRouter(prefix="/costs", tags=["Costs"])


@router.get("/summary")
def get_cost_summary(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db)
):
    total_cost = (
        db.query(func.sum(CostRecord.billed_cost))
        .filter(CostRecord.tenant_id == tenant_id)
        .scalar()
    )

    return {
        "tenant_id": tenant_id,
        "total_cost": round(total_cost or 0, 2)
    }


@router.get("/by-service")
def get_cost_by_service(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(
            CostRecord.service_name,
            func.sum(CostRecord.billed_cost).label("total_cost")
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .group_by(CostRecord.service_name)
        .order_by(func.sum(CostRecord.billed_cost).desc())
        .all()
    )

    return [
        {
            "service_name": row.service_name,
            "total_cost": round(row.total_cost, 2)
        }
        for row in rows
    ]


@router.get("/by-region")
def get_cost_by_region(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(
            CostRecord.region,
            func.sum(CostRecord.billed_cost).label("total_cost")
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .group_by(CostRecord.region)
        .order_by(func.sum(CostRecord.billed_cost).desc())
        .all()
    )

    return [
        {
            "region": row.region,
            "total_cost": round(row.total_cost, 2)
        }
        for row in rows
    ]


@router.get("/daily")
def get_daily_cost(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(
            CostRecord.usage_date,
            func.sum(CostRecord.billed_cost).label("total_cost")
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .group_by(CostRecord.usage_date)
        .order_by(CostRecord.usage_date.asc())
        .all()
    )

    return [
        {
            "usage_date": str(row.usage_date),
            "total_cost": round(row.total_cost, 2)
        }
        for row in rows
    ]