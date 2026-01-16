from app.db import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Table, Column, ForeignKey

role_authority = Table(
    "role_authority",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("authority_id", ForeignKey("authorities.id"), primary_key=True),
)

