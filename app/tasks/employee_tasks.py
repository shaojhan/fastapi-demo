from celery import shared_task
from loguru import logger

from app.services.EmployeeService import EmployeeService
from app.services.EmailService import EmailService


@shared_task(bind=True, name="etl.employee.batch_import", max_retries=0)
def batch_import_employees_task(self, rows: list[dict]) -> dict:
    """
    Celery task for batch importing employees from CSV data.
    Reports progress via PROGRESS state updates.
    """
    service = EmployeeService()

    def on_progress(current: int, total: int, current_idno: str):
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "percent": round((current / total) * 100, 1),
                "current_idno": current_idno,
            },
        )

    result = service.batch_import_employees_with_progress(
        rows, progress_callback=on_progress
    )

    # Send password emails for newly created users (best-effort)
    credentials = result.pop("new_user_credentials", [])
    if credentials:
        email_service = EmailService()
        for cred in credentials:
            try:
                import asyncio
                asyncio.run(
                    email_service.send_employee_password_email(
                        cred["email"], cred["uid"], cred["password"]
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to send password email to {cred['email']}: {e}")

    return result
