"""
Unit tests for MQTTRouter endpoints.
Tests HTTP layer for MQTT operations (Admin only).

測試策略:
- TestClient + dependency_overrides
- 驗證 Admin-only 授權
- 驗證各端點正確委派給 MQTTService
"""
import pytest
from unittest.mock import MagicMock
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
        id="33333333-3333-3333-3333-333333333333", uid="admin", email="admin@example.com",
        hashed_password="hashed", profile=DomainProfile(name="Admin"),
        role=UserRole.ADMIN, email_verified=True,
    )


class TestMQTTStatus:
    """測試 GET /mqtt/status 端點"""

    def test_get_status_as_admin(self):
        from app.router.MQTTRouter import get_mqtt_service
        app = _create_app()
        mock_service = MagicMock()
        mock_service.get_status.return_value = {"connected": True, "subscriptions": []}

        app.dependency_overrides[get_current_user] = lambda: _make_admin()
        app.dependency_overrides[get_mqtt_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get("/mqtt/status")
        assert response.status_code == 200

    def test_get_status_non_admin_forbidden(self):
        app = _create_app()
        normal = UserModel.reconstitute(
            id="44444444-4444-4444-4444-444444444444", uid="n", email="n@e.com", hashed_password="h",
            profile=DomainProfile(name="N"), role=UserRole.NORMAL,
        )
        app.dependency_overrides[get_current_user] = lambda: normal
        client = TestClient(app)

        response = client.get("/mqtt/status")
        assert response.status_code == 403


class TestMQTTPublish:
    """測試 POST /mqtt/publish 端點"""

    def test_publish_message(self):
        from app.router.MQTTRouter import get_mqtt_service
        app = _create_app()
        mock_service = MagicMock()

        app.dependency_overrides[get_current_user] = lambda: _make_admin()
        app.dependency_overrides[get_mqtt_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/mqtt/publish", json={
            "topic": "sensor/temp",
            "payload": '{"temp": 25}',
        })
        assert response.status_code == 200
        mock_service.publish.assert_called_once()


class TestMQTTMessages:
    """測試 GET /mqtt/messages 端點"""

    def test_get_messages(self):
        from app.router.MQTTRouter import get_mqtt_service
        app = _create_app()
        mock_service = MagicMock()
        mock_service.get_messages.return_value = ([], 0)

        app.dependency_overrides[get_current_user] = lambda: _make_admin()
        app.dependency_overrides[get_mqtt_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get("/mqtt/messages?page=1&size=10")
        assert response.status_code == 200
        assert response.json()["total"] == 0
