"""
Database seed script for initial data.

Usage: poetry run db-init

This script will:
1. Create common authorities (READ, WRITE, DELETE, APPROVE, EXPORT, ADMIN)
2. Create admin role with all authorities
3. Create admin user account

The script is idempotent - running it multiple times will not create duplicates.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.UserModel import UserRole
from database.models.user import User, Profile
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


def create_admin_role(db: Session, authorities: list[Authority]) -> Role:
    """Create admin role with all authorities."""
    existing = db.query(Role).filter(Role.name == "Admin").first()
    if existing:
        print("  Admin role already exists, updating authorities.")
        existing.authorities = authorities
        db.flush()
        return existing

    admin_role = Role(name="Admin", level=99)
    admin_role.authorities = authorities
    db.add(admin_role)
    db.flush()
    print("  Created admin role with all authorities.")
    return admin_role


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


def seed_database():
    """Main seed function."""
    print("\n=== Database Initialization ===\n")

    db = SessionLocal()
    try:
        print("[1/3] Creating authorities...")
        authorities = create_authorities(db)

        print("\n[2/3] Creating admin role...")
        create_admin_role(db, authorities)

        print("\n[3/3] Creating admin user...")
        create_admin_user(db)

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
