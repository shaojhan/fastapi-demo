"""
Unit tests for MessageRouter endpoints.

測試策略:
- TestClient + dependency_overrides
- 驗證認證需求和基本 CRUD 端點
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.router.MessageRouter import router
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


def _make_user():
    return UserModel.reconstitute(
        id="11111111-1111-1111-1111-111111111111", uid="user", email="user@example.com",
        hashed_password="hashed", profile=DomainProfile(name="User"),
        role=UserRole.NORMAL, email_verified=True,
    )


class TestSendMessage:
    """測試 POST /messages/ 端點"""

    def test_send_message_authenticated(self):
        from app.router.MessageRouter import get_message_service
        app = _create_app()
        user = _make_user()
        mock_service = MagicMock()
        mock_sender = MagicMock()
        mock_sender.user_id = "11111111-1111-1111-1111-111111111111"
        mock_sender.username = "user"
        mock_sender.email = "user@example.com"
        mock_recipient = MagicMock()
        mock_recipient.user_id = "22222222-2222-2222-2222-222222222222"
        mock_recipient.username = "other"
        mock_recipient.email = "other@example.com"
        mock_msg = MagicMock()
        mock_msg.id = 1
        mock_msg.subject = "Hello"
        mock_msg.content = "Hi there"
        mock_msg.sender = mock_sender
        mock_msg.recipient = mock_recipient
        mock_msg.is_read = False
        mock_msg.read_at = None
        mock_msg.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_msg.parent_id = None
        mock_service.send_message.return_value = mock_msg

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_message_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/messages/", json={
            "recipient_id": "22222222-2222-2222-2222-222222222222",
            "subject": "Hello",
            "content": "Hi there",
        })
        assert response.status_code == 200
        mock_service.send_message.assert_called_once()


class TestGetInbox:
    """測試 GET /messages/inbox 端點"""

    def test_get_inbox(self):
        from app.router.MessageRouter import get_message_service
        app = _create_app()
        user = _make_user()
        mock_service = MagicMock()
        mock_service.get_inbox.return_value = ([], 0, 0)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_message_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get("/messages/inbox?page=1&size=10")
        assert response.status_code == 200

    def test_get_inbox_unauthenticated(self):
        app = _create_app()
        client = TestClient(app)
        response = client.get("/messages/inbox")
        assert response.status_code == 401


class TestUnreadCount:
    """測試 GET /messages/unread-count 端點"""

    def test_get_unread_count(self):
        from app.router.MessageRouter import get_message_service
        app = _create_app()
        user = _make_user()
        mock_service = MagicMock()
        mock_service.get_unread_count.return_value = 5

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_message_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get("/messages/unread-count")
        assert response.status_code == 200
        assert response.json()["count"] == 5
