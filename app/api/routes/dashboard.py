from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...core.config import get_settings
from ...core.dependencies import get_database_session
from ...models.database import ResourceMetric

router = APIRouter()
templates = Jinja2Templates(directory="app/static/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    namespace: Optional[str] = Query(None),
    sort_column: Optional[str] = Query(None),
    sort_direction: Optional[str] = Query("asc"),
    hide_incomplete: Optional[bool] = Query(False),
    db: Session = Depends(get_database_session),
):
    """Main dashboard page."""
    settings = get_settings()

    # Build query - exclude inactive pods
    query = db.query(ResourceMetric).filter(
        ResourceMetric.timestamp
        == db.query(func.max(ResourceMetric.timestamp)).scalar(),
        ResourceMetric.pod_phase.in_(["Running", "Pending", "Unknown"]) # Exclude Succeeded, Failed
    )

    if search:
        query = query.filter(ResourceMetric.pod_name.contains(search))

    if namespace:
        query = query.filter(ResourceMetric.namespace == namespace)

    if hide_incomplete:
        query = query.filter(
            ResourceMetric.cpu_request_cores.isnot(None),
            ResourceMetric.cpu_request_cores > 0,
            ResourceMetric.memory_request_bytes.isnot(None),
            ResourceMetric.memory_request_bytes > 0,
            ResourceMetric.cpu_limit_cores.isnot(None),
            ResourceMetric.cpu_limit_cores > 0,
            ResourceMetric.memory_limit_bytes.isnot(None),
            ResourceMetric.memory_limit_bytes > 0,
        )

    # Apply sorting
    if sort_column and sort_direction in ["asc", "desc"]:
        if sort_column == "utilization_pct":
            # Special handling for utilization percentage (CPU requests)
            cpu_utilization = ResourceMetric.cpu_usage_cores / func.nullif(ResourceMetric.cpu_request_cores, 0)
            if sort_direction == "desc":
                query = query.order_by(desc(cpu_utilization))
            else:
                query = query.order_by(cpu_utilization)
        else:
            sort_attr = getattr(ResourceMetric, sort_column, None)
            if sort_attr:
                if sort_direction == "desc":
                    query = query.order_by(desc(sort_attr))
                else:
                    query = query.order_by(sort_attr)

    # Get total count for pagination
    total_count = query.count()
    total_pages = (total_count + settings.page_size - 1) // settings.page_size

    # Apply pagination
    offset = (page - 1) * settings.page_size
    resources = query.offset(offset).limit(settings.page_size).all()

    # Get available namespaces for filter
    namespaces = db.query(ResourceMetric.namespace).distinct().all()
    namespaces = [ns[0] for ns in namespaces]

    # Prepare data for tables
    cpu_requests_data = []
    cpu_limits_data = []
    memory_requests_data = []
    memory_limits_data = []

    for resource in resources:
        # Calculate utilization percentages
        cpu_req_pct = (
            (resource.cpu_usage_cores / resource.cpu_request_cores * 100)
            if resource.cpu_request_cores
            else 0
        )
        cpu_limit_pct = (
            (resource.cpu_usage_cores / resource.cpu_limit_cores * 100)
            if resource.cpu_limit_cores
            else 0
        )
        mem_req_pct = (
            (resource.memory_usage_bytes / resource.memory_request_bytes * 100)
            if resource.memory_request_bytes
            else 0
        )
        mem_limit_pct = (
            (resource.memory_usage_bytes / resource.memory_limit_bytes * 100)
            if resource.memory_limit_bytes
            else 0
        )

        base_data = {
            "pod_name": resource.pod_name,
            "namespace": resource.namespace,
            "container_name": resource.container_name,
            "node_name": resource.node_name,
            "status": resource.pod_phase,
        }

        # CPU requests vs usage (convert to millicores)
        cpu_req_row = base_data.copy()
        cpu_req_row.update(
            {
                "requested": (
                    f"{resource.cpu_request_cores * 1000:.0f}m"
                    if resource.cpu_request_cores
                    else "Not set"
                ),
                "actual": (
                    f"{resource.cpu_usage_cores * 1000:.0f}m"
                    if resource.cpu_usage_cores
                    else "0m"
                ),
                "utilization_pct": f"{cpu_req_pct:.1f}%" if cpu_req_pct else "N/A",
            }
        )
        cpu_requests_data.append(cpu_req_row)

        # CPU limits vs usage (convert to millicores)
        cpu_limit_row = base_data.copy()
        cpu_limit_row.update(
            {
                "limit": (
                    f"{resource.cpu_limit_cores * 1000:.0f}m"
                    if resource.cpu_limit_cores
                    else "Not set"
                ),
                "actual": (
                    f"{resource.cpu_usage_cores * 1000:.0f}m"
                    if resource.cpu_usage_cores
                    else "0m"
                ),
                "utilization_pct": f"{cpu_limit_pct:.1f}%" if cpu_limit_pct else "N/A",
            }
        )
        cpu_limits_data.append(cpu_limit_row)

        # Memory requests vs usage
        mem_req_row = base_data.copy()
        mem_req_row.update(
            {
                "requested": (
                    f"{resource.memory_request_bytes // (1024 ** 2)}Mi"
                    if resource.memory_request_bytes
                    else "Not set"
                ),
                "actual": (
                    f"{resource.memory_usage_bytes // (1024 ** 2)}Mi"
                    if resource.memory_usage_bytes
                    else "0Mi"
                ),
                "utilization_pct": f"{mem_req_pct:.1f}%" if mem_req_pct else "N/A",
            }
        )
        memory_requests_data.append(mem_req_row)

        # Memory limits vs usage
        mem_limit_row = base_data.copy()
        mem_limit_row.update(
            {
                "limit": (
                    f"{resource.memory_limit_bytes // (1024 ** 2)}Mi"
                    if resource.memory_limit_bytes
                    else "Not set"
                ),
                "actual": (
                    f"{resource.memory_usage_bytes // (1024 ** 2)}Mi"
                    if resource.memory_usage_bytes
                    else "0Mi"
                ),
                "utilization_pct": f"{mem_limit_pct:.1f}%" if mem_limit_pct else "N/A",
            }
        )
        memory_limits_data.append(mem_limit_row)

    # Calculate summary statistics from ALL records (not just current page)
    all_query = db.query(ResourceMetric).filter(
        ResourceMetric.timestamp
        == db.query(func.max(ResourceMetric.timestamp)).scalar()
    )
    if search:
        all_query = all_query.filter(ResourceMetric.pod_name.contains(search))
    if namespace:
        all_query = all_query.filter(ResourceMetric.namespace == namespace)

    all_resources = all_query.all()

    total_cpu_requests = sum(r.cpu_request_cores or 0 for r in all_resources)
    total_cpu_limits = sum(r.cpu_limit_cores or 0 for r in all_resources)
    total_memory_requests = sum(r.memory_request_bytes or 0 for r in all_resources)
    total_memory_limits = sum(r.memory_limit_bytes or 0 for r in all_resources)
    total_cpu_usage = sum(r.cpu_usage_cores or 0 for r in all_resources)
    total_memory_usage = sum(r.memory_usage_bytes or 0 for r in all_resources)

    cpu_requests_underutilization = max(0, total_cpu_requests - total_cpu_usage)
    cpu_limits_underutilization = max(0, total_cpu_limits - total_cpu_usage)
    memory_requests_underutilization = max(
        0, total_memory_requests - total_memory_usage
    )
    memory_limits_underutilization = max(0, total_memory_limits - total_memory_usage)

    summary_stats = {
        "total_cpu_requests": total_cpu_requests,
        "total_cpu_limits": total_cpu_limits,
        "total_memory_requests_gb": total_memory_requests / (1024**3),
        "total_memory_limits_gb": total_memory_limits / (1024**3),
        "total_cpu_usage": total_cpu_usage,
        "total_memory_usage_gb": total_memory_usage / (1024**3),
        "cpu_requests_underutilization": cpu_requests_underutilization,
        "cpu_limits_underutilization": cpu_limits_underutilization,
        "memory_requests_underutilization_gb": memory_requests_underutilization
        / (1024**3),
        "memory_limits_underutilization_gb": memory_limits_underutilization / (1024**3),
        "total_containers": len(all_resources),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "cpu_requests_data": cpu_requests_data,
            "cpu_limits_data": cpu_limits_data,
            "memory_requests_data": memory_requests_data,
            "memory_limits_data": memory_limits_data,
            "summary_stats": summary_stats,
            "namespaces": namespaces,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "search": search or "",
            "selected_namespace": namespace or "all",
            "page_size": settings.page_size,
            "sort_column": sort_column or "",
            "sort_direction": sort_direction,
            "hide_incomplete": hide_incomplete,
        },
    )


