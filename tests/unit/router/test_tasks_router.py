from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.router.TasksRouter import get_background_task_publisher, router


def _create_app():
    app = FastAPI()
    app.include_router(router)
    return app


class TestEnqueueDemoTask:
    def test_enqueue_add_uses_task_publisher(self):
        app = _create_app()
        mock_publisher = MagicMock()
        mock_publisher.enqueue_demo_task.return_value = "demo-task-123"
        app.dependency_overrides[get_background_task_publisher] = lambda: mock_publisher

        client = TestClient(app)
        response = client.get("/tasks/add")

        assert response.status_code == 200
        assert response.json() == {"task_id": "demo-task-123"}
        mock_publisher.enqueue_demo_task.assert_called_once_with()
