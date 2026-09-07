from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is missing. Check backend/.env."
    )


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Creates one database session for an API request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()