import asyncio
from uuid import UUID

from celery import shared_task
from loguru import logger

from app.services.LINEService import LINEService


@shared_task(
    bind=True,
    name="line.notification.approval_created",
    max_retries=2,
    default_retry_delay=60,
    ignore_result=True,
)
def notify_approver_of_new_request(
    self,
    approval_request_id: str,
    approval_type: str,
    approver_user_id: str,
) -> None:
    """
    Send a LINE push notification to the first approver when a new approval
    request is created.

    Args:
        approval_request_id: The UUID of the new approval request.
        approval_type: "LEAVE" or "EXPENSE".
        approver_user_id: The UUID of the user who should approve the request.
    """
    from app.db import SessionLocal
    from database.models.user import User

    with SessionLocal() as session:
        user = session.query(User).filter(User.id == UUID(approver_user_id)).first()
        if not user or not user.line_user_id:
            logger.info(
                f"Skipping LINE notify for approver {approver_user_id}: no line_user_id bound"
            )
            return

        line_user_id = user.line_user_id

    type_label = "請假" if approval_type == "LEAVE" else "報帳"
    short_id = approval_request_id[:8]
    message = (
        f"您有一筆新的{type_label}申請待審核\n"
        f"申請編號：{short_id}...\n"
        f"請登入系統進行審核。"
    )

    service = LINEService()
    try:
        asyncio.run(service.push_text_message(line_user_id, message))
    except Exception as exc:
        logger.error(f"LINE notify failed for approver {approver_user_id}: {exc}")
        raise self.retry(exc=exc)
