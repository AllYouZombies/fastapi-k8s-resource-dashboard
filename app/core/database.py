import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings
from ..models.database import Base

settings = get_settings()

# Create directory for SQLite database if needed
if "sqlite" in settings.database_url:
    # Extract path from sqlite URL (handle both sqlite:/// and sqlite://// formats)
    db_path = settings.database_url.replace("sqlite:////", "/").replace("sqlite:///", "")
    if not db_path.startswith("/"):
        db_path = os.path.join(os.getcwd(), db_path)
    
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        try:
            Path(db_dir).mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # If we can't create the directory, try using /tmp as fallback
            import tempfile
            db_path = os.path.join(tempfile.gettempdir(), "k8s_metrics.db")
            settings.database_url = f"sqlite:///{db_path}"

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