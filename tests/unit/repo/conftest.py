"""
Fixtures for repository tests.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db import Base
from database.models.employee import Employee
from database.models.role import Role
from database.models.authority import Authority
from database.models.association import role_authority


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
