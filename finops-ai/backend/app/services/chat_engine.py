from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cost_record import CostRecord
from app.models.waste_finding import WasteFinding
from app.models.anomaly import AnomalyFinding
from app.models.forecast import CostForecast
from app.models.tenant import Tenant
from app.models.chat_message import ChatMessage


def detect_intent(question: str):
    text = question.lower()

    if any(word in text for word in ["overview", "summary", "dashboard", "status"]):
        return "overall_summary"

    if any(word in text for word in ["total cost", "spend", "spent", "cloud cost", "cost summary"]):
        return "cost_summary"

    if any(word in text for word in ["top service", "services", "highest cost", "most expensive"]):
        return "top_services"

    if any(word in text for word in ["waste", "saving", "savings", "idle", "unused", "rightsizing"]):
        return "waste_summary"

    if any(word in text for word in ["anomaly", "anomalies", "spike", "unusual", "sudden increase"]):
        return "anomaly_summary"

    if any(word in text for word in ["forecast", "predict", "prediction", "future", "next month"]):
        return "forecast_summary"

    if any(word in text for word in ["budget", "over budget", "within budget"]):
        return "budget_summary"

    return "overall_summary"


def get_cost_summary(db: Session, tenant_id: str):
    row = (
        db.query(
            func.sum(CostRecord.billed_cost).label("total_cost"),
            func.count(CostRecord.id).label("record_count"),
            func.min(CostRecord.usage_date).label("start_date"),
            func.max(CostRecord.usage_date).label("end_date"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .first()
    )

    total_cost = float(row.total_cost or 0)

    return {
        "total_cost": round(total_cost, 2),
        "record_count": int(row.record_count or 0),
        "start_date": str(row.start_date) if row.start_date else None,
        "end_date": str(row.end_date) if row.end_date else None,
    }


def get_top_services(db: Session, tenant_id: str, limit: int = 5):
    rows = (
        db.query(
            CostRecord.service_name,
            func.sum(CostRecord.billed_cost).label("total_cost"),
        )
        .filter(CostRecord.tenant_id == tenant_id)
        .group_by(CostRecord.service_name)
        .order_by(func.sum(CostRecord.billed_cost).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "service_name": row.service_name,
            "total_cost": round(float(row.total_cost or 0), 2),
        }
        for row in rows
    ]


def get_waste_summary(db: Session, tenant_id: str):
    findings = (
        db.query(WasteFinding)
        .filter(WasteFinding.tenant_id == tenant_id)
        .all()
    )

    active = [item for item in findings if item.status == "active"]
    dismissed = [item for item in findings if item.status == "dismissed"]
    resolved = [item for item in findings if item.status == "resolved"]

    total_saving = sum(item.estimated_monthly_saving or 0 for item in active)

    top_findings = sorted(
        active,
        key=lambda item: item.estimated_monthly_saving or 0,
        reverse=True,
    )[:5]

    return {
        "total_findings": len(findings),
        "active_findings": len(active),
        "dismissed_findings": len(dismissed),
        "resolved_findings": len(resolved),
        "estimated_monthly_saving": round(total_saving, 2),
        "top_findings": [
            {
                "id": item.id,
                "title": item.title,
                "severity": item.severity,
                "estimated_monthly_saving": item.estimated_monthly_saving,
            }
            for item in top_findings
        ],
    }


def get_anomaly_summary(db: Session, tenant_id: str):
    anomalies = (
        db.query(AnomalyFinding)
        .filter(AnomalyFinding.tenant_id == tenant_id)
        .all()
    )

    active = [item for item in anomalies if item.status == "active"]
    dismissed = [item for item in anomalies if item.status == "dismissed"]
    resolved = [item for item in anomalies if item.status == "resolved"]

    active_delta_cost = sum(item.delta_cost or 0 for item in active)

    top_anomalies = sorted(
        active,
        key=lambda item: item.delta_cost or 0,
        reverse=True,
    )[:5]

    return {
        "total_anomalies": len(anomalies),
        "active_anomalies": len(active),
        "dismissed_anomalies": len(dismissed),
        "resolved_anomalies": len(resolved),
        "active_delta_cost": round(active_delta_cost, 2),
        "top_anomalies": [
            {
                "id": item.id,
                "title": item.title,
                "anomaly_date": str(item.anomaly_date),
                "severity": item.severity,
                "delta_cost": item.delta_cost,
                "delta_percent": item.delta_percent,
            }
            for item in top_anomalies
        ],
    }


def get_forecast_summary(db: Session, tenant_id: str):
    latest_training_row = (
        db.query(func.max(CostForecast.training_end_date).label("latest_date"))
        .filter(CostForecast.tenant_id == tenant_id)
        .first()
    )

    latest_training_date = latest_training_row.latest_date if latest_training_row else None

    if not latest_training_date:
        return {
            "has_forecast": False,
            "message": "No forecast found. Please run /forecast/run first.",
        }

    forecasts = (
        db.query(CostForecast)
        .filter(CostForecast.tenant_id == tenant_id)
        .filter(CostForecast.training_end_date == latest_training_date)
        .order_by(CostForecast.forecast_date.asc())
        .all()
    )

    if not forecasts:
        return {
            "has_forecast": False,
            "message": "No forecast found. Please run /forecast/run first.",
        }

    total_forecasted_cost = sum(item.predicted_cost or 0 for item in forecasts)
    average_daily_forecast = total_forecasted_cost / len(forecasts)

    peak_forecast = max(forecasts, key=lambda item: item.predicted_cost or 0)

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    monthly_budget = tenant.monthly_budget if tenant else None

    if monthly_budget:
        budget_utilization_percent = (total_forecasted_cost / monthly_budget) * 100
        budget_gap = monthly_budget - total_forecasted_cost

        if total_forecasted_cost > monthly_budget:
            budget_status = "over_budget"
        elif budget_utilization_percent >= 80:
            budget_status = "at_risk"
        else:
            budget_status = "within_budget"
    else:
        budget_utilization_percent = None
        budget_gap = None
        budget_status = "budget_not_configured"

    return {
        "has_forecast": True,
        "forecast_days": len(forecasts),
        "forecast_start_date": str(forecasts[0].forecast_date),
        "forecast_end_date": str(forecasts[-1].forecast_date),
        "total_forecasted_cost": round(total_forecasted_cost, 2),
        "average_daily_forecast": round(average_daily_forecast, 2),
        "peak_forecast_date": str(peak_forecast.forecast_date),
        "peak_forecast_cost": round(peak_forecast.predicted_cost or 0, 2),
        "monthly_budget": monthly_budget,
        "budget_status": budget_status,
        "budget_gap": round(budget_gap, 2) if budget_gap is not None else None,
        "budget_utilization_percent": round(budget_utilization_percent, 2)
        if budget_utilization_percent is not None
        else None,
        "confidence_score": forecasts[0].confidence_score,
    }


def build_answer(intent: str, data: dict):
    if intent == "cost_summary":
        return (
            f"Your total cloud cost is ${data['total_cost']:.2f} "
            f"from {data['start_date']} to {data['end_date']}. "
            f"The analysis is based on {data['record_count']} cost records."
        )

    if intent == "top_services":
        services = data.get("top_services", [])

        if not services:
            return "No service-level cost data is available."

        lines = ["Your top cost services are:"]

        for index, service in enumerate(services, start=1):
            lines.append(
                f"{index}. {service['service_name']} - ${service['total_cost']:.2f}"
            )

        return "\n".join(lines)

    if intent == "waste_summary":
        return (
            f"You currently have {data['active_findings']} active waste findings. "
            f"The estimated monthly saving opportunity is ${data['estimated_monthly_saving']:.2f}. "
            f"There are {data['dismissed_findings']} dismissed findings and "
            f"{data['resolved_findings']} resolved findings."
        )

    if intent == "anomaly_summary":
        return (
            f"You currently have {data['active_anomalies']} active cost anomalies. "
            f"The active anomaly delta cost is ${data['active_delta_cost']:.2f}. "
            f"There are {data['dismissed_anomalies']} dismissed anomalies and "
            f"{data['resolved_anomalies']} resolved anomalies."
        )

    if intent == "forecast_summary":
        if not data.get("has_forecast"):
            return data["message"]

        return (
            f"Your forecasted cost for the next {data['forecast_days']} days is "
            f"${data['total_forecasted_cost']:.2f}. "
            f"The average daily forecast is ${data['average_daily_forecast']:.2f}. "
            f"The peak forecasted day is {data['peak_forecast_date']} "
            f"with ${data['peak_forecast_cost']:.2f}. "
            f"Forecast confidence is {data['confidence_score']}."
        )

    if intent == "budget_summary":
        if not data.get("has_forecast"):
            return data["message"]

        return (
            f"Your budget status is {data['budget_status']}. "
            f"Forecasted cost is ${data['total_forecasted_cost']:.2f}. "
            f"Monthly budget is ${data['monthly_budget']:.2f}. "
            f"Budget utilization is {data['budget_utilization_percent']:.2f}%."
        )

    if intent == "overall_summary":
        cost = data["cost"]
        waste = data["waste"]
        anomaly = data["anomaly"]
        forecast = data["forecast"]

        forecast_text = (
            f"Forecasted cost is ${forecast['total_forecasted_cost']:.2f}."
            if forecast.get("has_forecast")
            else "Forecast is not available yet."
        )

        return (
            f"Cloud cost overview: total historical cost is ${cost['total_cost']:.2f}. "
            f"There are {waste['active_findings']} active waste findings with "
            f"${waste['estimated_monthly_saving']:.2f} estimated monthly savings. "
            f"There are {anomaly['active_anomalies']} active cost anomalies. "
            f"{forecast_text}"
        )

    return "I could not understand the question clearly, so I generated a general cloud cost summary."


def ask_chatbot(db: Session, tenant_id: str, question: str):
    intent = detect_intent(question)

    if intent == "cost_summary":
        data = get_cost_summary(db=db, tenant_id=tenant_id)

    elif intent == "top_services":
        data = {
            "top_services": get_top_services(db=db, tenant_id=tenant_id)
        }

    elif intent == "waste_summary":
        data = get_waste_summary(db=db, tenant_id=tenant_id)

    elif intent == "anomaly_summary":
        data = get_anomaly_summary(db=db, tenant_id=tenant_id)

    elif intent == "forecast_summary":
        data = get_forecast_summary(db=db, tenant_id=tenant_id)

    elif intent == "budget_summary":
        data = get_forecast_summary(db=db, tenant_id=tenant_id)

    else:
        data = {
            "cost": get_cost_summary(db=db, tenant_id=tenant_id),
            "top_services": get_top_services(db=db, tenant_id=tenant_id),
            "waste": get_waste_summary(db=db, tenant_id=tenant_id),
            "anomaly": get_anomaly_summary(db=db, tenant_id=tenant_id),
            "forecast": get_forecast_summary(db=db, tenant_id=tenant_id),
        }

    answer = build_answer(intent=intent, data=data)

    chat_message = ChatMessage(
        tenant_id=tenant_id,
        question=question,
        answer=answer,
        intent=intent,
        data=data,
    )

    db.add(chat_message)
    db.commit()
    db.refresh(chat_message)

    return {
        "id": chat_message.id,
        "tenant_id": tenant_id,
        "question": question,
        "intent": intent,
        "answer": answer,
        "data": data,
        "suggested_questions": [
            "What is my total cloud cost?",
            "Which services are costing the most?",
            "How much waste saving is available?",
            "Show me active anomalies.",
            "What is my forecasted cost?",
            "Am I over budget?",
        ],
    }