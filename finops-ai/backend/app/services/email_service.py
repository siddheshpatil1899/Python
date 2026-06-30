import smtplib
from email.message import EmailMessage

from app.core.config import settings


def is_email_configured():
    return bool(
        settings.SMTP_HOST
        and settings.SMTP_USERNAME
        and settings.SMTP_PASSWORD
        and settings.SMTP_FROM_EMAIL
    )


def send_email(to_email: str, subject: str, body: str):
    if not is_email_configured():
        print("Email not sent because SMTP is not configured.")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(body)
        return False

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

        return True

    except Exception as error:
        print(f"Email sending failed: {error}")
        return False


def send_signup_notification_to_admin(
    full_name: str,
    email: str,
    requested_role: str,
):
    subject = "New FinOps AI access request"

    body = f"""
A new user has requested access to FinOps AI.

Name: {full_name}
Email: {email}
Requested Role: {requested_role}

The user has been created as inactive.
Please log in as admin and activate/update access from the Settings page.
"""

    return send_email(
        to_email=settings.SMTP_ADMIN_EMAIL,
        subject=subject,
        body=body,
    )


def send_user_created_email(
    full_name: str,
    email: str,
    password: str,
    role: str,
):
    subject = "Your FinOps AI account has been created"

    body = f"""
Hello {full_name},

Your FinOps AI account has been created.

Login URL: http://localhost:5173/
Email: {email}
Temporary Password: {password}
Role: {role}

Regards,
FinOps AI
"""

    return send_email(
        to_email=email,
        subject=subject,
        body=body,
    )


def send_password_reset_email(
    full_name: str,
    email: str,
    reset_link: str,
):
    subject = "Reset your FinOps AI password"

    body = f"""
Hello {full_name},

We received a request to reset your FinOps AI password.

Reset your password using this link:

{reset_link}

This link will expire in 30 minutes.

If you did not request this, please ignore this email.

Regards,
FinOps AI
"""

    return send_email(
        to_email=email,
        subject=subject,
        body=body,
    )