import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "FinOps AI")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    API_V1_PREFIX = "/api/v1"

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finops_ai.db")

    BACKEND_CORS_ORIGINS = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )

    @property
    def cors_origins(self):
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()