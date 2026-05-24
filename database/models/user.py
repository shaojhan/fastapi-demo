from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db import Base
from app.domain.UserModel import AccountType, UserRole

if TYPE_CHECKING:
    from .employee import Employee


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    uid: Mapped[str] = mapped_column(String(32), unique=True)
    pwd: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.NORMAL, server_default='NORMAL')
    account_type: Mapped[AccountType] = mapped_column(SqlEnum(AccountType), default=AccountType.REAL, server_default='REAL')
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    github_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    line_user_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    profile: Mapped["Profile"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    employee: Mapped["Employee"] = relationship(
        "Employee",
        back_populates="user",
        uselist=False,
        lazy="selectin"
    )

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    name: Mapped[str] = mapped_column(String(64))
    birthdate: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship(
        back_populates="profile"
    )
