from app.db import Base

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Uuid,
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

from uuid import UUID, uuid4
from enum import Enum

class Empolyee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    idno: Mapped[str] = mapped_column(String(32), nullable=False)
    department: Mapped[str] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(32))


    # profile: Mapped["Profile"] = relationship(
    #     back_populates="user",
    #     cascade="all, delete-orphan",
    #     lazy="selectin"
    # )

class EmployeeAuthority(Base):
    __tablename__ = "employee_authority"

    name: Mapped[str] = mapped_column()

class Authority(Base):
    __tablename__ = ""

    name: Mapped[str] = mapped_column()