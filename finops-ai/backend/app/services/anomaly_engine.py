import hashlib
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cost_record import CostRecord
from app.models.anomaly import AnomalyFinding


MIN_POINTS_FOR_MODEL = 14
CONTAMINATION_RATE = 0.08
MIN_SPIKE_AMOUNT = 25.0
MIN_SPIKE_PERCENT = 40.0


def generate_anomaly_key(
    tenant_id,
    account_id,
    anomaly_date,
    level,
    service_name=None,
    region=None,
):
    raw_key = "|".join(
        [
            tenant_id or "",
            account_id or "",
            str(anomaly_date) or "",
            level or "",
            service_name or "",
            region or "",
        ]
    )

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def calculate_severity(delta_cost):
    if delta_cost >= 1000:
        return "critical"

    if delta_cost >= 500:
        return "high"

    if delta_cost >= 100:
        return "medium"

    return "low"


def clamp_confidence(value):
    return max(0.0, min(1.0, round(value, 2)))


def get_daily_account_costs(db: Session, tenant_id: str):
    rows = (
        db.query(
            CostRecord.cloud_provider,
            CostRecord.account_id,
            CostRecord.usage_date,
            func.sum(CostRecord.billed_cost).label("daily_cost"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .group_by(
            CostRecord.cloud_provider,
            CostRecord.account_id,
            CostRecord.usage_date,
        )
        .order_by(CostRecord.account_id.asc(), CostRecord.usage_date.asc())
        .all()
    )

    return pd.DataFrame(
        [
            {
                "cloud_provider": row.cloud_provider,
                "account_id": row.account_id,
                "usage_date": row.usage_date,
                "daily_cost": float(row.daily_cost or 0),
            }
            for row in rows
        ]
    )


def build_features(account_df: pd.DataFrame):
    df = account_df.copy()
    df = df.sort_values("usage_date")

    df["usage_date"] = pd.to_datetime(df["usage_date"])
    df["day_of_week"] = df["usage_date"].dt.dayofweek

    df["rolling_7d_avg"] = (
        df["daily_cost"]
        .rolling(window=7, min_periods=3)
        .mean()
        .fillna(df["daily_cost"].mean())
    )

    df["rolling_7d_std"] = (
        df["daily_cost"]
        .rolling(window=7, min_periods=3)
        .std()
        .fillna(0)
    )

    df["cost_vs_rolling_avg"] = df["daily_cost"] - df["rolling_7d_avg"]

    df["cost_ratio"] = np.where(
        df["rolling_7d_avg"] > 0,
        df["daily_cost"] / df["rolling_7d_avg"],
        1.0,
    )

    feature_columns = [
        "daily_cost",
        "day_of_week",
        "rolling_7d_avg",
        "rolling_7d_std",
        "cost_vs_rolling_avg",
        "cost_ratio",
    ]

    return df, feature_columns


def get_service_drilldown(
    db: Session,
    tenant_id: str,
    account_id: str,
    anomaly_date,
):
    current_rows = (
        db.query(
            CostRecord.cloud_provider,
            CostRecord.service_name,
            CostRecord.region,
            func.sum(CostRecord.billed_cost).label("current_cost"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .filter(CostRecord.account_id == account_id)
        .filter(CostRecord.usage_date == anomaly_date)
        .group_by(
            CostRecord.cloud_provider,
            CostRecord.service_name,
            CostRecord.region,
        )
        .all()
    )

    findings = []

    for current in current_rows:
        baseline_row = (
            db.query(
                func.avg(CostRecord.billed_cost).label("avg_cost")
            )
            .filter(CostRecord.tenant_id == tenant_id)
            .filter(CostRecord.account_id == account_id)
            .filter(CostRecord.service_name == current.service_name)
            .filter(CostRecord.region == current.region)
            .filter(CostRecord.usage_date < anomaly_date)
            .first()
        )

        baseline_cost = float(baseline_row.avg_cost or 0)
        current_cost = float(current.current_cost or 0)

        delta_cost = current_cost - baseline_cost

        if baseline_cost > 0:
            delta_percent = (delta_cost / baseline_cost) * 100
        else:
            delta_percent = 100.0 if current_cost > 0 else 0.0

        if delta_cost < MIN_SPIKE_AMOUNT:
            continue

        if delta_percent < MIN_SPIKE_PERCENT:
            continue

        findings.append(
            {
                "cloud_provider": current.cloud_provider,
                "service_name": current.service_name,
                "region": current.region,
                "current_cost": round(current_cost, 2),
                "baseline_cost": round(baseline_cost, 2),
                "delta_cost": round(delta_cost, 2),
                "delta_percent": round(delta_percent, 2),
            }
        )

    findings.sort(key=lambda item: item["delta_cost"], reverse=True)

    return findings


def build_anomaly_data(
    tenant_id,
    cloud_provider,
    account_id,
    anomaly_date,
    level,
    current_cost,
    baseline_cost,
    delta_cost,
    delta_percent,
    anomaly_score,
    confidence_score,
    service_name=None,
    region=None,
    evidence=None,
):
    anomaly_key = generate_anomaly_key(
        tenant_id=tenant_id,
        account_id=account_id,
        anomaly_date=anomaly_date,
        level=level,
        service_name=service_name,
        region=region,
    )

    if level == "account":
        title = f"Cost spike detected for account {account_id}"
        explanation = (
            f"Account {account_id} spent ${current_cost:.2f} on {anomaly_date}, "
            f"which is ${delta_cost:.2f} above the baseline of ${baseline_cost:.2f}."
        )
        recommendation = (
            "Review the service-level drill-down to identify which services caused the spike."
        )
    else:
        title = f"Cost spike detected in {service_name}"
        explanation = (
            f"{service_name} cost increased by ${delta_cost:.2f} on {anomaly_date}, "
            f"which is {delta_percent:.2f}% above baseline."
        )
        recommendation = (
            "Check usage, recent deployments, scaling events, storage growth, or traffic changes for this service."
        )

    return {
        "anomaly_key": anomaly_key,
        "tenant_id": tenant_id,
        "cloud_provider": cloud_provider,
        "account_id": account_id,
        "anomaly_date": anomaly_date,
        "level": level,
        "service_name": service_name,
        "region": region,
        "severity": calculate_severity(delta_cost),
        "status": "active",
        "current_cost": round(current_cost, 2),
        "baseline_cost": round(baseline_cost, 2),
        "delta_cost": round(delta_cost, 2),
        "delta_percent": round(delta_percent, 2),
        "anomaly_score": round(float(anomaly_score), 4),
        "confidence_score": clamp_confidence(confidence_score),
        "title": title,
        "explanation": explanation,
        "recommendation": recommendation,
        "evidence": evidence or {},
    }


def upsert_anomaly(db: Session, anomaly_data: dict):
    existing = (
        db.query(AnomalyFinding)
        .filter(AnomalyFinding.anomaly_key == anomaly_data["anomaly_key"])
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing:
        existing.last_seen_at = now
        existing.evidence = anomaly_data.get("evidence")

        if existing.status != "dismissed":
            existing.status = "active"
            existing.resolved_at = None
            existing.current_cost = anomaly_data["current_cost"]
            existing.baseline_cost = anomaly_data["baseline_cost"]
            existing.delta_cost = anomaly_data["delta_cost"]
            existing.delta_percent = anomaly_data["delta_percent"]
            existing.anomaly_score = anomaly_data["anomaly_score"]
            existing.confidence_score = anomaly_data["confidence_score"]
            existing.severity = anomaly_data["severity"]
            existing.title = anomaly_data["title"]
            existing.explanation = anomaly_data["explanation"]
            existing.recommendation = anomaly_data["recommendation"]

        return existing

    new_anomaly = AnomalyFinding(**anomaly_data)
    db.add(new_anomaly)

    return new_anomaly


def run_anomaly_scan(db: Session, tenant_id: str):
    daily_df = get_daily_account_costs(db, tenant_id)

    if daily_df.empty:
        return {
            "tenant_id": tenant_id,
            "accounts_scanned": 0,
            "anomalies_detected": 0,
            "message": "No cost data available for anomaly detection",
        }

    all_anomalies = []
    accounts_scanned = 0

    for account_id, account_df in daily_df.groupby("account_id"):
        account_df = account_df.sort_values("usage_date")

        if len(account_df) < MIN_POINTS_FOR_MODEL:
            continue

        accounts_scanned += 1

        feature_df, feature_columns = build_features(account_df)

        scaler = StandardScaler()
        X = scaler.fit_transform(feature_df[feature_columns])

        model = IsolationForest(
            n_estimators=100,
            contamination=CONTAMINATION_RATE,
            random_state=42,
        )

        predictions = model.fit_predict(X)
        scores = model.decision_function(X)

        feature_df["prediction"] = predictions
        feature_df["anomaly_score"] = scores

        for _, row in feature_df.iterrows():
            if int(row["prediction"]) != -1:
                continue

            current_cost = float(row["daily_cost"])
            baseline_cost = float(row["rolling_7d_avg"])
            delta_cost = current_cost - baseline_cost

            if baseline_cost > 0:
                delta_percent = (delta_cost / baseline_cost) * 100
            else:
                delta_percent = 100.0 if current_cost > 0 else 0.0

            if delta_cost < MIN_SPIKE_AMOUNT:
                continue

            if delta_percent < MIN_SPIKE_PERCENT:
                continue

            anomaly_date = row["usage_date"].date()
            cloud_provider = row["cloud_provider"]

            account_anomaly = build_anomaly_data(
                tenant_id=tenant_id,
                cloud_provider=cloud_provider,
                account_id=account_id,
                anomaly_date=anomaly_date,
                level="account",
                current_cost=current_cost,
                baseline_cost=baseline_cost,
                delta_cost=delta_cost,
                delta_percent=delta_percent,
                anomaly_score=abs(float(row["anomaly_score"])),
                confidence_score=0.85,
                evidence={
                    "model": "IsolationForest",
                    "features": feature_columns,
                    "rolling_7d_avg": round(baseline_cost, 2),
                    "daily_cost": round(current_cost, 2),
                    "delta_cost": round(delta_cost, 2),
                    "delta_percent": round(delta_percent, 2),
                },
            )

            all_anomalies.append(account_anomaly)

            service_drilldown = get_service_drilldown(
                db=db,
                tenant_id=tenant_id,
                account_id=account_id,
                anomaly_date=anomaly_date,
            )

            for service in service_drilldown[:3]:
                service_anomaly = build_anomaly_data(
                    tenant_id=tenant_id,
                    cloud_provider=service["cloud_provider"],
                    account_id=account_id,
                    anomaly_date=anomaly_date,
                    level="service",
                    service_name=service["service_name"],
                    region=service["region"],
                    current_cost=service["current_cost"],
                    baseline_cost=service["baseline_cost"],
                    delta_cost=service["delta_cost"],
                    delta_percent=service["delta_percent"],
                    anomaly_score=abs(float(row["anomaly_score"])),
                    confidence_score=0.78,
                    evidence={
                        "parent_account_anomaly_date": str(anomaly_date),
                        "service_ranked_by_delta_cost": True,
                    },
                )

                all_anomalies.append(service_anomaly)

    seen_keys = set()

    for anomaly_data in all_anomalies:
        seen_keys.add(anomaly_data["anomaly_key"])
        upsert_anomaly(db, anomaly_data)

    active_anomalies = (
        db.query(AnomalyFinding)
        .filter(AnomalyFinding.tenant_id == tenant_id)
        .filter(AnomalyFinding.status == "active")
        .all()
    )

    now = datetime.now(timezone.utc)

    for anomaly in active_anomalies:
        if anomaly.anomaly_key not in seen_keys:
            anomaly.status = "resolved"
            anomaly.resolved_at = now

    db.commit()

    return {
        "tenant_id": tenant_id,
        "accounts_scanned": accounts_scanned,
        "anomalies_detected": len(all_anomalies),
        "message": "Anomaly scan completed successfully",
    }