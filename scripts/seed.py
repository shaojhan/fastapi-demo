"""
Database seed script for initial data.

Usage: poetry run db-init

This script will:
1. Create common authorities (READ, WRITE, DELETE, APPROVE, EXPORT, ADMIN)
2. Create roles (Admin, Manager, Senior, Junior)
3. Create admin user account
4. Create test employee accounts across departments with different role levels

The script is idempotent - running it multiple times will not create duplicates.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.UserModel import UserRole, AccountType
from database.models.user import User, Profile
from database.models.employee import Employee
from database.models.role import Role
from database.models.authority import Authority

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Default authorities
DEFAULT_AUTHORITIES = [
    {"name": "READ", "description": "讀取資料權限"},
    {"name": "WRITE", "description": "寫入資料權限"},
    {"name": "DELETE", "description": "刪除資料權限"},
    {"name": "APPROVE", "description": "簽核權限"},
    {"name": "EXPORT", "description": "匯出資料權限"},
    {"name": "ADMIN", "description": "管理員權限"},
]

# Default admin user config
ADMIN_USER = {
    "uid": "admin",
    "password": "Admin@123",
    "email": "admin@example.com",
    "name": "Administrator",
}


def create_authorities(db: Session) -> list[Authority]:
    """Create default authorities if they don't exist."""
    authorities = []
    for auth_data in DEFAULT_AUTHORITIES:
        existing = db.query(Authority).filter(Authority.name == auth_data["name"]).first()
        if existing:
            print(f"  Authority '{auth_data['name']}' already exists, skipping.")
            authorities.append(existing)
        else:
            authority = Authority(**auth_data)
            db.add(authority)
            db.flush()
            print(f"  Created authority: {auth_data['name']}")
            authorities.append(authority)
    return authorities


def create_roles(db: Session, authorities: list[Authority]) -> dict[str, Role]:
    """Create all roles if they don't exist."""
    # Role definitions: name -> (level, authority_names)
    ROLE_DEFINITIONS = {
        "Admin":   (99, ["READ", "WRITE", "DELETE", "APPROVE", "EXPORT", "ADMIN"]),
        "Manager": (50, ["READ", "WRITE", "DELETE", "APPROVE", "EXPORT"]),
        "Senior":  (30, ["READ", "WRITE", "APPROVE"]),
        "Junior":  (10, ["READ", "WRITE"]),
    }

    auth_map = {a.name: a for a in authorities}
    roles = {}

    for role_name, (level, auth_names) in ROLE_DEFINITIONS.items():
        existing = db.query(Role).filter(Role.name == role_name).first()
        if existing:
            print(f"  Role '{role_name}' already exists, updating authorities.")
            existing.authorities = [auth_map[n] for n in auth_names]
            existing.level = level
            db.flush()
            roles[role_name] = existing
        else:
            role = Role(name=role_name, level=level)
            role.authorities = [auth_map[n] for n in auth_names]
            db.add(role)
            db.flush()
            print(f"  Created role: {role_name} (level={level})")
            roles[role_name] = role

    return roles


def create_admin_user(db: Session) -> User | None:
    """Create admin user if not exists."""
    existing = db.query(User).filter(User.uid == ADMIN_USER["uid"]).first()
    if existing:
        print(f"  Admin user '{ADMIN_USER['uid']}' already exists, skipping.")
        return None

    hashed_password = pwd_context.hash(ADMIN_USER["password"])

    admin_user = User(
        id=uuid4(),
        created_at=datetime.now(timezone.utc),
        uid=ADMIN_USER["uid"],
        pwd=hashed_password,
        email=ADMIN_USER["email"],
        role=UserRole.ADMIN,
        account_type=AccountType.SYSTEM,
        email_verified=True,
    )

    profile = Profile(
        created_at=datetime.now(timezone.utc),
        name=ADMIN_USER["name"],
        birthdate=date(2000, 1, 1),
        description="System Administrator",
    )
    admin_user.profile = profile

    db.add(admin_user)
    db.flush()
    print(f"  Created admin user: {ADMIN_USER['uid']} (password: {ADMIN_USER['password']})")
    return admin_user


