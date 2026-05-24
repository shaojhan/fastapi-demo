from sqlalchemy import Column, ForeignKey, Table

from app.db import Base

role_authority = Table(
    "role_authority",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("authority_id", ForeignKey("authorities.id"), primary_key=True),
)

