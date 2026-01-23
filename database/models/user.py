from app.db import Base

from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Uuid,
    String,
    DateTime,
    Date,
    Enum as SqlEnum,
    Integer,
    Boolean,
    func,
    ForeignKey
)
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
)

from uuid import UUID, uuid4
from enum import Enum
from app.domain.UserModel import UserRole

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    uid: Mapped[str] = mapped_column(String(32), unique=True)
    pwd: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.NORMAL, server_default='NORMAL')
    
    profile: Mapped["Profile"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
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
    
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship(
        back_populates="profile"
    )
