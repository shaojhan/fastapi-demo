"""
Unit tests for auth dependency functions (get_current_user, require_admin, require_employee).

測試策略:
- 建立最小化的 FastAPI app 搭配 TestClient
- Override 依賴注入來模擬不同角色的使用者
- 驗證認證和授權邏輯
"""
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.router.dependencies.auth import get_current_user, require_admin, require_employee
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.exceptions.UserException import ForbiddenError
from app.exceptions.BaseException import BaseException as AppBaseException


def _create_test_app():
    """建立測試用的最小化 FastAPI app"""
    app = FastAPI()

    # Register custom exception handler
    @app.exception_handler(AppBaseException)
    async def base_exception_handler(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.get("/test/me")
    def me(user: UserModel = Depends(get_current_user)):
        return {"uid": user.uid, "role": user.role.value}

    @app.get("/test/admin")
    def admin_only(user: UserModel = Depends(require_admin)):
        return {"uid": user.uid}

    @app.get("/test/employee")
    def employee_only(user: UserModel = Depends(require_employee)):
        return {"uid": user.uid}

    return app


class TestGetCurrentUser:
    """測試 get_current_user 依賴"""

    def test_authenticated_user_returns_user_info(self, mock_normal_user):
        """測試認證使用者能取得自身資訊"""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = lambda: mock_normal_user
        client = TestClient(app)

        response = client.get("/test/me")
        assert response.status_code == 200
        assert response.json()["uid"] == "normaluser"

    def test_unauthenticated_returns_401(self):
        """測試未認證時回傳 401（無 token）"""
        app = _create_test_app()
        client = TestClient(app)

        response = client.get("/test/me")
        assert response.status_code == 401


class TestRequireAdmin:
    """測試 require_admin 依賴"""

    def test_admin_passes(self, mock_admin_user):
        """測試管理員通過授權"""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user
        client = TestClient(app)

        response = client.get("/test/admin")
        assert response.status_code == 200

    def test_normal_user_forbidden(self, mock_normal_user):
        """測試一般使用者被拒絕"""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = lambda: mock_normal_user
        client = TestClient(app)

        response = client.get("/test/admin")
        assert response.status_code == 403

    def test_employee_user_forbidden(self, mock_employee_user):
        """測試員工使用者被拒絕"""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = lambda: mock_employee_user
        client = TestClient(app)

        response = client.get("/test/admin")
        assert response.status_code == 403


class TestRequireEmployee:
    """測試 require_employee 依賴"""

    def test_employee_passes(self, mock_employee_user):
        """測試員工通過授權"""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = lambda: mock_employee_user
        client = TestClient(app)

        response = client.get("/test/employee")
        assert response.status_code == 200

    def test_admin_passes(self, mock_admin_user):
        """測試管理員也通過（admin 是 employee 的超集）"""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user
        client = TestClient(app)

        response = client.get("/test/employee")
        assert response.status_code == 200

    def test_normal_user_forbidden(self, mock_normal_user):
        """測試一般使用者被拒絕"""
        app = _create_test_app()
        app.dependency_overrides[get_current_user] = lambda: mock_normal_user
        client = TestClient(app)

        response = client.get("/test/employee")
        assert response.status_code == 403
