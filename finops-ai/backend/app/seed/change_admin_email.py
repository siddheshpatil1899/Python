from app.core.database import SessionLocal
from app.models.user import User


OLD_ADMIN_EMAIL = "admin@finops.ai"
NEW_ADMIN_EMAIL = "siddhesh.p@seamlessautomation.com"


def change_admin_email():
    db = SessionLocal()

    try:
        admin = db.query(User).filter(User.email == OLD_ADMIN_EMAIL).first()

        if not admin:
            print(f"Admin user not found with email: {OLD_ADMIN_EMAIL}")
            return

        existing = db.query(User).filter(User.email == NEW_ADMIN_EMAIL).first()

        if existing:
            print(f"Another user already exists with email: {NEW_ADMIN_EMAIL}")
            return

        admin.email = NEW_ADMIN_EMAIL
        db.commit()

        print("Admin email updated successfully.")
        print(f"Old email: {OLD_ADMIN_EMAIL}")
        print(f"New email: {NEW_ADMIN_EMAIL}")

    finally:
        db.close()


if __name__ == "__main__":
    change_admin_email()