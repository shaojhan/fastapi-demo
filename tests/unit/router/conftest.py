"""
Shared fixtures for Router layer unit tests.

測試策略:
- 使用 FastAPI TestClient 進行 HTTP 端點測試
- Override 依賴注入以 mock Service 層
- 使用 mock_user fixture 模擬已認證使用者
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile

# 固定的測試 UUID
NORMAL_USER_ID = "11111111-1111-1111-1111-111111111111"
EMPLOYEE_USER_ID = "22222222-2222-2222-2222-222222222222"
ADMIN_USER_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture
def mock_normal_user() -> UserModel:
    """建立模擬的一般使用者"""
    return UserModel.reconstitute(
        id=NORMAL_USER_ID,
        uid="normaluser",
        email="normal@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Normal User", birthdate=None, description=None),
        role=UserRole.NORMAL,
        email_verified=True,
    )


@pytest.fixture
def mock_employee_user() -> UserModel:
    """建立模擬的員工使用者"""
    return UserModel.reconstitute(
        id=EMPLOYEE_USER_ID,
        uid="employeeuser",
        email="employee@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Employee User", birthdate=None, description=None),
        role=UserRole.EMPLOYEE,
        email_verified=True,
    )


@pytest.fixture
def mock_admin_user() -> UserModel:
    """建立模擬的管理員使用者"""
    return UserModel.reconstitute(
        id=ADMIN_USER_ID,
        uid="adminuser",
        email="admin@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Admin User", birthdate=None, description=None),
        role=UserRole.ADMIN,
        email_verified=True,
    )
