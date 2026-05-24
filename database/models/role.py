from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

from .association import role_authority

if TYPE_CHECKING:
    from .authority import Authority
    from .employee import Employee


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    authorities: Mapped[list["Authority"]] = relationship("Authority", secondary=role_authority, lazy="selectin")
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="role")