@router.get("/api/summary")
async def get_summary_stats(
        search: Optional[str] = Query(None),
        namespace: Optional[str] = Query(None),
        db: Session = Depends(get_database_session)
):
    """API endpoint for summary statistics."""
    # Get filtered data for summary stats - exclude inactive pods
    all_query = db.query(ResourceMetric).filter(
        ResourceMetric.timestamp == db.query(func.max(ResourceMetric.timestamp)).scalar(),
        ResourceMetric.pod_phase.in_(["Running", "Pending", "Unknown"]) # Exclude Succeeded, Failed
    )
    if search:
        all_query = all_query.filter(ResourceMetric.pod_name.contains(search))
    if namespace:
        all_query = all_query.filter(ResourceMetric.namespace == namespace)
    
    all_resources = all_query.all()
    
    total_cpu_requests = sum(r.cpu_request_cores or 0 for r in all_resources)
    total_cpu_limits = sum(r.cpu_limit_cores or 0 for r in all_resources)
    total_memory_requests = sum(r.memory_request_bytes or 0 for r in all_resources)
    total_memory_limits = sum(r.memory_limit_bytes or 0 for r in all_resources)
    total_cpu_usage = sum(r.cpu_usage_cores or 0 for r in all_resources)
    total_memory_usage = sum(r.memory_usage_bytes or 0 for r in all_resources)
    
    cpu_requests_underutilization = max(0, total_cpu_requests - total_cpu_usage)
    cpu_limits_underutilization = max(0, total_cpu_limits - total_cpu_usage)
    memory_requests_underutilization = max(0, total_memory_requests - total_memory_usage)
    memory_limits_underutilization = max(0, total_memory_limits - total_memory_usage)
    
    return {
        "total_cpu_requests": total_cpu_requests,
        "total_cpu_limits": total_cpu_limits,
        "total_memory_requests_gb": total_memory_requests / (1024**3),
        "total_memory_limits_gb": total_memory_limits / (1024**3),
        "total_cpu_usage": total_cpu_usage,
        "total_memory_usage_gb": total_memory_usage / (1024**3),
        "cpu_requests_underutilization": cpu_requests_underutilization,
        "cpu_limits_underutilization": cpu_limits_underutilization,
        "memory_requests_underutilization_gb": memory_requests_underutilization / (1024**3),
        "memory_limits_underutilization_gb": memory_limits_underutilization / (1024**3),
        "total_containers": len(all_resources)
    }


