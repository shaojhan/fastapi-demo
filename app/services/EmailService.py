from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from app.config import get_settings


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        settings = get_settings()
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
        )
        self._fastmail = FastMail(conf)
        self._settings = settings

    async def send_verification_email(self, email: str, token: str) -> None:
        """
        Send a verification email with a link containing the JWT token.

        Args:
            email: Recipient email address
            token: JWT verification token
        """
        verify_url = f"{self._settings.FRONTEND_URL}/api/users/verify-email?token={token}"

        html_body = f"""
        <html>
        <body>
            <h2>Email Verification</h2>
            <p>Please click the link below to verify your email address:</p>
            <p><a href="{verify_url}">Verify Email</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you did not create an account, please ignore this email.</p>
        </body>
        </html>
        """

        message = MessageSchema(
            subject="Verify your email address",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        await self._fastmail.send_message(message)
