from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Kubernetes Resource Monitor"
    debug: bool = False
    log_level: str = "INFO"

    # Kubernetes settings
    k8s_in_cluster: bool = False  # Default to false for easier local development
    k8s_config_path: Optional[str] = None
    excluded_namespaces: List[str] = ["kube-system", "kube-public", "kube-node-lease"]

    # Prometheus settings
    prometheus_url: str = "http://localhost:9090"  # More generic default
    prometheus_timeout: int = 30

    # Database settings
    database_url: str = "sqlite:///./k8s_metrics.db"
    retention_days: int = 7  # More reasonable default for production

    # Scheduler settings
    collection_interval_minutes: int = 5
    enable_scheduler: bool = True

    # API settings
    cors_origins: List[str] = ["*"]
    page_size: int = 20

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()