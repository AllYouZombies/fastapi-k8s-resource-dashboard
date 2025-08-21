from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...core.dependencies import get_database_session, get_settings_dependency
from ...models.database import ResourceMetric, ResourceSummary
from ...models.schemas import (
    ChartDataResponse,
    MetricsResponse,
    ResourceMetricResponse,
    ResourceSummaryResponse,
)

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    namespace: Optional[str] = Query(None),
    db: Session = Depends(get_database_session),
):
    """Get paginated resource metrics with optional filtering"""
    settings = get_settings_dependency()

    # Build base query for latest metrics - exclude excluded namespaces
    query = db.query(ResourceMetric).filter(
        ResourceMetric.timestamp
        == db.query(func.max(ResourceMetric.timestamp)).scalar(),
        ~ResourceMetric.namespace.in_(
            settings.excluded_namespaces_list
        ),  # Exclude excluded namespaces
    )

    # Apply filters
    if search:
        query = query.filter(ResourceMetric.pod_name.contains(search))

    if namespace:
        query = query.filter(ResourceMetric.namespace == namespace)

    # Get total count
    total_count = query.count()

    # Calculate pagination
    total_pages = (total_count + page_size - 1) // page_size
    offset = (page - 1) * page_size

    # Get paginated results
    metrics = query.offset(offset).limit(page_size).all()

    # Convert to response models
    metric_responses = [ResourceMetricResponse.from_orm(metric) for metric in metrics]

    return MetricsResponse(
        metrics=metric_responses,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/chart-data", response_model=ChartDataResponse)
async def get_chart_data(
    hours: int = Query(24, ge=1, le=24), db: Session = Depends(get_database_session)
):
    """Get chart data for the last N hours"""
    settings = get_settings_dependency()

    # Get recent metrics for charts - exclude excluded namespaces
    recent_metrics = (
        db.query(ResourceMetric)
        .filter(
            ~ResourceMetric.namespace.in_(settings.excluded_namespaces_list)
        )  # Exclude excluded namespaces
        .order_by(desc(ResourceMetric.timestamp))
        .limit(hours * 12)
        .all()
    )  # 12 points per hour (every 5 minutes)

    # Group by timestamp and calculate averages
    from collections import defaultdict

    time_groups = defaultdict(list)

    for metric in recent_metrics:
        time_key = metric.timestamp.strftime("%H:%M")
        time_groups[time_key].append(metric)

    timestamps = []
    cpu_utilization = []
    memory_utilization = []

    for time_key in sorted(time_groups.keys()):
        metrics = time_groups[time_key]
        avg_cpu = (
            sum(m.cpu_usage_cores or 0 for m in metrics) / len(metrics)
            if metrics
            else 0
        )
        avg_memory = (
            sum(m.memory_usage_bytes or 0 for m in metrics) / len(metrics) / (1024**2)
            if metrics
            else 0
        )  # Convert to MB

        timestamps.append(time_key)
        cpu_utilization.append(round(avg_cpu, 3))
        memory_utilization.append(round(avg_memory, 1))

    return ChartDataResponse(
        timestamps=timestamps,
        cpu_utilization=cpu_utilization,
        memory_utilization=memory_utilization,
    )


@router.get("/namespaces")
async def get_namespaces(db: Session = Depends(get_database_session)) -> List[str]:
    """Get all available namespaces (excluding excluded namespaces)"""
    settings = get_settings_dependency()

    namespaces = (
        db.query(ResourceMetric.namespace)
        .filter(
            ~ResourceMetric.namespace.in_(
                settings.excluded_namespaces_list
            )  # Exclude excluded namespaces
        )
        .distinct()
        .all()
    )
    return [ns[0] for ns in namespaces if ns[0]]


@router.get("/summary", response_model=List[ResourceSummaryResponse])
async def get_summary(
    namespace: Optional[str] = Query(None), db: Session = Depends(get_database_session)
):
    """Get resource summary by namespace"""
    query = db.query(ResourceSummary).filter(
        ResourceSummary.timestamp
        == db.query(func.max(ResourceSummary.timestamp)).scalar()
    )

    if namespace:
        query = query.filter(ResourceSummary.namespace == namespace)

    summaries = query.all()
    return [ResourceSummaryResponse.from_orm(summary) for summary in summaries]


@router.post("/collect")
async def trigger_collection():
    """Manually trigger resource collection (for testing)"""
    from ...services.collector_service import ResourceCollectorService

    try:
        collector = ResourceCollectorService()
        await collector.initialize()
        await collector.collect_and_store_metrics()
        await collector.cleanup()

        return {"status": "success", "message": "Collection completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
