"""Database session management for seeding operations.

Provides SQLAlchemy session management with proper cleanup and error handling.
Configured for SQLite development database.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_session(database_url: str) -> Generator[Session, None, None]:
    """
    Create a database session context manager.

    Args:
        database_url: SQLAlchemy database URL (e.g., "sqlite:///./sostenki.db")

    Yields:
        SQLAlchemy Session for database operations

    Example:
        ```python
        for session in create_session("sqlite:///./sostenki.db"):
            users = session.query(User).all()
        ```
    """
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
