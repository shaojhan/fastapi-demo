from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

engine_kwargs: dict = {"echo": settings.SQL_ECHO, "pool_pre_ping": True}
# SQLite (used in tests) doesn't support pool sizing args; only apply for real DBs.
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
    )
if settings.DATABASE_URL.startswith("mysql"):
    engine_kwargs["pool_recycle"] = 3600
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

class Base(DeclarativeBase):
    pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

