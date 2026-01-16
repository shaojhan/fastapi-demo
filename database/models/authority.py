from app.db import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

class Authority(Base):
    __tablename__ = "authorities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=True)