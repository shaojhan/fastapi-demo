from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

engine_kwargs = {"echo": settings.SQL_ECHO, "pool_pre_ping": True}
if settings.DATABASE_URL.startswith("mysql"):
    engine_kwargs["pool_recycle"] = 3600
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

class Base(DeclarativeBase):
    pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