# Test employee accounts: (uid, email, name, department, role_name)
TEST_EMPLOYEES = [
    # RD 部門
    ("rd_manager",  "rd.manager@example.com",  "王大明", "RD", "Manager"),
    ("rd_senior",   "rd.senior@example.com",   "李小華", "RD", "Senior"),
    ("rd_junior1",  "rd.junior1@example.com",  "張志豪", "RD", "Junior"),
    ("rd_junior2",  "rd.junior2@example.com",  "陳美玲", "RD", "Junior"),
    # IT 部門
    ("it_manager",  "it.manager@example.com",  "林建宏", "IT", "Manager"),
    ("it_senior",   "it.senior@example.com",   "黃雅琪", "IT", "Senior"),
    ("it_junior1",  "it.junior1@example.com",  "吳承恩", "IT", "Junior"),
    # HR 部門
    ("hr_manager",  "hr.manager@example.com",  "周芷若", "HR", "Manager"),
    ("hr_senior",   "hr.senior@example.com",   "趙敏敏", "HR", "Senior"),
    ("hr_junior1",  "hr.junior1@example.com",  "楊逍遙", "HR", "Junior"),
    # BD 部門
    ("bd_manager",  "bd.manager@example.com",  "孫業務", "BD", "Manager"),
    ("bd_junior1",  "bd.junior1@example.com",  "鄭小新", "BD", "Junior"),
    # PR 部門
    ("pr_manager",  "pr.manager@example.com",  "蔡公關", "PR", "Manager"),
    ("pr_junior1",  "pr.junior1@example.com",  "許文馨", "PR", "Junior"),
]

DEFAULT_PASSWORD = "Test@123"


def create_test_employees(db: Session, roles: dict[str, Role]) -> None:
    """Create test employee accounts with users across all departments."""
    hashed_password = pwd_context.hash(DEFAULT_PASSWORD)
    created_count = 0

    for uid, email, name, department, role_name in TEST_EMPLOYEES:
        # Skip if user already exists
        existing_user = db.query(User).filter(User.uid == uid).first()
        if existing_user:
            print(f"  User '{uid}' already exists, skipping.")
            continue

        # Create user
        user = User(
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
            uid=uid,
            pwd=hashed_password,
            email=email,
            role=UserRole.EMPLOYEE,
            account_type=AccountType.TEST,
            email_verified=True,
        )
        profile = Profile(
            created_at=datetime.now(timezone.utc),
            name=name,
            birthdate=date(1990, 1, 1),
            description=f"{department} 部門 - {role_name}",
        )
        user.profile = profile
        db.add(user)
        db.flush()

        # Create employee linked to user
        employee = Employee(
            created_at=datetime.now(timezone.utc),
            idno=f"EMP-{uid.upper()}",
            department=department,
            role_id=roles[role_name].id,
            user_id=user.id,
        )
        db.add(employee)
        db.flush()

        created_count += 1
        print(f"  Created employee: {uid} ({name}) - {department}/{role_name}")

    if created_count > 0:
        print(f"  Total: {created_count} employee(s) created (password: {DEFAULT_PASSWORD})")
    else:
        print("  All test employees already exist.")


def seed_database():
    """Main seed function."""
    print("\n=== Database Initialization ===\n")

    db = SessionLocal()
    try:
        print("[1/5] Creating authorities...")
        authorities = create_authorities(db)

        print("\n[2/5] Creating roles...")
        roles = create_roles(db, authorities)

        print("\n[3/5] Creating admin user...")
        create_admin_user(db)

        print("\n[4/5] Linking admin user to Admin role...")
        admin_user = db.query(User).filter(User.uid == ADMIN_USER["uid"]).first()
        existing_admin_emp = db.query(Employee).filter(Employee.user_id == admin_user.id).first()
        if not existing_admin_emp:
            admin_emp = Employee(
                created_at=datetime.now(timezone.utc),
                idno="EMP-ADMIN",
                department="IT",
                role_id=roles["Admin"].id,
                user_id=admin_user.id,
            )
            db.add(admin_emp)
            db.flush()
            print("  Created admin employee record.")
        else:
            print("  Admin employee record already exists, skipping.")

        print("\n[5/5] Creating test employees...")
        create_test_employees(db, roles)

        db.commit()
        print("\n=== Initialization complete ===\n")

    except Exception as e:
        db.rollback()
        print(f"\nError during initialization: {e}")
        raise
    finally:
        db.close()


def main():
    """Entry point for poetry script."""
    seed_database()


if __name__ == "__main__":
    main()
