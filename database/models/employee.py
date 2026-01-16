from app.db import Base

from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import (
    relationship,
    Mapped,
    mapped_column,
)

if TYPE_CHECKING:
    from .role import Role

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    idno: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(32))
    
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=True)
    role: Mapped["Role"] = relationship("Role", back_populates="employees", lazy="selectin")
