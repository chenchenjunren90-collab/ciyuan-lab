"""Database engine and session construction without import-time connections."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create the shared SQLAlchemy engine for PostgreSQL."""

    return create_engine(database_url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build sessions with explicit transaction boundaries in repositories."""

    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
