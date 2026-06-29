import json
from datetime import datetime

import pandas as pd

from app.core.database import SessionLocal, Base, engine
from app.models.cost_record import CostRecord


CSV_PATH = "app/seed/dummy_cost_data.csv"


def safe_json_loads(value):
    """
    Convert CSV tag text into a Python dictionary.

    Example:
    {"team":"engineering","env":"prod"}
    """

    if pd.isna(value):
        return None

    if isinstance(value, dict):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def safe_float(value):
    """
    Convert empty or invalid numeric values into None.
    """

    if pd.isna(value):
        return None

    return float(value)


def seed_cost_records():
    """
    Load dummy cloud cost data from CSV and insert it into the database.

    During development, this script first deletes old records.
    This avoids duplicate rows when you run the seed command multiple times.
    """

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        df = pd.read_csv(CSV_PATH)

        db.query(CostRecord).delete()
        db.commit()

        records = []

        for _, row in df.iterrows():
            record = CostRecord(
                tenant_id=row["tenant_id"],
                cloud_provider=row["cloud_provider"],
                account_id=row["account_id"],
                service_name=row["service_name"],
                region=row.get("region"),
                usage_date=datetime.strptime(row["usage_date"], "%Y-%m-%d").date(),
                usage_quantity=safe_float(row.get("usage_quantity")),
                usage_unit=row.get("usage_unit"),
                billed_cost=safe_float(row.get("billed_cost")),
                effective_cost=safe_float(row.get("effective_cost")),
                currency=row.get("currency", "USD"),
                resource_id=row.get("resource_id"),
                tags=safe_json_loads(row.get("tags")),
            )

            records.append(record)

        db.add_all(records)
        db.commit()

        print(f"Inserted {len(records)} dummy cost records successfully.")

    except Exception as error:
        db.rollback()
        print(f"Error while seeding dummy data: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_cost_records()