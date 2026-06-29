from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.waste_finding import WasteFinding
from app.services.waste_rule_engine import run_waste_scan


router = APIRouter(prefix="/waste", tags=["Waste Detection"])


@router.post("/run-scan")
def run_scan(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    result = run_waste_scan(db=db, tenant_id=tenant_id)
    return result


@router.get("/findings")
def get_findings(
    tenant_id: str = Query(...),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(WasteFinding).filter(WasteFinding.tenant_id == tenant_id)

    if status:
        query = query.filter(WasteFinding.status == status)

    findings = query.order_by(WasteFinding.estimated_monthly_saving.desc()).all()

    return [
        {
            "id": finding.id,
            "finding_key": finding.finding_key,
            "tenant_id": finding.tenant_id,
            "cloud_provider": finding.cloud_provider,
            "account_id": finding.account_id,
            "rule_id": finding.rule_id,
            "rule_name": finding.rule_name,
            "service_name": finding.service_name,
            "region": finding.region,
            "resource_id": finding.resource_id,
            "severity": finding.severity,
            "status": finding.status,
            "confidence_score": finding.confidence_score,
            "estimated_monthly_saving": finding.estimated_monthly_saving,
            "current_monthly_cost": finding.current_monthly_cost,
            "title": finding.title,
            "explanation": finding.explanation,
            "recommendation": finding.recommendation,
            "evidence": finding.evidence,
            "first_seen_at": finding.first_seen_at,
            "last_seen_at": finding.last_seen_at,
            "dismissed_at": finding.dismissed_at,
            "resolved_at": finding.resolved_at,
        }
        for finding in findings
    ]


@router.post("/dismiss/{finding_id}")
def dismiss_finding(
    finding_id: int,
    db: Session = Depends(get_db),
):
    finding = db.query(WasteFinding).filter(WasteFinding.id == finding_id).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.status = "dismissed"
    finding.dismissed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Finding dismissed successfully",
        "finding_id": finding_id,
        "status": finding.status,
    }


@router.post("/reactivate/{finding_id}")
def reactivate_finding(
    finding_id: int,
    db: Session = Depends(get_db),
):
    finding = db.query(WasteFinding).filter(WasteFinding.id == finding_id).first()

    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.status = "active"
    finding.dismissed_at = None

    db.commit()

    return {
        "message": "Finding reactivated successfully",
        "finding_id": finding_id,
        "status": finding.status,
    }
@router.get("/summary")
def get_waste_summary(
    tenant_id: str = Query(...),
    db: Session = Depends(get_db),
):
    findings = (
        db.query(WasteFinding)
        .filter(WasteFinding.tenant_id == tenant_id)
        .all()
    )

    total_findings = len(findings)

    active_findings = [
        finding for finding in findings
        if finding.status == "active"
    ]

    dismissed_findings = [
        finding for finding in findings
        if finding.status == "dismissed"
    ]

    resolved_findings = [
        finding for finding in findings
        if finding.status == "resolved"
    ]

    total_estimated_monthly_saving = sum(
        finding.estimated_monthly_saving or 0
        for finding in active_findings
    )

    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for finding in active_findings:
        if finding.severity in severity_counts:
            severity_counts[finding.severity] += 1

    return {
        "tenant_id": tenant_id,
        "total_findings": total_findings,
        "active_findings": len(active_findings),
        "dismissed_findings": len(dismissed_findings),
        "resolved_findings": len(resolved_findings),
        "total_estimated_monthly_saving": round(total_estimated_monthly_saving, 2),
        "severity_counts": severity_counts,
    }