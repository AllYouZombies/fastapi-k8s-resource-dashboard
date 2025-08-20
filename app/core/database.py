import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings
from ..models.database import Base

settings = get_settings()

# Create directory for SQLite database if needed
if "sqlite" in settings.database_url:
    db_path = settings.database_url.replace("sqlite:///", "")
    if not db_path.startswith("/"):
        db_path = os.path.join(os.getcwd(), db_path)
    Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()