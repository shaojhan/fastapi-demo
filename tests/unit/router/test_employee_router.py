"""
Unit tests for EmployeeRouter endpoints.
Tests HTTP layer for employee management (Admin only).

測試策略:
- TestClient + dependency_overrides
- 驗證 Admin-only 授權
- 驗證 list 和 assign 端點
"""
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.router.EmployeeRouter import router
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


class TestListEmployees:
    """測試 GET /employees/ 端點"""

    def test_list_as_admin(self):
        from app.router.EmployeeRouter import get_employee_query_service
        app = _create_app()
        mock_query = MagicMock()
        mock_query.get_all_employees_paginated.return_value = ([], 0)

        app.dependency_overrides[get_current_user] = lambda: _make_admin()
        app.dependency_overrides[get_employee_query_service] = lambda: mock_query
        client = TestClient(app)

        response = client.get("/employees/?page=1&size=10")
        assert response.status_code == 200

    def test_list_as_normal_user_forbidden(self):
        app = _create_app()
        normal = UserModel.reconstitute(
            id="44444444-4444-4444-4444-444444444444", uid="n", email="n@e.com", hashed_password="h",
            profile=DomainProfile(name="N"), role=UserRole.NORMAL,
        )
        app.dependency_overrides[get_current_user] = lambda: normal
        client = TestClient(app)

        response = client.get("/employees/")
        assert response.status_code == 403


class TestAssignEmployee:
    """測試 POST /employees/assign 端點"""

    def test_assign_employee_as_admin(self):
        from app.router.EmployeeRouter import get_employee_service
        app = _create_app()
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.id = 1
        mock_result.idno = "EMP001"
        mock_result.department = "IT"
        mock_result.user_id = "66666666-6666-6666-6666-666666666666"
        mock_result.role = MagicMock()
        mock_result.role.id = 1
        mock_result.role.name = "Developer"
        mock_result.role.level = 3
        mock_result.role.authorities = []
        mock_result.created_at = None
        mock_service.assign_user_as_employee.return_value = mock_result

        app.dependency_overrides[get_current_user] = lambda: _make_admin()
        app.dependency_overrides[get_employee_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/employees/assign", json={
            "user_id": "66666666-6666-6666-6666-666666666666",
            "idno": "EMP001",
            "department": "IT",
            "role_id": 1,
        })
        assert response.status_code == 200
        mock_service.assign_user_as_employee.assert_called_once()
