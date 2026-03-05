import httpx
from loguru import logger

from app.config import get_settings

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


class LINEService:
    """Service for sending LINE push notifications via Messaging API."""

    def __init__(self):
        settings = get_settings()
        self._token = settings.LINE_CHANNEL_ACCESS_TOKEN

    async def push_text_message(self, line_user_id: str, text: str) -> bool:
        """
        Push a plain-text message to a LINE user.

        Args:
            line_user_id: The recipient's LINE user ID (starts with 'U').
            text: The message body (max 5000 chars).

        Returns:
            True on success, False otherwise.
        """
        if not self._token:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN is not configured — skipping push")
            return False

        payload = {
            "to": line_user_id,
            "messages": [{"type": "text", "text": text}],
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(LINE_PUSH_URL, json=payload, headers=headers)

            if response.status_code == 200:
                logger.info(f"LINE push sent to {line_user_id}")
                return True

            logger.error(
                f"LINE push failed: status={response.status_code} body={response.text}"
            )
            return False

        except httpx.HTTPError as exc:
            logger.error(f"LINE push HTTP error: {exc}")
            return False
