from app.core.database import SessionLocal
from app.models.user import User


USER_EMAIL = "rushikesh.c@seamlessautomations.com"


def activate_user():
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == USER_EMAIL).first()

        if not user:
            print(f"User not found: {USER_EMAIL}")
            return

        user.is_active = True
        user.role = "analyst"
        user.allowed_modules = [
            "dashboard",
            "cost",
            "waste",
            "anomaly",
            "forecast",
            "warehouse",
            "chatbot",
        ]

        db.commit()

        print("User activated successfully.")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Active: {user.is_active}")
        print(f"Allowed modules: {user.allowed_modules}")

    finally:
        db.close()


if __name__ == "__main__":
    activate_user()