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
            USE_CREDENTIALS=bool(settings.MAIL_USERNAME),
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

    async def send_employee_password_email(self, email: str, uid: str, password: str) -> None:
        """
        Send an email to a newly created employee with their login credentials.

        Args:
            email: Recipient email address
            uid: The employee's login username
            password: The generated plain-text password
        """
        html_body = f"""
        <html>
        <body>
            <h2>Your Employee Account Has Been Created</h2>
            <p>An administrator has created an employee account for you. Below are your login credentials:</p>
            <ul>
                <li><strong>Username:</strong> {uid}</li>
                <li><strong>Password:</strong> {password}</li>
            </ul>
            <p>Please log in and change your password as soon as possible.</p>
        </body>
        </html>
        """

        message = MessageSchema(
            subject="Your Employee Account Credentials",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        await self._fastmail.send_message(message)

    async def send_password_reset_email(self, email: str, token: str) -> None:
        """
        Send a password reset email with a link containing the JWT token.

        Args:
            email: Recipient email address
            token: JWT password reset token
        """
        reset_url = f"{self._settings.FRONTEND_URL}/api/users/reset-password?token={token}"

        html_body = f"""
        <html>
        <body>
            <h2>Password Reset</h2>
            <p>You requested a password reset. Click the link below to set a new password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you did not request a password reset, please ignore this email.</p>
        </body>
        </html>
        """

        message = MessageSchema(
            subject="Reset your password",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        await self._fastmail.send_message(message)

    async def send_summary_email(
        self, email: str, summary: str, hours: int
    ) -> None:
        """
        Send the MQTT daily digest email to a single recipient.

        Args:
            email:   Recipient email address.
            summary: AI-generated summary text (may contain newlines).
            hours:   The look-back window used to generate the summary.
        """
        import zoneinfo
        from datetime import datetime, timezone

        tz = zoneinfo.ZoneInfo("Asia/Taipei")
        now_local = datetime.now(timezone.utc).astimezone(tz)
        summary_html = summary.replace("\n", "<br>")

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>MQTT 訊息每日摘要</h2>
            <p><strong>涵蓋期間：</strong>過去 {hours} 小時</p>
            <p><strong>產生時間：</strong>{now_local.strftime("%Y-%m-%d %H:%M %Z")}</p>
            <hr>
            <div style="background:#f9f9f9; padding:16px; border-left:4px solid #0078d4;">
                {summary_html}
            </div>
            <hr>
            <p style="color:#888; font-size:12px;">此郵件由系統自動產生，請勿直接回覆。</p>
        </body>
        </html>
        """

        message = MessageSchema(
            subject=f"【MQTT 摘要】{now_local.strftime('%Y-%m-%d')} 每日系統訊息彙整",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        await self._fastmail.send_message(message)
