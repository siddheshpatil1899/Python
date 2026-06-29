import hashlib
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.waste_finding import WasteFinding
from app.models.cloud_resource import CloudResource
from app.models.resource_metric import ResourceMetric
from app.models.pricing import Pricing
from app.models.cloud_account import CloudAccount


MONTHLY_HOURS = 730

IDLE_EC2_CPU_THRESHOLD = 5.0
OVERSIZED_EC2_CPU_THRESHOLD = 20.0
RDS_CONNECTION_THRESHOLD = 1.0
LB_REQUEST_THRESHOLD = 1.0


def generate_finding_key(
    tenant_id,
    rule_id,
    account_id,
    service_name,
    region,
    resource_id,
):
    raw_key = "|".join(
        [
            tenant_id or "",
            rule_id or "",
            account_id or "",
            service_name or "",
            region or "",
            resource_id or "",
        ]
    )

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def calculate_severity(monthly_saving):
    if monthly_saving >= 1000:
        return "critical"

    if monthly_saving >= 500:
        return "high"

    if monthly_saving >= 100:
        return "medium"

    return "low"


def clamp_confidence(value):
    return max(0.0, min(1.0, round(value, 2)))


def get_provider_for_account(db, tenant_id, account_id):
    account = (
        db.query(CloudAccount)
        .filter(CloudAccount.tenant_id == tenant_id)
        .filter(CloudAccount.account_id == str(account_id))
        .first()
    )

    if account:
        return account.provider.lower()

    return "aws"


def get_average_metric(db, tenant_id, resource_id, metric_name):
    row = (
        db.query(
            func.avg(ResourceMetric.value).label("avg_value"),
            func.count(ResourceMetric.id).label("sample_count"),
        )
        .filter(ResourceMetric.tenant_id == tenant_id)
        .filter(ResourceMetric.resource_id == resource_id)
        .filter(ResourceMetric.metric_name == metric_name)
        .first()
    )

    avg_value = float(row.avg_value or 0)
    sample_count = int(row.sample_count or 0)

    return avg_value, sample_count


def get_pricing(db, provider, sku, region):
    return (
        db.query(Pricing)
        .filter(Pricing.provider == provider.lower())
        .filter(Pricing.sku == sku)
        .filter(Pricing.region == region)
        .first()
    )


def calculate_hourly_monthly_cost(db, provider, sku, region):
    pricing = get_pricing(db, provider, sku, region)

    if not pricing or pricing.hourly_rate is None:
        return 0.0

    return float(pricing.hourly_rate) * MONTHLY_HOURS


def calculate_storage_monthly_cost(db, provider, volume_type, region, size_gb):
    pricing = get_pricing(db, provider, volume_type, region)

    if not pricing or pricing.price_per_gb_month is None:
        return 0.0

    return float(pricing.price_per_gb_month) * float(size_gb or 0)


def calculate_lb_monthly_cost(db, provider, lb_type, region):
    pricing = get_pricing(db, provider, lb_type, region)

    if not pricing or pricing.monthly_base_rate is None:
        return 0.0

    return float(pricing.monthly_base_rate)


def build_finding(
    tenant_id,
    cloud_provider,
    account_id,
    rule_id,
    rule_name,
    service_name,
    region,
    resource_id,
    monthly_cost,
    estimated_monthly_saving,
    confidence_score,
    title,
    explanation,
    recommendation,
    evidence,
):
    finding_key = generate_finding_key(
        tenant_id=tenant_id,
        rule_id=rule_id,
        account_id=account_id,
        service_name=service_name,
        region=region,
        resource_id=resource_id,
    )

    return {
        "finding_key": finding_key,
        "tenant_id": tenant_id,
        "cloud_provider": cloud_provider.upper(),
        "account_id": str(account_id),
        "rule_id": rule_id,
        "rule_name": rule_name,
        "service_name": service_name,
        "region": region,
        "resource_id": resource_id,
        "severity": calculate_severity(estimated_monthly_saving),
        "status": "active",
        "confidence_score": clamp_confidence(confidence_score),
        "estimated_monthly_saving": round(estimated_monthly_saving, 2),
        "current_monthly_cost": round(monthly_cost, 2),
        "title": title,
        "explanation": explanation,
        "recommendation": recommendation,
        "evidence": evidence,
    }


