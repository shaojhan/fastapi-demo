from typing import List, TYPE_CHECKING
from app.db import Base
from sqlalchemy import Integer, String, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .association import role_authority

if TYPE_CHECKING:
    from .employee import Employee
    from .authority import Authority


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    authorities: Mapped[List["Authority"]] = relationship("Authority", secondary=role_authority, lazy="selectin")
    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="role")