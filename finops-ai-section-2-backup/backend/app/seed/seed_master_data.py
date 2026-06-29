import json

import pandas as pd

from app.core.database import Base, engine, SessionLocal
from app.models.tenant import Tenant
from app.models.cloud_account import CloudAccount
from app.models.cloud_resource import CloudResource
from app.models.resource_metric import ResourceMetric
from app.models.pricing import Pricing


TENANTS_CSV = "app/seed/tenants.csv"
CLOUD_ACCOUNTS_CSV = "app/seed/cloud_accounts.csv"
RESOURCES_CSV = "app/seed/resources.csv"
RESOURCE_METRICS_CSV = "app/seed/resource_metrics.csv"
PRICING_CSV = "app/seed/pricing.csv"


def clean_value(value):
    if pd.isna(value):
        return None
    return value


def parse_datetime(value):
    if pd.isna(value):
        return None
    return pd.to_datetime(value).to_pydatetime()


def parse_date(value):
    if pd.isna(value):
        return None
    return pd.to_datetime(value).date()


def parse_json(value):
    if pd.isna(value):
        return None

    try:
        return json.loads(value)
    except Exception:
        return None


def parse_bool(value):
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    return str(value).lower() in ["true", "1", "yes"]


def seed_tenants(db):
    df = pd.read_csv(TENANTS_CSV)

    db.query(Tenant).delete()

    for _, row in df.iterrows():
        tenant = Tenant(
            id=row["id"],
            name=row["name"],
            plan_tier=clean_value(row.get("plan_tier")),
            monthly_budget=clean_value(row.get("monthly_budget")),
            created_at=parse_datetime(row.get("created_at")),
        )
        db.add(tenant)


def seed_cloud_accounts(db):
    df = pd.read_csv(CLOUD_ACCOUNTS_CSV)

    db.query(CloudAccount).delete()

    for _, row in df.iterrows():
        account = CloudAccount(
            id=row["id"],
            tenant_id=row["tenant_id"],
            provider=row["provider"],
            account_id=str(row["account_id"]),
            role_arn=clean_value(row.get("role_arn")),
            external_id=clean_value(row.get("external_id")),
            auth_metadata=parse_json(row.get("auth_metadata")),
            last_synced_at=parse_datetime(row.get("last_synced_at")),
            consecutive_failures=int(row.get("consecutive_failures", 0)),
            last_error=clean_value(row.get("last_error")),
            needs_reauth=parse_bool(row.get("needs_reauth")),
        )
        db.add(account)


def seed_resources(db):
    df = pd.read_csv(RESOURCES_CSV)

    db.query(CloudResource).delete()

    for _, row in df.iterrows():
        resource = CloudResource(
            resource_id=row["resource_id"],
            resource_type=row["resource_type"],
            instance_type=clean_value(row.get("instance_type")),
            volume_type=clean_value(row.get("volume_type")),
            lb_type=clean_value(row.get("lb_type")),
            size_gb=clean_value(row.get("size_gb")),
            state=clean_value(row.get("state")),
            state_changed_at=parse_datetime(row.get("state_changed_at")),
            healthy_target_count=clean_value(row.get("healthy_target_count")),
            tenant_id=row["tenant_id"],
            account_id=str(row["account_id"]),
            region=clean_value(row.get("region")),
            refreshed_at=parse_datetime(row.get("refreshed_at")),
        )
        db.add(resource)


def seed_resource_metrics(db):
    df = pd.read_csv(RESOURCE_METRICS_CSV)

    db.query(ResourceMetric).delete()

    for _, row in df.iterrows():
        metric = ResourceMetric(
            tenant_id=row["tenant_id"],
            resource_id=row["resource_id"],
            metric_name=row["metric_name"],
            metric_date=parse_date(row["metric_date"]),
            value=float(row["value"]),
        )
        db.add(metric)


def seed_pricing(db):
    df = pd.read_csv(PRICING_CSV)

    db.query(Pricing).delete()

    for _, row in df.iterrows():
        pricing = Pricing(
            provider=row["provider"],
            sku=row["sku"],
            region=row["region"],
            hourly_rate=clean_value(row.get("hourly_rate")),
            price_per_gb_month=clean_value(row.get("price_per_gb_month")),
            monthly_base_rate=clean_value(row.get("monthly_base_rate")),
            updated_at=parse_datetime(row.get("updated_at")),
        )
        db.add(pricing)


def seed_master_data():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        seed_tenants(db)
        seed_cloud_accounts(db)
        seed_resources(db)
        seed_resource_metrics(db)
        seed_pricing(db)

        db.commit()

        print("Master dummy data inserted successfully.")
        print("Inserted tenants, cloud accounts, resources, metrics, and pricing.")

    except Exception as error:
        db.rollback()
        print(f"Error while seeding master data: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_master_data()