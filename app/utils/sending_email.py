from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from dotenv import load_dotenv
import os

load_dotenv()

# SMTP configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("EMAIL_USER"),
    MAIL_PASSWORD=os.getenv("EMAIL_PASSWORD"),
    MAIL_FROM=os.getenv("EMAIL_USER"),
    MAIL_PORT=int(os.getenv("EMAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("EMAIL_HOST"),
    MAIL_TLS=os.getenv("EMAIL_USE_SSL", "False").lower() != "true",
    MAIL_SSL=os.getenv("EMAIL_USE_SSL", "False").lower() == "true",
    MAIL_FROM_NAME="accordion.jakub-kuba.com"
)


async def send_confirmation_email(email: EmailStr, confirmation_link: str):
    message = MessageSchema(
        subject="Registration confirmation",
        recipients=[email],
        html=(
            "Thank you for registering in my application! "
            "Please confirm your registration by clicking the following link: "
            f"<a href='{confirmation_link}'>Confirm Registration</a>. "
            "If you do not confirm your email within one hour, "
            "your account will be deleted."
        ),
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
