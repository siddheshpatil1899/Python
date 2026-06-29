import csv
import json
from pathlib import Path


INPUT_FILE = Path("app/seed/cost_data.csv")
OUTPUT_FILE = Path("app/seed/dummy_cost_data.csv")


OUTPUT_COLUMNS = [
    "tenant_id",
    "cloud_provider",
    "account_id",
    "service_name",
    "region",
    "usage_date",
    "usage_quantity",
    "usage_unit",
    "billed_cost",
    "effective_cost",
    "currency",
    "resource_id",
    "tags",
]


def build_resource_id(row):
    """
    Creates a dummy resource_id because the uploaded CSV does not have resource-level IDs.
    This helps later for waste findings and recommendations.
    """

    provider = row.get("provider", "").lower()
    account_id = row.get("account_id", "")
    service_name = row.get("service_name", "").replace(" ", "_").lower()
    region = row.get("region", "")
    usage_date = row.get("usage_date", "")

    return f"{provider}-{account_id}-{service_name}-{region}-{usage_date}"


def convert_cost_data():
    with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        rows = list(reader)

    converted_rows = []

    for row in rows:
        tags = {
            "source": "dummy_data",
            "usage_type": row.get("usage_type", "unknown")
        }

        converted_row = {
            "tenant_id": row.get("tenant_id"),
            "cloud_provider": row.get("provider", "").upper(),
            "account_id": row.get("account_id"),
            "service_name": row.get("service_name"),
            "region": row.get("region"),
            "usage_date": row.get("usage_date"),
            "usage_quantity": row.get("usage_quantity"),
            "usage_unit": row.get("usage_unit"),
            "billed_cost": row.get("billed_cost"),
            "effective_cost": row.get("billed_cost"),
            "currency": row.get("currency", "USD"),
            "resource_id": build_resource_id(row),
            "tags": json.dumps(tags),
        }

        converted_rows.append(converted_row)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(converted_rows)

    print(f"Converted {len(converted_rows)} rows.")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    convert_cost_data()