"""
Integration test shared fixtures.

策略：
- 每個測試建立獨立的 SQLite in-memory 資料庫（function scope）
- 透過 monkeypatch 將所有 UnitOfWork 模組的 engine 替換為測試用 engine
- 僅 mock 外部服務（Email、Kafka、MQTT）
- 測試流程：HTTP request → Router → Service → Repository → SQLite DB
"""
import importlib
import pytest
import uuid
from datetime import date
from uuid import uuid4

from uuid import UUID as PyUUID

from sqlalchemy import create_engine, BigInteger, Uuid as SaUuid
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from passlib.context import CryptContext

# SQLite 不支援 BigInteger 自動遞增，需要將 BigInteger 編譯為 INTEGER
@compiles(BigInteger, "sqlite")
def _compile_big_int_sqlite(type_, compiler, **kw):
    return "INTEGER"


# SQLite 不支援原生 UUID 型別，SQLAlchemy 的 Uuid bind_processor 預期 uuid.UUID 物件，
# 但生產程式碼有些地方傳入 str。此 patch 讓 SQLite 模式下也能接受 str 格式的 UUID。
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

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# UnitOfWork 模組清單（所有需要替換 engine 的模組）
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
    """每個測試用獨立的 in-memory SQLite 資料庫（shared cache，跨執行緒可用）。

    使用 shared-cache 模式讓 seed 資料與 HTTP 請求（不同執行緒）使用同一個 DB，
    並用唯一的 db_name 確保測試間完全隔離。
    """
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
    """將所有 UoW 模組的 engine 替換為測試用 SQLite engine。

    UoW 的 __init__ 會讀取模組層級的 engine 名稱來建立 session_factory，
    透過 monkeypatch.setattr 可在每次 UoW 實例化時注入測試 engine。
    """
    for module_path in _UOW_MODULES:
        mod = importlib.import_module(module_path)
        monkeypatch.setattr(mod, "engine", test_engine)


@pytest.fixture
def db_session(test_engine) -> Session:
    """提供直接操作測試資料庫的 session，用於 seed 資料。"""
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
    """在測試資料庫中建立 User + Profile，回傳帳號資訊 dict。"""
    user_id = uuid4()
    user = User(
        id=user_id,
        uid=uid,
        pwd=_pwd_context.hash(password),
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
    """建立 Admin 測試帳號。"""
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
    """建立一般使用者測試帳號（email 已驗證）。"""
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
    """建立 email 尚未驗證的使用者帳號。"""
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
    """建立測試用 FastAPI app（無 MQTT/Kafka lifespan）。"""
    from app.exceptions.BaseException import BaseException as AppBaseException
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    import app.router

    test_app = FastAPI()

    # Use a disabled limiter so rate limits never block normal integration tests
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
def client() -> TestClient:
    """提供 FastAPI TestClient，使用真實 Router/Service/Repository 層。"""
    app = _create_test_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def get_auth_token(client: TestClient, uid_or_email: str, password: str) -> str:
    """輔助函式：登入並回傳 Bearer token。"""
    resp = client.post(
        "/users/login",
        data={"username": uid_or_email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    """回傳 Authorization header dict。"""
    return {"Authorization": f"Bearer {token}"}