@router.get("/api/chart-data")
async def get_chart_data(
        hours: int = Query(24, ge=1, le=168),  # Max 1 week
        db: Session = Depends(get_database_session)
):
    """API endpoint for chart data with historical data."""
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    # Get metrics from the last N hours - exclude inactive pods
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    recent_metrics = (
        db.query(ResourceMetric)
        .filter(
            ResourceMetric.timestamp >= cutoff_time,
            ResourceMetric.pod_phase.in_(["Running", "Pending", "Unknown"]) # Exclude Succeeded, Failed
        )
        .order_by(ResourceMetric.timestamp)
        .all()
    )

    # Group by timestamp (5-minute intervals)
    time_groups = defaultdict(list)
    
    for metric in recent_metrics:
        # Round to 5-minute intervals
        minute = (metric.timestamp.minute // 5) * 5
        time_key = metric.timestamp.replace(minute=minute, second=0, microsecond=0)
        time_groups[time_key].append(metric)

    # Calculate totals for percentage calculations
    if recent_metrics:
        latest_timestamp = max(m.timestamp for m in recent_metrics)
        latest_metrics = [m for m in recent_metrics if m.timestamp == latest_timestamp]
        total_cpu_requests = sum(m.cpu_request_cores or 0 for m in latest_metrics)
        total_cpu_limits = sum(m.cpu_limit_cores or 0 for m in latest_metrics)
        total_memory_requests = sum(m.memory_request_bytes or 0 for m in latest_metrics)
        total_memory_limits = sum(m.memory_limit_bytes or 0 for m in latest_metrics)
    else:
        total_cpu_requests = total_cpu_limits = total_memory_requests = total_memory_limits = 1

    timestamps = []
    cpu_usage_absolute = []
    cpu_usage_percentage_requests = []
    cpu_usage_percentage_limits = []
    memory_usage_absolute = []
    memory_usage_percentage_requests = []
    memory_usage_percentage_limits = []

    for time_key in sorted(time_groups.keys()):
        metrics = time_groups[time_key]
        total_cpu = sum(m.cpu_usage_cores or 0 for m in metrics)
        total_memory = sum(m.memory_usage_bytes or 0 for m in metrics)
        
        # Calculate percentages
        cpu_pct_requests = (total_cpu / total_cpu_requests * 100) if total_cpu_requests else 0
        cpu_pct_limits = (total_cpu / total_cpu_limits * 100) if total_cpu_limits else 0
        memory_pct_requests = (total_memory / total_memory_requests * 100) if total_memory_requests else 0
        memory_pct_limits = (total_memory / total_memory_limits * 100) if total_memory_limits else 0

        timestamps.append(time_key.strftime("%H:%M"))
        cpu_usage_absolute.append(round(total_cpu, 3))
        cpu_usage_percentage_requests.append(round(cpu_pct_requests, 1))
        cpu_usage_percentage_limits.append(round(cpu_pct_limits, 1))
        memory_usage_absolute.append(round(total_memory / (1024**3), 2))  # GB
        memory_usage_percentage_requests.append(round(memory_pct_requests, 1))
        memory_usage_percentage_limits.append(round(memory_pct_limits, 1))

    return {
        "timestamps": timestamps,
        "cpu_usage_absolute": cpu_usage_absolute,
        "cpu_usage_percentage_requests": cpu_usage_percentage_requests,
        "cpu_usage_percentage_limits": cpu_usage_percentage_limits,
        "memory_usage_absolute": memory_usage_absolute,
        "memory_usage_percentage_requests": memory_usage_percentage_requests,
        "memory_usage_percentage_limits": memory_usage_percentage_limits,
    }


@router.get("/api/table/cpu-requests")
async def get_cpu_requests_table(
        page: int = Query(1, ge=1),
        search: Optional[str] = Query(None),
        namespace: Optional[str] = Query(None),
        sort_column: Optional[str] = Query(None),
        sort_direction: Optional[str] = Query("asc"),
        db: Session = Depends(get_database_session)
):
    """API endpoint for CPU requests table data."""
    settings = get_settings()
    
    # Build query
    query = db.query(ResourceMetric).filter(
        ResourceMetric.timestamp == db.query(func.max(ResourceMetric.timestamp)).scalar()
    )

    if search:
        query = query.filter(ResourceMetric.pod_name.contains(search))
    if namespace:
        query = query.filter(ResourceMetric.namespace == namespace)

    # Apply sorting
    if sort_column and sort_direction in ["asc", "desc"]:
        sort_attr = getattr(ResourceMetric, sort_column, None)
        if sort_attr:
            if sort_direction == "desc":
                query = query.order_by(desc(sort_attr))
            else:
                query = query.order_by(sort_attr)

    # Get total count and pagination
    total_count = query.count()
    total_pages = (total_count + settings.page_size - 1) // settings.page_size
    offset = (page - 1) * settings.page_size
    resources = query.offset(offset).limit(settings.page_size).all()

    # Prepare table data
    table_data = []
    for resource in resources:
        cpu_req_pct = (
            (resource.cpu_usage_cores / resource.cpu_request_cores * 100)
            if resource.cpu_request_cores
            else 0
        )
        
        table_data.append({
            "pod_name": resource.pod_name,
            "namespace": resource.namespace,
            "container_name": resource.container_name,
            "node_name": resource.node_name,
            "status": resource.pod_phase,
            "requested": f"{resource.cpu_request_cores * 1000:.0f}m" if resource.cpu_request_cores else "Not set",
            "actual": f"{resource.cpu_usage_cores * 1000:.0f}m" if resource.cpu_usage_cores else "0m",
            "utilization_pct": f"{cpu_req_pct:.1f}%" if cpu_req_pct else "N/A"
        })

    return {
        "data": table_data,
        "total_count": total_count,
        "current_page": page,
        "total_pages": total_pages
    }
