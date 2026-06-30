from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cost_record import CostRecord


router = APIRouter(prefix="/costs", tags=["Costs"])


def apply_date_filter(query, start_date: Optional[date], end_date: Optional[date]):
    if start_date:
        query = query.filter(CostRecord.usage_date >= start_date)

    if end_date:
        query = query.filter(CostRecord.usage_date <= end_date)

    return query


@router.get("/summary")
def get_cost_summary(
    tenant_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    base_query = db.query(CostRecord).filter(CostRecord.tenant_id == tenant_id)
    base_query = apply_date_filter(base_query, start_date, end_date)

    total_cost = (
        base_query.with_entities(func.coalesce(func.sum(CostRecord.billed_cost), 0))
        .scalar()
    )

    record_count = base_query.with_entities(func.count(CostRecord.id)).scalar()

    total_accounts = (
        base_query.with_entities(func.count(func.distinct(CostRecord.account_id)))
        .scalar()
    )

    total_services = (
        base_query.with_entities(func.count(func.distinct(CostRecord.service_name)))
        .scalar()
    )

    total_providers = (
        base_query.with_entities(func.count(func.distinct(CostRecord.cloud_provider)))
        .scalar()
    )

    total_regions = (
        base_query.with_entities(func.count(func.distinct(CostRecord.region)))
        .scalar()
    )

    latest_usage_date = (
        base_query.with_entities(func.max(CostRecord.usage_date))
        .scalar()
    )

    return {
        "tenant_id": tenant_id,
        "total_cost": round(float(total_cost or 0), 2),
        "record_count": int(record_count or 0),
        "total_accounts": int(total_accounts or 0),
        "total_services": int(total_services or 0),
        "total_providers": int(total_providers or 0),
        "total_regions": int(total_regions or 0),
        "latest_usage_date": str(latest_usage_date) if latest_usage_date else None,
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
    }


@router.get("/provider-breakdown")
def get_provider_breakdown(
    tenant_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            CostRecord.cloud_provider.label("provider"),
            func.coalesce(func.sum(CostRecord.billed_cost), 0).label("total_cost"),
            func.count(CostRecord.id).label("record_count"),
            func.count(func.distinct(CostRecord.account_id)).label("account_count"),
            func.count(func.distinct(CostRecord.service_name)).label("service_count"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
    )

    query = apply_date_filter(query, start_date, end_date)

    rows = (
        query.group_by(CostRecord.cloud_provider)
        .order_by(func.sum(CostRecord.billed_cost).desc())
        .all()
    )

    return [
        {
            "provider": row.provider or "Unknown",
            "total_cost": round(float(row.total_cost or 0), 2),
            "record_count": int(row.record_count or 0),
            "account_count": int(row.account_count or 0),
            "service_count": int(row.service_count or 0),
        }
        for row in rows
    ]


@router.get("/service-cost")
def get_cost_by_service(
    tenant_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            CostRecord.service_name.label("service_name"),
            CostRecord.cloud_provider.label("provider"),
            func.coalesce(func.sum(CostRecord.billed_cost), 0).label("total_cost"),
            func.count(CostRecord.id).label("record_count"),
            func.count(func.distinct(CostRecord.account_id)).label("account_count"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
    )

    query = apply_date_filter(query, start_date, end_date)

    rows = (
        query.group_by(CostRecord.service_name, CostRecord.cloud_provider)
        .order_by(func.sum(CostRecord.billed_cost).desc())
        .all()
    )

    return [
        {
            "service_name": row.service_name or "Unknown",
            "provider": row.provider or "Unknown",
            "total_cost": round(float(row.total_cost or 0), 2),
            "record_count": int(row.record_count or 0),
            "account_count": int(row.account_count or 0),
        }
        for row in rows
    ]


@router.get("/daily")
def get_daily_cost(
    tenant_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            CostRecord.usage_date.label("usage_date"),
            func.coalesce(func.sum(CostRecord.billed_cost), 0).label("total_cost"),
            func.count(CostRecord.id).label("record_count"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
    )

    query = apply_date_filter(query, start_date, end_date)

    rows = (
        query.group_by(CostRecord.usage_date)
        .order_by(CostRecord.usage_date.asc())
        .all()
    )

    return [
        {
            "usage_date": str(row.usage_date),
            "total_cost": round(float(row.total_cost or 0), 2),
            "record_count": int(row.record_count or 0),
        }
        for row in rows
    ]


@router.get("/accounts")
def get_cost_by_account(
    tenant_id: str = Query(...),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            CostRecord.account_id.label("account_id"),
            CostRecord.cloud_provider.label("provider"),
            func.coalesce(func.sum(CostRecord.billed_cost), 0).label("total_cost"),
            func.count(CostRecord.id).label("record_count"),
            func.count(func.distinct(CostRecord.service_name)).label("service_count"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
    )

    query = apply_date_filter(query, start_date, end_date)

    rows = (
        query.group_by(CostRecord.account_id, CostRecord.cloud_provider)
        .order_by(func.sum(CostRecord.billed_cost).desc())
        .all()
    )

    return [
        {
            "account_id": row.account_id,
            "provider": row.provider or "Unknown",
            "total_cost": round(float(row.total_cost or 0), 2),
            "record_count": int(row.record_count or 0),
            "service_count": int(row.service_count or 0),
        }
        for row in rows
    ]