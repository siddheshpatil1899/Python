from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.anomaly import AnomalyFinding
from app.services.anomaly_engine import run_anomaly_scan


router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection"])


@router.post("/run-scan")
def run_scan(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    result = run_anomaly_scan(db=db, tenant_id=tenant_id)
    return result


@router.get("/findings")
def get_anomalies(
    tenant_id: str = Query(...),
    status: str | None = Query(default=None),
    level: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(AnomalyFinding).filter(AnomalyFinding.tenant_id == tenant_id)

    if status:
        query = query.filter(AnomalyFinding.status == status)

    if level:
        query = query.filter(AnomalyFinding.level == level)

    anomalies = (
        query
        .order_by(AnomalyFinding.delta_cost.desc())
        .all()
    )

    return [
        {
            "id": anomaly.id,
            "anomaly_key": anomaly.anomaly_key,
            "tenant_id": anomaly.tenant_id,
            "cloud_provider": anomaly.cloud_provider,
            "account_id": anomaly.account_id,
            "anomaly_date": anomaly.anomaly_date,
            "level": anomaly.level,
            "service_name": anomaly.service_name,
            "region": anomaly.region,
            "severity": anomaly.severity,
            "status": anomaly.status,
            "current_cost": anomaly.current_cost,
            "baseline_cost": anomaly.baseline_cost,
            "delta_cost": anomaly.delta_cost,
            "delta_percent": anomaly.delta_percent,
            "anomaly_score": anomaly.anomaly_score,
            "confidence_score": anomaly.confidence_score,
            "title": anomaly.title,
            "explanation": anomaly.explanation,
            "recommendation": anomaly.recommendation,
            "evidence": anomaly.evidence,
            "first_seen_at": anomaly.first_seen_at,
            "last_seen_at": anomaly.last_seen_at,
            "dismissed_at": anomaly.dismissed_at,
            "resolved_at": anomaly.resolved_at,
        }
        for anomaly in anomalies
    ]


@router.get("/summary")
def get_anomaly_summary(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    anomalies = (
        db.query(AnomalyFinding)
        .filter(AnomalyFinding.tenant_id == tenant_id)
        .all()
    )

    active = [item for item in anomalies if item.status == "active"]
    dismissed = [item for item in anomalies if item.status == "dismissed"]
    resolved = [item for item in anomalies if item.status == "resolved"]

    total_delta_cost = sum(item.delta_cost or 0 for item in active)

    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    level_counts = {
        "account": 0,
        "service": 0,
    }

    for item in active:
        if item.severity in severity_counts:
            severity_counts[item.severity] += 1

        if item.level in level_counts:
            level_counts[item.level] += 1

    return {
        "tenant_id": tenant_id,
        "total_anomalies": len(anomalies),
        "active_anomalies": len(active),
        "dismissed_anomalies": len(dismissed),
        "resolved_anomalies": len(resolved),
        "active_delta_cost": round(total_delta_cost, 2),
        "severity_counts": severity_counts,
        "level_counts": level_counts,
    }


@router.post("/dismiss/{anomaly_id}")
def dismiss_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db),
):
    anomaly = db.query(AnomalyFinding).filter(AnomalyFinding.id == anomaly_id).first()

    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.status = "dismissed"
    anomaly.dismissed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Anomaly dismissed successfully",
        "anomaly_id": anomaly_id,
        "status": anomaly.status,
    }


@router.post("/reactivate/{anomaly_id}")
def reactivate_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db),
):
    anomaly = db.query(AnomalyFinding).filter(AnomalyFinding.id == anomaly_id).first()

    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.status = "active"
    anomaly.dismissed_at = None

    db.commit()

    return {
        "message": "Anomaly reactivated successfully",
        "anomaly_id": anomaly_id,
        "status": anomaly.status,
    }