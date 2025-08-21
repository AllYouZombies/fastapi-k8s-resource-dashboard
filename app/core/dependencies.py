from fastapi import Depends
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db


def get_settings_dependency() -> Settings:
    """Dependency to get application settings"""
    return get_settings()


def get_database_session(db: Session = Depends(get_db)) -> Session:
    """Dependency to get database session"""
    return db
