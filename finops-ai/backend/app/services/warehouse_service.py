import hashlib
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cost_record import CostRecord
from app.models.warehouse import CostDailyAggregate, WarehouseRefreshLog


def generate_aggregate_key(
    tenant_id,
    aggregate_level,
    usage_date,
    cloud_provider=None,
    account_id=None,
    service_name=None,
    region=None,
):
    raw_key = "|".join(
        [
            tenant_id or "",
            aggregate_level or "",
            str(usage_date) or "",
            cloud_provider or "",
            account_id or "",
            service_name or "",
            region or "",
        ]
    )

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def insert_aggregate_rows(db: Session, tenant_id: str, aggregate_level: str):
    group_columns = [
        CostRecord.tenant_id,
        CostRecord.usage_date,
    ]

    if aggregate_level in ["provider", "account", "service"]:
        group_columns.append(CostRecord.cloud_provider)

    if aggregate_level in ["account", "service"]:
        group_columns.append(CostRecord.account_id)

    if aggregate_level == "service":
        group_columns.append(CostRecord.service_name)
        group_columns.append(CostRecord.region)

    query = (
        db.query(
            CostRecord.tenant_id.label("tenant_id"),
            CostRecord.usage_date.label("usage_date"),
            CostRecord.cloud_provider.label("cloud_provider"),
            CostRecord.account_id.label("account_id"),
            CostRecord.service_name.label("service_name"),
            CostRecord.region.label("region"),
            func.sum(CostRecord.billed_cost).label("total_billed_cost"),
            func.sum(
                func.coalesce(CostRecord.effective_cost, CostRecord.billed_cost)
            ).label("total_effective_cost"),
            func.sum(CostRecord.usage_quantity).label("total_usage_quantity"),
            func.count(CostRecord.id).label("record_count"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .group_by(*group_columns)
        .all()
    )

    inserted_count = 0

    for row in query:
        cloud_provider = row.cloud_provider if aggregate_level in ["provider", "account", "service"] else None
        account_id = row.account_id if aggregate_level in ["account", "service"] else None
        service_name = row.service_name if aggregate_level == "service" else None
        region = row.region if aggregate_level == "service" else None

        aggregate_key = generate_aggregate_key(
            tenant_id=row.tenant_id,
            aggregate_level=aggregate_level,
            usage_date=row.usage_date,
            cloud_provider=cloud_provider,
            account_id=account_id,
            service_name=service_name,
            region=region,
        )

        aggregate = CostDailyAggregate(
            aggregate_key=aggregate_key,
            tenant_id=row.tenant_id,
            aggregate_level=aggregate_level,
            cloud_provider=cloud_provider,
            account_id=account_id,
            service_name=service_name,
            region=region,
            usage_date=row.usage_date,
            total_billed_cost=round(float(row.total_billed_cost or 0), 2),
            total_effective_cost=round(float(row.total_effective_cost or 0), 2),
            total_usage_quantity=round(float(row.total_usage_quantity or 0), 4),
            record_count=int(row.record_count or 0),
        )

        db.add(aggregate)
        inserted_count += 1

    return inserted_count


def refresh_warehouse(db: Session, tenant_id: str):
    started_at = datetime.now(timezone.utc)

    log = WarehouseRefreshLog(
        tenant_id=tenant_id,
        status="running",
        source_record_count=0,
        aggregate_record_count=0,
        message="Warehouse refresh started",
        started_at=started_at,
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        source_record_count = (
            db.query(CostRecord)
            .filter(CostRecord.tenant_id == tenant_id)
            .count()
        )

        db.query(CostDailyAggregate).filter(
            CostDailyAggregate.tenant_id == tenant_id
        ).delete()

        total_inserted = 0

        for aggregate_level in ["tenant", "provider", "account", "service"]:
            total_inserted += insert_aggregate_rows(
                db=db,
                tenant_id=tenant_id,
                aggregate_level=aggregate_level,
            )

        log.status = "success"
        log.source_record_count = source_record_count
        log.aggregate_record_count = total_inserted
        log.message = "Warehouse refresh completed successfully"
        log.finished_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "tenant_id": tenant_id,
            "status": "success",
            "source_record_count": source_record_count,
            "aggregate_record_count": total_inserted,
            "message": "Warehouse refresh completed successfully",
        }

    except Exception as error:
        db.rollback()

        log.status = "failed"
        log.message = str(error)
        log.finished_at = datetime.now(timezone.utc)

        db.add(log)
        db.commit()

        return {
            "tenant_id": tenant_id,
            "status": "failed",
            "message": str(error),
        }


def get_warehouse_health(db: Session, tenant_id: str):
    source_record_count = (
        db.query(CostRecord)
        .filter(CostRecord.tenant_id == tenant_id)
        .count()
    )

    aggregate_record_count = (
        db.query(CostDailyAggregate)
        .filter(CostDailyAggregate.tenant_id == tenant_id)
        .count()
    )

    date_range = (
        db.query(
            func.min(CostRecord.usage_date).label("start_date"),
            func.max(CostRecord.usage_date).label("end_date"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .first()
    )

    latest_refresh = (
        db.query(WarehouseRefreshLog)
        .filter(WarehouseRefreshLog.tenant_id == tenant_id)
        .order_by(WarehouseRefreshLog.started_at.desc())
        .first()
    )

    return {
        "tenant_id": tenant_id,
        "source_record_count": source_record_count,
        "aggregate_record_count": aggregate_record_count,
        "source_start_date": date_range.start_date if date_range else None,
        "source_end_date": date_range.end_date if date_range else None,
        "warehouse_ready": aggregate_record_count > 0,
        "latest_refresh": {
            "status": latest_refresh.status,
            "source_record_count": latest_refresh.source_record_count,
            "aggregate_record_count": latest_refresh.aggregate_record_count,
            "message": latest_refresh.message,
            "started_at": latest_refresh.started_at,
            "finished_at": latest_refresh.finished_at,
        }
        if latest_refresh
        else None,
    }