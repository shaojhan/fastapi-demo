"""
Unit tests for UserRouter endpoints.
Tests HTTP layer: request validation, response format, auth checks, service delegation.

測試策略:
- 使用 TestClient + dependency_overrides mock Service 層
- 驗證端點的 HTTP 狀態碼、回應格式、認證需求
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.router.UserRouter import router
from app.router.dependencies.auth import get_current_user, require_admin
from app.router.UserRouter import get_user_service, get_auth_service, get_user_query_service, get_login_record_query_service
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.domain.services.AuthenticationService import AuthToken
from app.exceptions.BaseException import BaseException as AppBaseException


def _create_app():
    app = FastAPI()

    @app.exception_handler(AppBaseException)
    async def handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router)
    return app


def _make_user(role=UserRole.NORMAL):
    return UserModel.reconstitute(
        id="11111111-1111-1111-1111-111111111111", uid="testuser", email="test@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Test", birthdate=None, description=None),
        role=role, email_verified=True,
    )


class TestGetMe:
    """測試 GET /users/me 端點"""

    def test_get_me_authenticated(self):
        """測試已認證使用者能取得自身資訊"""
        app = _create_app()
        user = _make_user()
        app.dependency_overrides[get_current_user] = lambda: user
        client = TestClient(app)

        response = client.get("/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_me_unauthenticated(self):
        """測試未認證時回傳 401"""
        app = _create_app()
        client = TestClient(app)
        response = client.get("/users/me")
        assert response.status_code == 401


class TestCreateUser:
    """測試 POST /users/create 端點"""

    def test_create_user_success(self):
        """測試成功建立使用者"""
        app = _create_app()
        mock_service = MagicMock()
        mock_service.add_user_profile = MagicMock()
        mock_service.send_pending_verification_email = AsyncMock()
        app.dependency_overrides[get_user_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/users/create", json={
            "uid": "newuser",
            "pwd": "P@ssword123",
            "email": "new@example.com",
            "name": "New User",
            "birthdate": "1990-01-01",
            "description": "",
            "role": "NORMAL",
        })

        assert response.status_code == 200
        mock_service.add_user_profile.assert_called_once()


class TestLoginUser:
    """測試 POST /users/login 端點"""

    def test_login_success(self):
        """測試成功登入"""
        app = _create_app()
        user = _make_user()
        mock_auth = MagicMock()
        mock_auth.login.return_value = (
            AuthToken(access_token="jwt_token", token_type="bearer"),
            user,
        )
        app.dependency_overrides[get_auth_service] = lambda: mock_auth
        client = TestClient(app)

        response = client.post("/users/login", data={
            "username": "testuser",
            "password": "P@ssword123",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "jwt_token"
        assert data["user"]["uid"] == "testuser"


class TestListUsers:
    """測試 GET /users/ 端點（Admin only）"""

    def test_list_users_as_admin(self):
        """測試管理員能列出所有使用者"""
        app = _create_app()
        admin = _make_user(role=UserRole.ADMIN)
        mock_query = MagicMock()
        mock_query.get_all_users.return_value = ([admin], 1)

        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_user_query_service] = lambda: mock_query
        client = TestClient(app)

        response = client.get("/users/?page=1&size=10")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_list_users_as_normal_user_forbidden(self):
        """測試一般使用者無法列出所有使用者"""
        app = _create_app()
        user = _make_user(role=UserRole.NORMAL)
        app.dependency_overrides[get_current_user] = lambda: user
        client = TestClient(app)

        response = client.get("/users/?page=1&size=10")
        assert response.status_code == 403


class TestSearchUsers:
    """測試 GET /users/search 端點"""

    def test_search_users_authenticated(self):
        """測試已認證使用者能搜尋"""
        app = _create_app()
        user = _make_user()
        mock_query = MagicMock()
        mock_query.search_users.return_value = ([], 0)

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_user_query_service] = lambda: mock_query
        client = TestClient(app)

        response = client.get("/users/search?keyword=test")
        assert response.status_code == 200


class TestVerifyEmail:
    """測試 GET /users/verify-email 端點"""

    def test_verify_email_success(self):
        """測試成功驗證 email"""
        app = _create_app()
        mock_service = MagicMock()
        app.dependency_overrides[get_user_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get("/users/verify-email?token=valid_token")
        assert response.status_code == 200
        mock_service.verify_email.assert_called_once_with("valid_token")


class TestUpdatePassword:
    """測試 POST /users/update 端點"""

    def test_update_password_success(self):
        """測試成功更新密碼"""
        app = _create_app()
        mock_service = MagicMock()
        app.dependency_overrides[get_user_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/users/update", json={
            "user_id": "11d200ac-48d8-4675-bfc0-a3a61af3c499",
            "old_password": "OldP@ss123",
            "new_password": "NewP@ss456",
        })

        assert response.status_code == 200
        mock_service.update_password.assert_called_once()


class TestUpdateProfile:
    """測試 POST /users/profile/update 端點"""

    def test_update_profile_success(self):
        """測試成功更新個人資料"""
        app = _create_app()
        mock_service = MagicMock()
        mock_service.update_user_profile.return_value = _make_user()
        app.dependency_overrides[get_user_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/users/profile/update", json={
            "user_id": "11d200ac-48d8-4675-bfc0-a3a61af3c499",
            "name": "New Name",
            "birthdate": "1990-05-15",
            "description": "Updated desc",
        })

        assert response.status_code == 200
        mock_service.update_user_profile.assert_called_once()