def upsert_finding(db, finding_data):
    existing_finding = (
        db.query(WasteFinding)
        .filter(WasteFinding.finding_key == finding_data["finding_key"])
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing_finding:
        existing_finding.last_seen_at = now
        existing_finding.evidence = finding_data.get("evidence")

        if existing_finding.status != "dismissed":
            existing_finding.status = "active"
            existing_finding.resolved_at = None
            existing_finding.confidence_score = finding_data["confidence_score"]
            existing_finding.estimated_monthly_saving = finding_data["estimated_monthly_saving"]
            existing_finding.current_monthly_cost = finding_data["current_monthly_cost"]
            existing_finding.severity = finding_data["severity"]
            existing_finding.title = finding_data["title"]
            existing_finding.explanation = finding_data["explanation"]
            existing_finding.recommendation = finding_data["recommendation"]

        return existing_finding

    new_finding = WasteFinding(**finding_data)
    db.add(new_finding)

    return new_finding


def rule_idle_ec2_instances(db, tenant_id):
    findings = []

    resources = (
        db.query(CloudResource)
        .filter(CloudResource.tenant_id == tenant_id)
        .filter(CloudResource.resource_type == "ec2_instance")
        .filter(CloudResource.state == "running")
        .all()
    )

    for resource in resources:
        avg_cpu, sample_count = get_average_metric(
            db=db,
            tenant_id=tenant_id,
            resource_id=resource.resource_id,
            metric_name="CPUUtilization",
        )

        if sample_count < 7:
            continue

        if avg_cpu >= IDLE_EC2_CPU_THRESHOLD:
            continue

        provider = get_provider_for_account(db, tenant_id, resource.account_id)

        monthly_cost = calculate_hourly_monthly_cost(
            db=db,
            provider=provider,
            sku=resource.instance_type,
            region=resource.region,
        )

        estimated_saving = monthly_cost * 0.90

        findings.append(
            build_finding(
                tenant_id=tenant_id,
                cloud_provider=provider,
                account_id=resource.account_id,
                rule_id="idle_ec2_instance",
                rule_name="Idle EC2 instance",
                service_name="EC2",
                region=resource.region,
                resource_id=resource.resource_id,
                monthly_cost=monthly_cost,
                estimated_monthly_saving=estimated_saving,
                confidence_score=0.95 if avg_cpu < 3 else 0.85,
                title=f"Idle EC2 instance detected: {resource.resource_id}",
                explanation=(
                    f"This EC2 instance has average CPU utilization of {avg_cpu:.2f}% "
                    f"across {sample_count} samples."
                ),
                recommendation=(
                    "Verify whether the instance is needed. If not, stop it, terminate it, "
                    "or apply a schedule so it only runs during business hours."
                ),
                evidence={
                    "avg_cpu_percent": round(avg_cpu, 2),
                    "sample_count": sample_count,
                    "cpu_threshold": IDLE_EC2_CPU_THRESHOLD,
                    "instance_type": resource.instance_type,
                },
            )
        )

    return findings


def rule_oversized_ec2_instances(db, tenant_id):
    findings = []

    downsizing_map = {
        "m5.2xlarge": "m5.xlarge",
        "m5.xlarge": "m5.large",
    }

    resources = (
        db.query(CloudResource)
        .filter(CloudResource.tenant_id == tenant_id)
        .filter(CloudResource.resource_type == "ec2_instance")
        .filter(CloudResource.state == "running")
        .all()
    )

    for resource in resources:
        if resource.instance_type not in downsizing_map:
            continue

        avg_cpu, sample_count = get_average_metric(
            db=db,
            tenant_id=tenant_id,
            resource_id=resource.resource_id,
            metric_name="CPUUtilization",
        )

        if sample_count < 7:
            continue

        if avg_cpu < IDLE_EC2_CPU_THRESHOLD:
            continue

        if avg_cpu >= OVERSIZED_EC2_CPU_THRESHOLD:
            continue

        provider = get_provider_for_account(db, tenant_id, resource.account_id)

        current_monthly_cost = calculate_hourly_monthly_cost(
            db=db,
            provider=provider,
            sku=resource.instance_type,
            region=resource.region,
        )

        recommended_instance_type = downsizing_map[resource.instance_type]

        recommended_monthly_cost = calculate_hourly_monthly_cost(
            db=db,
            provider=provider,
            sku=recommended_instance_type,
            region=resource.region,
        )

        estimated_saving = max(current_monthly_cost - recommended_monthly_cost, 0)

        if estimated_saving <= 0:
            continue

        findings.append(
            build_finding(
                tenant_id=tenant_id,
                cloud_provider=provider,
                account_id=resource.account_id,
                rule_id="oversized_ec2_instance",
                rule_name="Oversized EC2 instance",
                service_name="EC2",
                region=resource.region,
                resource_id=resource.resource_id,
                monthly_cost=current_monthly_cost,
                estimated_monthly_saving=estimated_saving,
                confidence_score=0.80,
                title=f"Oversized EC2 instance detected: {resource.resource_id}",
                explanation=(
                    f"This instance averages {avg_cpu:.2f}% CPU. "
                    "It may be oversized for its workload."
                ),
                recommendation=(
                    f"Review workload requirements and consider downsizing from "
                    f"{resource.instance_type} to {recommended_instance_type}."
                ),
                evidence={
                    "avg_cpu_percent": round(avg_cpu, 2),
                    "sample_count": sample_count,
                    "current_instance_type": resource.instance_type,
                    "recommended_instance_type": recommended_instance_type,
                    "current_monthly_cost": round(current_monthly_cost, 2),
                    "recommended_monthly_cost": round(recommended_monthly_cost, 2),
                },
            )
        )

    return findings


def rule_unattached_ebs_volumes(db, tenant_id):
    findings = []

    resources = (
        db.query(CloudResource)
        .filter(CloudResource.tenant_id == tenant_id)
        .filter(CloudResource.resource_type == "ebs_volume")
        .filter(CloudResource.state == "available")
        .all()
    )

    for resource in resources:
        provider = get_provider_for_account(db, tenant_id, resource.account_id)

        monthly_cost = calculate_storage_monthly_cost(
            db=db,
            provider=provider,
            volume_type=resource.volume_type,
            region=resource.region,
            size_gb=resource.size_gb or 0,
        )

        findings.append(
            build_finding(
                tenant_id=tenant_id,
                cloud_provider=provider,
                account_id=resource.account_id,
                rule_id="unattached_ebs_volume",
                rule_name="Unattached EBS volume",
                service_name="EBS",
                region=resource.region,
                resource_id=resource.resource_id,
                monthly_cost=monthly_cost,
                estimated_monthly_saving=monthly_cost,
                confidence_score=0.92,
                title=f"Unattached EBS volume detected: {resource.resource_id}",
                explanation=(
                    "This EBS volume is in available state and is not attached to a running instance."
                ),
                recommendation=(
                    "Confirm that the volume is not needed. If safe, snapshot it and delete the volume."
                ),
                evidence={
                    "state": resource.state,
                    "volume_type": resource.volume_type,
                    "size_gb": resource.size_gb,
                },
            )
        )

    return findings


def rule_zombie_load_balancers(db, tenant_id):
    findings = []

    resources = (
        db.query(CloudResource)
        .filter(CloudResource.tenant_id == tenant_id)
        .filter(CloudResource.resource_type == "load_balancer")
        .all()
    )

    for resource in resources:
        avg_requests, sample_count = get_average_metric(
            db=db,
            tenant_id=tenant_id,
            resource_id=resource.resource_id,
            metric_name="RequestCount",
        )

        has_no_targets = float(resource.healthy_target_count or 0) == 0
        has_no_requests = sample_count >= 7 and avg_requests < LB_REQUEST_THRESHOLD

        if not has_no_targets and not has_no_requests:
            continue

        provider = get_provider_for_account(db, tenant_id, resource.account_id)

        monthly_cost = calculate_lb_monthly_cost(
            db=db,
            provider=provider,
            lb_type=resource.lb_type,
            region=resource.region,
        )

        findings.append(
            build_finding(
                tenant_id=tenant_id,
                cloud_provider=provider,
                account_id=resource.account_id,
                rule_id="zombie_load_balancer",
                rule_name="Zombie load balancer",
                service_name="Load Balancer",
                region=resource.region,
                resource_id=resource.resource_id,
                monthly_cost=monthly_cost,
                estimated_monthly_saving=monthly_cost,
                confidence_score=0.94 if has_no_targets else 0.82,
                title=f"Unused load balancer detected: {resource.resource_id}",
                explanation=(
                    "This load balancer appears unused because it has no healthy targets "
                    "or almost no request traffic."
                ),
                recommendation=(
                    "Check whether any application still depends on this load balancer. "
                    "If not, delete it to avoid monthly base charges."
                ),
                evidence={
                    "healthy_target_count": resource.healthy_target_count,
                    "avg_request_count": round(avg_requests, 2),
                    "sample_count": sample_count,
                    "lb_type": resource.lb_type,
                },
            )
        )

    return findings


def rule_idle_rds_instances(db, tenant_id):
    findings = []

    resources = (
        db.query(CloudResource)
        .filter(CloudResource.tenant_id == tenant_id)
        .filter(CloudResource.resource_type == "rds_instance")
        .all()
    )

    for resource in resources:
        avg_connections, sample_count = get_average_metric(
            db=db,
            tenant_id=tenant_id,
            resource_id=resource.resource_id,
            metric_name="DatabaseConnections",
        )

        if sample_count < 7:
            continue

        if avg_connections >= RDS_CONNECTION_THRESHOLD:
            continue

        provider = get_provider_for_account(db, tenant_id, resource.account_id)

        monthly_cost = calculate_hourly_monthly_cost(
            db=db,
            provider=provider,
            sku=resource.instance_type,
            region=resource.region,
        )

        estimated_saving = monthly_cost * 0.70

        findings.append(
            build_finding(
                tenant_id=tenant_id,
                cloud_provider=provider,
                account_id=resource.account_id,
                rule_id="idle_rds_instance",
                rule_name="Idle RDS instance",
                service_name="RDS",
                region=resource.region,
                resource_id=resource.resource_id,
                monthly_cost=monthly_cost,
                estimated_monthly_saving=estimated_saving,
                confidence_score=0.88,
                title=f"Idle RDS instance detected: {resource.resource_id}",
                explanation=(
                    f"This RDS instance has average database connections of "
                    f"{avg_connections:.2f} across {sample_count} samples."
                ),
                recommendation=(
                    "Confirm whether the database is still required. If not, snapshot it and delete it. "
                    "If it is used only sometimes, consider scheduling or downsizing."
                ),
                evidence={
                    "avg_database_connections": round(avg_connections, 2),
                    "sample_count": sample_count,
                    "connection_threshold": RDS_CONNECTION_THRESHOLD,
                    "instance_type": resource.instance_type,
                },
            )
        )

    return findings


def run_waste_scan(db, tenant_id):
    rule_functions = [
        rule_idle_ec2_instances,
        rule_oversized_ec2_instances,
        rule_unattached_ebs_volumes,
        rule_zombie_load_balancers,
        rule_idle_rds_instances,
    ]

    all_findings = []

    for rule_function in rule_functions:
        findings = rule_function(db, tenant_id)
        all_findings.extend(findings)

    seen_keys = set()

    for finding_data in all_findings:
        seen_keys.add(finding_data["finding_key"])
        upsert_finding(db, finding_data)

    active_findings = (
        db.query(WasteFinding)
        .filter(WasteFinding.tenant_id == tenant_id)
        .filter(WasteFinding.status == "active")
        .all()
    )

    now = datetime.now(timezone.utc)

    for finding in active_findings:
        if finding.finding_key not in seen_keys:
            finding.status = "resolved"
            finding.resolved_at = now

    db.commit()

    return {
        "tenant_id": tenant_id,
        "rules_executed": len(rule_functions),
        "findings_detected": len(all_findings),
        "message": "Resource-based waste scan completed successfully",
    }