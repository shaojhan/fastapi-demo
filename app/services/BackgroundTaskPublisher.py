from typing import Protocol


class BackgroundTaskPublisher(Protocol):
    def enqueue_demo_task(self) -> str:
        """Queue the demo long-running task and return its task id."""

    def enqueue_employee_batch_import(self, rows: list[dict]) -> str:
        """Queue employee batch import and return its task id."""

    def enqueue_mqtt_summary(self, hours: int) -> str:
        """Queue MQTT summary generation and return its task id."""


class CeleryBackgroundTaskPublisher:
    def enqueue_demo_task(self) -> str:
        from app.tasks.add_tasks import very_long_task

        return very_long_task.delay().id

    def enqueue_employee_batch_import(self, rows: list[dict]) -> str:
        from app.tasks.employee_tasks import batch_import_employees_task

        return batch_import_employees_task.delay(rows).id

    def enqueue_mqtt_summary(self, hours: int) -> str:
        from app.tasks.mqtt_summary_tasks import send_mqtt_summary_task

        return send_mqtt_summary_task.delay(hours=hours).id


class NoopBackgroundTaskPublisher:
    def __init__(self, task_id: str = "noop-task-id"):
        self.task_id = task_id

    def enqueue_demo_task(self) -> str:
        return self.task_id

    def enqueue_employee_batch_import(self, rows: list[dict]) -> str:
        return self.task_id

    def enqueue_mqtt_summary(self, hours: int) -> str:
        return self.task_id
