from sqlalchemy import Column, Integer, Float, String, DateTime, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class ResourceMetric(Base):
    __tablename__ = 'resource_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    namespace = Column(String(63), nullable=False, index=True)
    pod_name = Column(String(253), nullable=False, index=True)
    container_name = Column(String(253), nullable=True)
    node_name = Column(String(253), nullable=True)

    # Resource requests and limits
    cpu_request_cores = Column(Float, nullable=True)
    memory_request_bytes = Column(Integer, nullable=True)
    cpu_limit_cores = Column(Float, nullable=True)
    memory_limit_bytes = Column(Integer, nullable=True)

    # Actual usage from Prometheus
    cpu_usage_cores = Column(Float, nullable=True)
    memory_usage_bytes = Column(Integer, nullable=True)

    # Status information
    pod_phase = Column(String(20), nullable=True)

    # Composite indexes for optimal query performance
    __table_args__ = (
        Index('idx_time_pod', 'timestamp', 'pod_name'),
        Index('idx_time_namespace', 'timestamp', 'namespace'),
        Index('idx_pod_time_desc', 'pod_name', 'timestamp'),
    )


# Separate table for summary data
class ResourceSummary(Base):
    __tablename__ = 'resource_summaries'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    namespace = Column(String(63), nullable=False)

    total_pods = Column(Integer, default=0)
    total_cpu_requests = Column(Float, default=0.0)
    total_memory_requests = Column(Integer, default=0)
    total_cpu_limits = Column(Float, default=0.0)
    total_memory_limits = Column(Integer, default=0)
    total_cpu_usage = Column(Float, default=0.0)
    total_memory_usage = Column(Integer, default=0)