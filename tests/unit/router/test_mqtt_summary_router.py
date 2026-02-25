"""
Unit tests for MQTT summary trigger endpoint.

測試策略:
- TestClient + dependency_overrides
- Mock send_mqtt_summary_task.delay
- 驗證 Admin-only 授權、參數驗證、task 呼叫
"""
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.router.MQTTRouter import router
from app.router.dependencies.auth import get_current_user
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.exceptions.BaseException import BaseException as AppBaseException


def _create_app():
    app = FastAPI()

    @app.exception_handler(AppBaseException)
    async def handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router)
    return app


def _make_admin():
    return UserModel.reconstitute(
        id="33333333-3333-3333-3333-333333333333",
        uid="admin",
        email="admin@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Admin"),
        role=UserRole.ADMIN,
        email_verified=True,
    )


def _make_normal():
    return UserModel.reconstitute(
        id="11111111-1111-1111-1111-111111111111",
        uid="normal",
        email="normal@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Normal"),
        role=UserRole.NORMAL,
        email_verified=True,
    )


class TestMQTTSummaryTrigger:

    def test_trigger_returns_task_id_for_admin(self):
        app = _create_app()
        app.dependency_overrides[get_current_user] = lambda: _make_admin()

        fake_task = MagicMock()
        fake_task.id = "celery-task-abc123"

        with patch(
            "app.router.MQTTRouter.send_mqtt_summary_task"
        ) as mock_task_fn:
            mock_task_fn.delay.return_value = fake_task
            client = TestClient(app)
            resp = client.post("/mqtt/summary/trigger", json={"hours": 24})

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "celery-task-abc123"
        assert data["hours"] == 24
        assert "message" in data

    def test_trigger_forbidden_for_non_admin(self):
        app = _create_app()
        app.dependency_overrides[get_current_user] = lambda: _make_normal()
        client = TestClient(app)

        resp = client.post("/mqtt/summary/trigger", json={"hours": 24})
        assert resp.status_code == 403

    def test_trigger_default_hours_is_24(self):
        app = _create_app()
        app.dependency_overrides[get_current_user] = lambda: _make_admin()

        fake_task = MagicMock()
        fake_task.id = "task-id-456"

        with patch("app.router.MQTTRouter.send_mqtt_summary_task") as mock_task_fn:
            mock_task_fn.delay.return_value = fake_task
            client = TestClient(app)
            resp = client.post("/mqtt/summary/trigger", json={})

        assert resp.status_code == 200
        mock_task_fn.delay.assert_called_once_with(hours=24)

    def test_trigger_custom_hours_passed_to_task(self):
        app = _create_app()
        app.dependency_overrides[get_current_user] = lambda: _make_admin()

        fake_task = MagicMock()
        fake_task.id = "task-id-789"

        with patch("app.router.MQTTRouter.send_mqtt_summary_task") as mock_task_fn:
            mock_task_fn.delay.return_value = fake_task
            client = TestClient(app)
            resp = client.post("/mqtt/summary/trigger", json={"hours": 48})

        assert resp.status_code == 200
        assert resp.json()["hours"] == 48
        mock_task_fn.delay.assert_called_once_with(hours=48)

    def test_trigger_hours_out_of_range_rejected(self):
        app = _create_app()
        app.dependency_overrides[get_current_user] = lambda: _make_admin()
        client = TestClient(app)

        resp = client.post("/mqtt/summary/trigger", json={"hours": 200})
        assert resp.status_code == 422

    def test_trigger_hours_zero_rejected(self):
        app = _create_app()
        app.dependency_overrides[get_current_user] = lambda: _make_admin()
        client = TestClient(app)

        resp = client.post("/mqtt/summary/trigger", json={"hours": 0})
        assert resp.status_code == 422
