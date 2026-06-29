from pathlib import Path

PROJECT_NAME = "finops-ai"

folders = [
    "backend/app/core",
    "backend/app/models",
    "backend/app/schemas",
    "backend/app/services",
    "backend/app/api",
    "backend/app/seed",
    "backend/alembic",
    "frontend",
]

files = [
    "backend/app/__init__.py",
    "backend/app/main.py",

    "backend/app/core/__init__.py",
    "backend/app/core/config.py",
    "backend/app/core/database.py",
    "backend/app/core/security.py",

    "backend/app/models/__init__.py",
    "backend/app/models/organization.py",
    "backend/app/models/user.py",
    "backend/app/models/cloud_account.py",
    "backend/app/models/cost_record.py",
    "backend/app/models/waste_finding.py",
    "backend/app/models/anomaly.py",
    "backend/app/models/forecast.py",

    "backend/app/schemas/__init__.py",
    "backend/app/schemas/cost_record_schema.py",
    "backend/app/schemas/waste_schema.py",
    "backend/app/schemas/anomaly_schema.py",
    "backend/app/schemas/forecast_schema.py",

    "backend/app/services/__init__.py",
    "backend/app/services/cost_service.py",
    "backend/app/services/waste_rule_engine.py",
    "backend/app/services/anomaly_engine.py",
    "backend/app/services/forecast_engine.py",
    "backend/app/services/chatbot_engine.py",

    "backend/app/api/__init__.py",
    "backend/app/api/routes_cost.py",
    "backend/app/api/routes_waste.py",
    "backend/app/api/routes_anomaly.py",
    "backend/app/api/routes_forecast.py",
    "backend/app/api/routes_chat.py",

    "backend/app/seed/__init__.py",
    "backend/app/seed/seed_dummy_data.py",
    "backend/app/seed/dummy_cost_data.csv",

    "backend/requirements.txt",
    "backend/Dockerfile",
    "backend/.env",

    "docker-compose.yml",
    "README.md",
]

starter_content = {
    "README.md": "# FinOps AI\n\nAI-powered cloud cost optimization platform.\n",

    "backend/.env": """DATABASE_URL=postgresql://finops_user:finops_password@localhost:5432/finops_ai
APP_NAME=FinOps AI
ENVIRONMENT=development
JWT_SECRET_KEY=change-this-secret-later
""",

    "backend/requirements.txt": """fastapi
uvicorn
sqlalchemy
psycopg2-binary
alembic
pandas
python-dotenv
pydantic
""",

    "docker-compose.yml": """version: "3.9"

services:
  postgres:
    image: postgres:16
    container_name: finops_postgres
    restart: always
    environment:
      POSTGRES_USER: finops_user
      POSTGRES_PASSWORD: finops_password
      POSTGRES_DB: finops_ai
    ports:
      - "5432:5432"
    volumes:
      - finops_postgres_data:/var/lib/postgresql/data

volumes:
  finops_postgres_data:
""",

    "backend/Dockerfile": """FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",

    "backend/app/main.py": """from fastapi import FastAPI

app = FastAPI(title="FinOps AI")


@app.get("/")
def root():
    return {"message": "FinOps AI backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
""",

    "backend/app/seed/dummy_cost_data.csv": """tenant_id,cloud_provider,account_id,service_name,region,usage_date,usage_quantity,usage_unit,billed_cost,effective_cost,currency,resource_id,tags
tenant_001,AWS,aws-prod-001,EC2,us-east-1,2026-01-01,120,hours,45.50,45.50,USD,i-001,"{""team"":""engineering"",""env"":""prod""}"
tenant_001,AWS,aws-prod-001,S3,us-east-1,2026-01-01,500,GB,12.25,12.25,USD,bucket-logs,"{""team"":""data"",""env"":""prod""}"
"""
}


def create_project_structure():
    root = Path(PROJECT_NAME)

    for folder in folders:
        folder_path = root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {folder_path}")

    for file in files:
        file_path = root / file
        file_path.parent.mkdir(parents=True, exist_ok=True)

        content = starter_content.get(file, "")

        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")
            print(f"Created file: {file_path}")
        else:
            print(f"Already exists: {file_path}")

    print("\nProject structure created successfully.")
    print(f"Open folder: {root.resolve()}") 

if __name__ == "__main__":
    create_project_structure()