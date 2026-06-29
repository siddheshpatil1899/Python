import hashlib
from datetime import timedelta

import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cost_record import CostRecord
from app.models.forecast import CostForecast
from app.models.tenant import Tenant


MIN_HISTORY_DAYS = 14
DEFAULT_HORIZON_DAYS = 30


def generate_forecast_key(
    tenant_id,
    scope,
    forecast_date,
    account_id=None,
    service_name=None,
    region=None,
):
    raw_key = "|".join(
        [
            tenant_id or "",
            scope or "",
            str(forecast_date) or "",
            account_id or "",
            service_name or "",
            region or "",
        ]
    )

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def clamp_confidence(value):
    return max(0.0, min(1.0, round(value, 2)))


def get_daily_tenant_costs(db: Session, tenant_id: str):
    rows = (
        db.query(
            CostRecord.usage_date,
            func.sum(CostRecord.billed_cost).label("daily_cost"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .group_by(CostRecord.usage_date)
        .order_by(CostRecord.usage_date.asc())
        .all()
    )

    return pd.DataFrame(
        [
            {
                "usage_date": row.usage_date,
                "daily_cost": float(row.daily_cost or 0),
            }
            for row in rows
        ]
    )


def prepare_daily_series(daily_df: pd.DataFrame):
    df = daily_df.copy()
    df["usage_date"] = pd.to_datetime(df["usage_date"])
    df = df.sort_values("usage_date")

    start_date = df["usage_date"].min()
    end_date = df["usage_date"].max()

    full_dates = pd.date_range(start=start_date, end=end_date, freq="D")

    df = (
        df.set_index("usage_date")
        .reindex(full_dates)
        .rename_axis("usage_date")
        .reset_index()
    )

    df["daily_cost"] = df["daily_cost"].fillna(0.0)

    df["day_index"] = range(len(df))
    df["day_of_week"] = df["usage_date"].dt.dayofweek

    return df


def build_training_features(df: pd.DataFrame):
    features = pd.DataFrame()
    features["day_index"] = df["day_index"]
    features["day_of_week"] = df["day_of_week"]

    return features


def build_future_features(last_day_index: int, future_dates):
    future_df = pd.DataFrame()
    future_df["forecast_date"] = pd.to_datetime(future_dates)
    future_df["day_index"] = range(last_day_index + 1, last_day_index + 1 + len(future_dates))
    future_df["day_of_week"] = future_df["forecast_date"].dt.dayofweek

    features = pd.DataFrame()
    features["day_index"] = future_df["day_index"]
    features["day_of_week"] = future_df["day_of_week"]

    return future_df, features


def calculate_confidence(history_days, residual_std, average_daily_cost):
    history_score = min(history_days / 60, 1.0)

    if average_daily_cost <= 0:
        stability_score = 0.5
    else:
        volatility_ratio = residual_std / average_daily_cost
        stability_score = max(0.0, 1.0 - volatility_ratio)

    confidence = (history_score * 0.5) + (stability_score * 0.5)

    return clamp_confidence(confidence)


def upsert_forecast(db: Session, forecast_data: dict):
    existing = (
        db.query(CostForecast)
        .filter(CostForecast.forecast_key == forecast_data["forecast_key"])
        .first()
    )

    if existing:
        existing.predicted_cost = forecast_data["predicted_cost"]
        existing.lower_bound = forecast_data["lower_bound"]
        existing.upper_bound = forecast_data["upper_bound"]
        existing.model_name = forecast_data["model_name"]
        existing.confidence_score = forecast_data["confidence_score"]
        existing.horizon_days = forecast_data["horizon_days"]
        existing.training_start_date = forecast_data["training_start_date"]
        existing.training_end_date = forecast_data["training_end_date"]
        existing.evidence = forecast_data["evidence"]

        return existing

    new_forecast = CostForecast(**forecast_data)
    db.add(new_forecast)

    return new_forecast


def run_cost_forecast(
    db: Session,
    tenant_id: str,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
):
    daily_df = get_daily_tenant_costs(db=db, tenant_id=tenant_id)

    if daily_df.empty:
        return {
            "tenant_id": tenant_id,
            "forecasts_created": 0,
            "message": "No cost data available for forecasting",
        }

    prepared_df = prepare_daily_series(daily_df)

    if len(prepared_df) < MIN_HISTORY_DAYS:
        return {
            "tenant_id": tenant_id,
            "forecasts_created": 0,
            "history_days": len(prepared_df),
            "message": "Not enough historical data for forecasting",
        }

    X = build_training_features(prepared_df)
    y = prepared_df["daily_cost"]

    model = LinearRegression()
    model.fit(X, y)

    fitted_values = model.predict(X)
    residuals = y - fitted_values
    residual_std = float(np.std(residuals))

    average_daily_cost = float(np.mean(y))

    confidence_score = calculate_confidence(
        history_days=len(prepared_df),
        residual_std=residual_std,
        average_daily_cost=average_daily_cost,
    )

    last_date = prepared_df["usage_date"].max().date()
    last_day_index = int(prepared_df["day_index"].max())

    future_dates = [
        last_date + timedelta(days=day)
        for day in range(1, horizon_days + 1)
    ]

    future_df, future_features = build_future_features(
        last_day_index=last_day_index,
        future_dates=future_dates,
    )

    predictions = model.predict(future_features)

    forecasts_created = 0

    training_start_date = prepared_df["usage_date"].min().date()
    training_end_date = prepared_df["usage_date"].max().date()

    for index, prediction in enumerate(predictions):
        forecast_date = future_df.iloc[index]["forecast_date"].date()

        predicted_cost = max(float(prediction), 0.0)
        lower_bound = max(predicted_cost - (1.96 * residual_std), 0.0)
        upper_bound = predicted_cost + (1.96 * residual_std)

        forecast_key = generate_forecast_key(
            tenant_id=tenant_id,
            scope="tenant",
            forecast_date=forecast_date,
        )

        forecast_data = {
            "forecast_key": forecast_key,
            "tenant_id": tenant_id,
            "scope": "tenant",
            "cloud_provider": "MULTI",
            "account_id": None,
            "service_name": None,
            "region": None,
            "forecast_date": forecast_date,
            "predicted_cost": round(predicted_cost, 2),
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2),
            "model_name": "LinearRegressionTrend",
            "confidence_score": confidence_score,
            "horizon_days": horizon_days,
            "training_start_date": training_start_date,
            "training_end_date": training_end_date,
            "evidence": {
                "history_days": len(prepared_df),
                "average_daily_cost": round(average_daily_cost, 2),
                "residual_std": round(residual_std, 2),
                "features": ["day_index", "day_of_week"],
                "forecast_start_date": str(future_dates[0]),
                "forecast_end_date": str(future_dates[-1]),
            },
        }

        upsert_forecast(db=db, forecast_data=forecast_data)
        forecasts_created += 1

    db.commit()

    total_forecasted_cost = float(sum(max(value, 0.0) for value in predictions))

    return {
        "tenant_id": tenant_id,
        "scope": "tenant",
        "history_days": len(prepared_df),
        "horizon_days": horizon_days,
        "forecasts_created": forecasts_created,
        "training_start_date": str(training_start_date),
        "training_end_date": str(training_end_date),
        "forecast_start_date": str(future_dates[0]),
        "forecast_end_date": str(future_dates[-1]),
        "total_forecasted_cost": round(total_forecasted_cost, 2),
        "confidence_score": confidence_score,
        "message": "Cost forecast completed successfully",
    }


def get_latest_forecast_training_end_date(db: Session, tenant_id: str):
    row = (
        db.query(func.max(CostForecast.training_end_date).label("latest_date"))
        .filter(CostForecast.tenant_id == tenant_id)
        .first()
    )

    return row.latest_date if row else None


def get_forecast_summary(db: Session, tenant_id: str):
    latest_training_end_date = get_latest_forecast_training_end_date(
        db=db,
        tenant_id=tenant_id,
    )

    if not latest_training_end_date:
        return {
            "tenant_id": tenant_id,
            "message": "No forecast data available. Run forecast first.",
        }

    forecasts = (
        db.query(CostForecast)
        .filter(CostForecast.tenant_id == tenant_id)
        .filter(CostForecast.scope == "tenant")
        .filter(CostForecast.training_end_date == latest_training_end_date)
        .order_by(CostForecast.forecast_date.asc())
        .all()
    )

    if not forecasts:
        return {
            "tenant_id": tenant_id,
            "message": "No forecast data available. Run forecast first.",
        }

    total_forecasted_cost = sum(item.predicted_cost or 0 for item in forecasts)
    average_daily_forecast = total_forecasted_cost / len(forecasts)

    peak_forecast = max(forecasts, key=lambda item: item.predicted_cost)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    monthly_budget = tenant.monthly_budget if tenant else None

    if monthly_budget:
        budget_gap = monthly_budget - total_forecasted_cost
        budget_utilization_percent = (total_forecasted_cost / monthly_budget) * 100

        if total_forecasted_cost > monthly_budget:
            budget_status = "over_budget"
        elif budget_utilization_percent >= 80:
            budget_status = "at_risk"
        else:
            budget_status = "within_budget"
    else:
        budget_gap = None
        budget_utilization_percent = None
        budget_status = "budget_not_configured"

    return {
        "tenant_id": tenant_id,
        "forecast_days": len(forecasts),
        "forecast_start_date": forecasts[0].forecast_date,
        "forecast_end_date": forecasts[-1].forecast_date,
        "training_end_date": latest_training_end_date,
        "total_forecasted_cost": round(total_forecasted_cost, 2),
        "average_daily_forecast": round(average_daily_forecast, 2),
        "peak_forecast_date": peak_forecast.forecast_date,
        "peak_forecast_cost": round(peak_forecast.predicted_cost, 2),
        "monthly_budget": monthly_budget,
        "budget_status": budget_status,
        "budget_gap": round(budget_gap, 2) if budget_gap is not None else None,
        "budget_utilization_percent": round(budget_utilization_percent, 2)
        if budget_utilization_percent is not None
        else None,
        "confidence_score": forecasts[0].confidence_score,
        "model_name": forecasts[0].model_name,
    }