from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db
from .config import get_settings, Settings


def get_settings_dependency() -> Settings:
    """Dependency to get application settings"""
    return get_settings()


def get_database_session(db: Session = Depends(get_db)) -> Session:
    """Dependency to get database session"""
    return db