from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.app_setting import AppSetting


ADMIN_EMAIL = "admin@finops.ai"
ADMIN_PASSWORD = "Admin@123"
TENANT_ID = "11111111-1111-1111-1111-111111111111"


def seed_admin_user():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()

        if existing:
            print("Admin user already exists.")
            return

        admin = User(
            email=ADMIN_EMAIL,
            full_name="FinOps Admin",
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
            allowed_modules=[
                "dashboard",
                "cost",
                "waste",
                "anomaly",
                "forecast",
                "warehouse",
                "chatbot",
                "settings",
            ],
        )

        db.add(admin)

        setting = AppSetting(
            tenant_id=TENANT_ID,
            data_fetch_mode="manual",
            fetch_frequency="daily",
            fetch_time="02:00",
            enabled_modules=[
                "cost",
                "waste",
                "anomaly",
                "forecast",
                "warehouse",
            ],
            notify_emails=[ADMIN_EMAIL],
        )

        db.add(setting)
        db.commit()

        print("Admin user created successfully.")
        print(f"Email: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_user()