"""
Fixtures for repository tests.
"""
import pytest
from uuid import uuid4
from datetime import datetime, date
from sqlalchemy import create_engine, BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session


# SQLite 不支援 BigInteger 自動遞增，需要將 BigInteger 編譯為 INTEGER
@compiles(BigInteger, "sqlite")
def compile_big_int_sqlite(type_, compiler, **kw):
    return "INTEGER"
from app.db import Base
from database.models.employee import Employee
from database.models.role import Role
from database.models.authority import Authority
from database.models.association import role_authority
from database.models.user import User, Profile
from database.models.schedule import Schedule, GoogleCalendarConfig
from database.models.message import Message
from database.models.chat import Conversation, ChatMessage
from database.models.login_record import LoginRecord
from database.models.approval import ApprovalRequestORM, ApprovalStepORM
from database.models.kafka import KafkaMessage
from database.models.mqtt import MQTTMessage
from app.domain.UserModel import UserRole


@pytest.fixture(scope="function")
def test_db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=test_db_engine, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_roles(test_db_session: Session):
    """Create sample roles for testing."""
    roles = [
        Role(id=1, name="Manager", level=5),
        Role(id=2, name="Developer", level=3),
        Role(id=3, name="Intern", level=1),
    ]

    for role in roles:
        test_db_session.add(role)

    test_db_session.commit()

    for role in roles:
        test_db_session.refresh(role)

    return roles


@pytest.fixture(scope="function")
def sample_authorities(test_db_session: Session):
    """Create sample authorities for testing."""
    authorities = [
        Authority(id=1, name="READ", description="Read access"),
        Authority(id=2, name="WRITE", description="Write access"),
        Authority(id=3, name="DELETE", description="Delete access"),
        Authority(id=4, name="ADMIN", description="Admin access"),
    ]

    for authority in authorities:
        test_db_session.add(authority)

    test_db_session.commit()

    for authority in authorities:
        test_db_session.refresh(authority)

    return authorities


@pytest.fixture(scope="function")
def roles_with_authorities(test_db_session: Session, sample_roles, sample_authorities):
    """Assign authorities to roles."""
    manager_role = sample_roles[0]  # Manager
    developer_role = sample_roles[1]  # Developer
    intern_role = sample_roles[2]  # Intern

    # Manager has all authorities
    manager_role.authorities = sample_authorities

    # Developer has READ and WRITE
    developer_role.authorities = [sample_authorities[0], sample_authorities[1]]

    # Intern has only READ
    intern_role.authorities = [sample_authorities[0]]

    test_db_session.commit()

    return {
        "manager": manager_role,
        "developer": developer_role,
        "intern": intern_role
    }


@pytest.fixture(scope="function")
def sample_users(test_db_session: Session):
    """Create sample users for testing."""
    users = [
        User(
            id=uuid4(),
            uid="user1",
            pwd="hashed_password",
            email="user1@example.com",
            role=UserRole.EMPLOYEE
        ),
        User(
            id=uuid4(),
            uid="user2",
            pwd="hashed_password",
            email="user2@example.com",
            role=UserRole.EMPLOYEE
        ),
        User(
            id=uuid4(),
            uid="admin",
            pwd="hashed_password",
            email="admin@example.com",
            role=UserRole.ADMIN
        ),
    ]

    for user in users:
        test_db_session.add(user)

    test_db_session.commit()

    for user in users:
        test_db_session.refresh(user)

    return users


@pytest.fixture(scope="function")
def sample_schedules(test_db_session: Session, sample_users):
    """Create sample schedules for testing."""
    creator = sample_users[0]

    schedules = [
        Schedule(
            id=uuid4(),
            title="Team Meeting",
            description="Weekly team meeting",
            location="Meeting Room A",
            start_time=datetime(2024, 12, 1, 9, 0),
            end_time=datetime(2024, 12, 1, 10, 0),
            all_day=False,
            timezone="Asia/Taipei",
            creator_id=creator.id,
        ),
        Schedule(
            id=uuid4(),
            title="Project Review",
            description="Quarterly project review",
            location="Conference Room",
            start_time=datetime(2024, 12, 2, 14, 0),
            end_time=datetime(2024, 12, 2, 16, 0),
            all_day=False,
            timezone="Asia/Taipei",
            creator_id=creator.id,
        ),
    ]

    for schedule in schedules:
        test_db_session.add(schedule)

    test_db_session.commit()

    for schedule in schedules:
        test_db_session.refresh(schedule)

    return schedules


@pytest.fixture(scope="function")
def sample_messages(test_db_session: Session, sample_users):
    """Create sample messages for testing."""
    sender = sample_users[0]
    recipient = sample_users[1]

    messages = [
        Message(
            subject="Hello",
            content="Hello, how are you?",
            sender_id=sender.id,
            recipient_id=recipient.id,
            is_read=False,
        ),
        Message(
            subject="Meeting Notice",
            content="Please attend the meeting tomorrow",
            sender_id=sender.id,
            recipient_id=recipient.id,
            is_read=True,
            read_at=datetime.now(),
        ),
    ]

    for message in messages:
        test_db_session.add(message)

    test_db_session.commit()

    for message in messages:
        test_db_session.refresh(message)

    return messages


@pytest.fixture(scope="function")
def sample_login_records(test_db_session: Session, sample_users):
    """Create sample login records for testing."""
    user1 = sample_users[0]
    user2 = sample_users[1]

    records = [
        LoginRecord(
            id=uuid4(),
            user_id=user1.id,
            username="user1",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 Chrome",
            success=True,
            failure_reason=None,
        ),
        LoginRecord(
            id=uuid4(),
            user_id=user1.id,
            username="user1",
            ip_address="192.168.1.2",
            user_agent="Mozilla/5.0 Firefox",
            success=False,
            failure_reason="密碼錯誤",
        ),
        LoginRecord(
            id=uuid4(),
            user_id=user2.id,
            username="user2",
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0 Safari",
            success=True,
            failure_reason=None,
        ),
        LoginRecord(
            id=uuid4(),
            user_id=None,
            username="nonexistent",
            ip_address="10.0.0.2",
            user_agent="curl/7.88",
            success=False,
            failure_reason="帳號不存在",
        ),
    ]

    for record in records:
        test_db_session.add(record)

    test_db_session.commit()

    for record in records:
        test_db_session.refresh(record)

    return records
