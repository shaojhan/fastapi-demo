from typing import Protocol


class ApprovalNotificationPublisher(Protocol):
    def approval_created(
        self,
        approval_request_id: str,
        approval_type: str,
        approver_user_id: str,
    ) -> None:
        """Publish a notification for a newly created approval request."""


class CeleryApprovalNotificationPublisher:
    def approval_created(
        self,
        approval_request_id: str,
        approval_type: str,
        approver_user_id: str,
    ) -> None:
        from app.tasks.line_notification_tasks import notify_approver_of_new_request

        notify_approver_of_new_request.delay(
            approval_request_id=approval_request_id,
            approval_type=approval_type,
            approver_user_id=approver_user_id,
        )


class NoopApprovalNotificationPublisher:
    def approval_created(
        self,
        approval_request_id: str,
        approval_type: str,
        approver_user_id: str,
    ) -> None:
        return None
