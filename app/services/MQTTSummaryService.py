from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

import httpx
from loguru import logger

from app.config import get_settings
from app.domain.MQTTModel import MQTTMessageModel
from app.services.EmailService import EmailService
from app.services.OllamaClient import OllamaClient
from app.services.unitofwork.MQTTUnitOfWork import MQTTUnitOfWork
from app.services.unitofwork.UserUnitOfWork import UserQueryUnitOfWork


class MQTTSummaryService:
    """Orchestrates the MQTT daily digest: fetch → AI summarise → email."""

    def __init__(self):
        self.ollama = OllamaClient()
        self.email_service = EmailService()
        self.settings = get_settings()

    # ── Private helpers ──────────────────────────────────────────────────

    def _fetch_recent_messages(self, hours: int) -> List[MQTTMessageModel]:
        """Return MQTT messages received within the last `hours` hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        with MQTTUnitOfWork() as uow:
            messages, _ = uow.repo.get_messages(
                received_after=cutoff,
                page=1,
                size=500,
            )
        return messages

    async def _generate_summary(
        self, messages: List[MQTTMessageModel], hours: int
    ) -> str:
        """Call OllamaClient to produce a Traditional-Chinese digest.

        Returns a fallback string (does not raise) if Ollama is unavailable,
        so the email still sends even when the LLM is down.
        """
        if not messages:
            return f"過去 {hours} 小時內沒有收到任何 MQTT 訊息。"

        lines = [
            f"{i + 1}. [{m.topic}] {m.payload[:200]}  ({m.received_at.strftime('%H:%M:%S')})"
            for i, m in enumerate(messages)
        ]
        message_text = "\n".join(lines)

        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "你是一位系統分析師，請使用繁體中文撰寫 MQTT 訊息摘要。"
                    "請依主題（topic）分組彙整，標示異常或值得注意的事件，"
                    "並在最後加上整體評估。格式要清晰、適合直接貼在電子郵件中。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"以下是過去 {hours} 小時的 MQTT 訊息（共 {len(messages)} 筆），"
                    f"請產生每日摘要報告：\n\n{message_text}"
                ),
            },
        ]

        try:
            response = await self.ollama.chat_completion(prompt_messages)
            return response["choices"][0]["message"]["content"]
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError) as exc:
            logger.error(f"Ollama unreachable during MQTT summary generation: {exc}")
            return f"（AI 摘要服務暫時無法使用。原始訊息筆數：{len(messages)} 筆）"

    def _get_recipient_emails(self) -> List[str]:
        """Collect email addresses for all email-verified users."""
        with UserQueryUnitOfWork() as uow:
            users, _ = uow.query_repo.get_all(page=1, size=9999)
        return [u.email for u in users if u.email_verified]

    # ── Public entry point ───────────────────────────────────────────────

    async def generate_and_send(self, hours: int | None = None) -> dict:
        """Full pipeline: fetch → summarise → email all verified users.

        Args:
            hours: Look-back window override; falls back to
                   settings.MQTT_SUMMARY_HOURS when None.

        Returns:
            {message_count, recipient_count, sent_count, failed_count}
        """
        if hours is None:
            hours = self.settings.MQTT_SUMMARY_HOURS

        messages = self._fetch_recent_messages(hours)
        summary = await self._generate_summary(messages, hours)
        recipients = self._get_recipient_emails()

        sent = 0
        failed = 0
        for email in recipients:
            try:
                await self.email_service.send_summary_email(email, summary, hours)
                sent += 1
            except Exception as exc:
                logger.warning(f"Failed to send MQTT summary email to {email}: {exc}")
                failed += 1

        logger.info(
            f"MQTT summary: {sent} sent, {failed} failed, "
            f"{len(messages)} messages, window={hours}h"
        )
        return {
            "message_count": len(messages),
            "recipient_count": len(recipients),
            "sent_count": sent,
            "failed_count": failed,
        }
