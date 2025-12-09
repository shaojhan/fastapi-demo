from app.database import Base

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    DateTime,
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

from app.router.schemas.UserSchema import UserEnum


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now())

    uid: Mapped[str] = mapped_column(String(32), unique=True)
    pwd: Mapped[str] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(String(32))
    role: Mapped[UserEnum] = mapped_column(SqlEnum(UserEnum), default=UserEnum.NORMAL, server_default='NORMAL')
    
    profile: Mapped["Profile"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
#     session: Mapped[List["Session"]] = relationship(
#         back_populates="",
#         cascade="all, delete-orphan",
#         lazy="selectin"
#     )

class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    name: Mapped[str] = mapped_column(String(64))
    age: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship(
        back_populates="profile"
    )

# class Session(Base):
#     __tablename__ = "sessions"

#     id: Mapped[str] = mapped_column(String(32))
#     expire_at: Mapped[datetime] = mapped_column(DateTime)

#     user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
#     user: Mapped["User"] = relationship(
#         back_populates="session"
#     )