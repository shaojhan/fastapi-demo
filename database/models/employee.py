from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db import Base

if TYPE_CHECKING:
    from .role import Role
    from .user import User

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    idno: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(32))

    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    role: Mapped["Role"] = relationship("Role", back_populates="employees", lazy="selectin")

    user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    user: Mapped["User"] = relationship("User", back_populates="employee", lazy="selectin")
