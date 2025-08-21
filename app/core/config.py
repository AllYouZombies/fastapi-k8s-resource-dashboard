from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Kubernetes Resource Monitor"
    debug: bool = False
    log_level: str = "INFO"

    # Kubernetes settings
    k8s_in_cluster: bool = False  # Default to false for easier local development
    k8s_config_path: Optional[str] = None
    k8s_context: Optional[str] = None  # Specific context to use
    excluded_namespaces: str = "kube-system,kube-public,kube-node-lease"

    # Prometheus settings
    prometheus_url: str = "http://localhost:9090"  # More generic default
    prometheus_timeout: int = 30

    # Database settings
    database_url: str = "sqlite:///./data/k8s_metrics.db"
    retention_days: int = 7  # More reasonable default for production

    # Scheduler settings
    collection_interval_minutes: int = 5
    enable_scheduler: bool = True

    # API settings
    cors_origins: str = "*"
    page_size: int = 20

    @property
    def excluded_namespaces_list(self):
        """Return excluded_namespaces as list"""
        return [ns.strip() for ns in self.excluded_namespaces.split(",") if ns.strip()]

    @property
    def cors_origins_list(self):
        """Return cors_origins as list"""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()
