from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.app_setting import AppSetting

try:
    from app.models.password_reset import PasswordResetToken
except Exception:
    PasswordResetToken = None


ADMIN_EMAIL = "siddhesh.p@seamlessautomations.com"
ADMIN_PASSWORD = "Admin@123"
TENANT_ID = "11111111-1111-1111-1111-111111111111"


def reset_admin_user():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()

        if not admin:
            old_admin = db.query(User).filter(User.email == "admin@finops.ai").first()

            if old_admin:
                admin = old_admin
                admin.email = ADMIN_EMAIL
            else:
                admin = db.query(User).filter(User.role == "admin").first()

                if admin:
                    admin.email = ADMIN_EMAIL
                else:
                    admin = User(
                        email=ADMIN_EMAIL,
                        full_name="FinOps Admin",
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

        admin.full_name = "FinOps Admin"
        admin.password_hash = hash_password(ADMIN_PASSWORD)
        admin.role = "admin"
        admin.is_active = True
        admin.allowed_modules = [
            "dashboard",
            "cost",
            "waste",
            "anomaly",
            "forecast",
            "warehouse",
            "chatbot",
            "settings",
        ]

        setting = (
            db.query(AppSetting)
            .filter(AppSetting.tenant_id == TENANT_ID)
            .first()
        )

        if not setting:
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
        else:
            setting.notify_emails = [ADMIN_EMAIL]

        db.commit()

        print("Admin user reset successfully.")
        print(f"Email: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")
        print("Role: admin")
        print("Active: True")

    finally:
        db.close()


if __name__ == "__main__":
    reset_admin_user()