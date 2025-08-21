from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ResourceMetricBase(BaseModel):
    timestamp: datetime
    namespace: str
    pod_name: str
    container_name: Optional[str] = None
    node_name: Optional[str] = None
    pod_phase: Optional[str] = None
    cpu_request_cores: Optional[float] = None
    memory_request_bytes: Optional[int] = None
    cpu_limit_cores: Optional[float] = None
    memory_limit_bytes: Optional[int] = None
    cpu_usage_cores: Optional[float] = None
    memory_usage_bytes: Optional[int] = None


class ResourceMetricResponse(ResourceMetricBase):
    id: int

    class Config:
        from_attributes = True


class ResourceSummaryBase(BaseModel):
    timestamp: datetime
    namespace: str
    total_pods: int = 0
    total_cpu_requests: float = 0.0
    total_memory_requests: int = 0
    total_cpu_limits: float = 0.0
    total_memory_limits: int = 0
    total_cpu_usage: float = 0.0
    total_memory_usage: int = 0


class ResourceSummaryResponse(ResourceSummaryBase):
    id: int

    class Config:
        from_attributes = True


class MetricsResponse(BaseModel):
    metrics: List[ResourceMetricResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class ChartDataResponse(BaseModel):
    timestamps: List[str]
    cpu_utilization: List[float]
    memory_utilization: List[float]


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    database_status: str
    kubernetes_status: str
    prometheus_status: str
