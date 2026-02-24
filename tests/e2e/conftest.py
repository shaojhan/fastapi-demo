"""
E2E 測試共用配置。

由於 pytest 不允許在非根目錄的 conftest.py 中使用 pytest_plugins，
此檔案直接複製整合測試所需的 fixture，讓 e2e 測試使用同樣的
SQLite in-memory 資料庫基礎設施。
"""

import importlib
import uuid
import pytest
from datetime import date
from uuid import uuid4

from sqlalchemy import create_engine, BigInteger, Uuid as SaUuid
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from uuid import UUID as PyUUID

# SQLite 不支援 BigInteger 自動遞增
@compiles(BigInteger, "sqlite")
def _compile_big_int_sqlite(type_, compiler, **kw):
    return "INTEGER"


# SQLite UUID bind_processor patch（支援 str 格式 UUID）
_orig_uuid_bind_processor = SaUuid.bind_processor


def _patched_uuid_bind_processor(self, dialect):
    orig = _orig_uuid_bind_processor(self, dialect)
    if orig is None:
        return None

    def process(value):
        if isinstance(value, str):
            try:
                value = PyUUID(value)
            except (ValueError, AttributeError):
                pass
        return orig(value)

    return process


SaUuid.bind_processor = _patched_uuid_bind_processor


from app.db import Base
from database.models.user import User, Profile
from app.domain.UserModel import UserRole
from app.utils.password import hash_password as _hash_password

_UOW_MODULES = [
    "app.services.unitofwork.UserUnitOfWork",
    "app.services.unitofwork.LoginRecordUnitOfWork",
    "app.services.unitofwork.SSOUnitOfWork",
    "app.services.unitofwork.EmployeeUnitOfWork",
    "app.services.unitofwork.AssignEmployeeUnitOfWork",
    "app.services.unitofwork.MessageUnitOfWork",
    "app.services.unitofwork.ScheduleUnitOfWork",
    "app.services.unitofwork.ApprovalUnitOfWork",
    "app.services.unitofwork.ChatUnitOfWork",
    "app.services.unitofwork.MQTTUnitOfWork",
    "app.services.unitofwork.KafkaUnitOfWork",
    "app.services.unitofwork.WorkflowUnitOfWork",
]


@pytest.fixture
def test_engine():
    db_name = f"testdb_{uuid.uuid4().hex}"
    url = f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true"
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def patch_uow_engines(test_engine, monkeypatch):
    for module_path in _UOW_MODULES:
        mod = importlib.import_module(module_path)
        monkeypatch.setattr(mod, "engine", test_engine)


@pytest.fixture
def db_session(test_engine) -> Session:
    SessionFactory = sessionmaker(bind=test_engine, expire_on_commit=False)
    session = SessionFactory()
    yield session
    session.close()


def _seed_user(
    session: Session,
    uid: str,
    email: str,
    password: str,
    role: UserRole,
    name: str = "",
    email_verified: bool = True,
) -> dict:
    user_id = uuid4()
    user = User(
        id=user_id,
        uid=uid,
        pwd=_hash_password(password),
        email=email,
        role=role,
        email_verified=email_verified,
    )
    profile = Profile(
        name=name or uid,
        birthdate=date(1990, 1, 1),
        description="",
    )
    user.profile = profile
    session.add(user)
    session.commit()
    session.refresh(user)
    return {
        "id": str(user_id),
        "uid": uid,
        "email": email,
        "password": password,
        "role": role,
    }


@pytest.fixture
def seed_admin(db_session: Session) -> dict:
    return _seed_user(
        db_session,
        uid="admin",
        email="admin@test.com",
        password="Admin123!",
        role=UserRole.ADMIN,
        name="Admin User",
    )


@pytest.fixture
def seed_normal_user(db_session: Session) -> dict:
    return _seed_user(
        db_session,
        uid="normaluser",
        email="normal@test.com",
        password="Normal123!",
        role=UserRole.NORMAL,
        name="Normal User",
    )


@pytest.fixture
def seed_unverified_user(db_session: Session) -> dict:
    return _seed_user(
        db_session,
        uid="unverified",
        email="unverified@test.com",
        password="Unverified123!",
        role=UserRole.NORMAL,
        name="Unverified User",
        email_verified=False,
    )


def _create_test_app() -> FastAPI:
    from app.exceptions.BaseException import BaseException as AppBaseException
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    import app.router

    test_app = FastAPI()
    test_app.state.limiter = Limiter(key_func=get_remote_address, enabled=False)
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @test_app.exception_handler(AppBaseException)
    async def _app_exception_handler(request, exc: AppBaseException):
        content = {"detail": exc.message}
        if exc.error_code:
            content["error_code"] = exc.error_code
        return JSONResponse(status_code=exc.status_code, content=content)

    test_app.include_router(app.router.router)
    return test_app


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    app = _create_test_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def get_auth_token(client, uid_or_email: str, password: str) -> str:
    resp = client.post(
        "/users/login",
        data={"username": uid_or_email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
