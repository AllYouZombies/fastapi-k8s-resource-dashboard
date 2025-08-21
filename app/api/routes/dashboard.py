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
    hide_incomplete: Optional[bool] = Query(True),
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

    # Get historical min/max data for all resources
    historical_stats = {}
    for resource in resources:
        key = f"{resource.pod_name}:{resource.container_name}:{resource.namespace}"
        if key not in historical_stats:
            # Get historical data for this pod/container
            hist_query = db.query(ResourceMetric).filter(
                ResourceMetric.pod_name == resource.pod_name,
                ResourceMetric.container_name == resource.container_name,
                ResourceMetric.namespace == resource.namespace
            )
            hist_data = hist_query.all()
            
            cpu_values = [h.cpu_usage_cores or 0 for h in hist_data]
            memory_values = [h.memory_usage_bytes or 0 for h in hist_data]
            
            historical_stats[key] = {
                "cpu_min": min(cpu_values) if cpu_values else 0,
                "cpu_max": max(cpu_values) if cpu_values else 0,
                "memory_min": min(memory_values) if memory_values else 0,
                "memory_max": max(memory_values) if memory_values else 0,
            }

    for resource in resources:
        key = f"{resource.pod_name}:{resource.container_name}:{resource.namespace}"
        hist_stats = historical_stats.get(key, {})
        
        # Calculate utilization percentages for current, min, max
        def calc_cpu_req_pct(cpu_val):
            return (cpu_val / resource.cpu_request_cores * 100) if resource.cpu_request_cores else 0
        
        def calc_cpu_limit_pct(cpu_val):
            return (cpu_val / resource.cpu_limit_cores * 100) if resource.cpu_limit_cores else 0
        
        def calc_mem_req_pct(mem_val):
            return (mem_val / resource.memory_request_bytes * 100) if resource.memory_request_bytes else 0
            
        def calc_mem_limit_pct(mem_val):
            return (mem_val / resource.memory_limit_bytes * 100) if resource.memory_limit_bytes else 0

        cpu_req_pct_current = calc_cpu_req_pct(resource.cpu_usage_cores or 0)
        cpu_req_pct_min = calc_cpu_req_pct(hist_stats.get("cpu_min", 0))
        cpu_req_pct_max = calc_cpu_req_pct(hist_stats.get("cpu_max", 0))
        
        cpu_limit_pct_current = calc_cpu_limit_pct(resource.cpu_usage_cores or 0)
        cpu_limit_pct_min = calc_cpu_limit_pct(hist_stats.get("cpu_min", 0))
        cpu_limit_pct_max = calc_cpu_limit_pct(hist_stats.get("cpu_max", 0))
        
        mem_req_pct_current = calc_mem_req_pct(resource.memory_usage_bytes or 0)
        mem_req_pct_min = calc_mem_req_pct(hist_stats.get("memory_min", 0))
        mem_req_pct_max = calc_mem_req_pct(hist_stats.get("memory_max", 0))
        
        mem_limit_pct_current = calc_mem_limit_pct(resource.memory_usage_bytes or 0)
        mem_limit_pct_min = calc_mem_limit_pct(hist_stats.get("memory_min", 0))
        mem_limit_pct_max = calc_mem_limit_pct(hist_stats.get("memory_max", 0))

        base_data = {
            "pod_name": resource.pod_name,
            "namespace": resource.namespace,
            "container_name": resource.container_name,
            "node_name": resource.node_name,
            "status": resource.pod_phase,
        }

        # Helper function to format min/current/max values
        def format_cpu_values(min_val, current_val, max_val):
            min_m = int(min_val * 1000) if min_val else 0
            current_m = int(current_val * 1000) if current_val else 0
            max_m = int(max_val * 1000) if max_val else 0
            return {
                "min": f"{min_m}m",
                "current": f"{current_m}m", 
                "max": f"{max_m}m",
                "display": f"{min_m}m {current_m}m {max_m}m"
            }
        
        def format_memory_values(min_val, current_val, max_val):
            min_mi = int(min_val / (1024 ** 2)) if min_val else 0
            current_mi = int(current_val / (1024 ** 2)) if current_val else 0
            max_mi = int(max_val / (1024 ** 2)) if max_val else 0
            return {
                "min": f"{min_mi}Mi",
                "current": f"{current_mi}Mi",
                "max": f"{max_mi}Mi", 
                "display": f"{min_mi}Mi {current_mi}Mi {max_mi}Mi"
            }
        
        def format_percentage_values(min_pct, current_pct, max_pct):
            return {
                "min": f"{min_pct:.1f}%" if min_pct is not None else "N/A",
                "current": f"{current_pct:.1f}%" if current_pct is not None else "N/A",
                "max": f"{max_pct:.1f}%" if max_pct is not None else "N/A",
                "display": f"{min_pct:.1f}% {current_pct:.1f}% {max_pct:.1f}%" if all(x is not None for x in [min_pct, current_pct, max_pct]) else "N/A"
            }

        # CPU requests vs usage (convert to millicores)
        cpu_actual_formatted = format_cpu_values(
            hist_stats.get("cpu_min", 0),
            resource.cpu_usage_cores or 0, 
            hist_stats.get("cpu_max", 0)
        )
        cpu_req_pct_formatted = format_percentage_values(
            cpu_req_pct_min, cpu_req_pct_current, cpu_req_pct_max
        )
        
        cpu_req_row = base_data.copy()
        cpu_req_row.update({
            "requested": (
                f"{resource.cpu_request_cores * 1000:.0f}m"
                if resource.cpu_request_cores
                else "Not set"
            ),
            "actual": cpu_actual_formatted["display"],
            "actual_current": cpu_actual_formatted["current"],
            "actual_min": cpu_actual_formatted["min"],
            "actual_max": cpu_actual_formatted["max"],
            "utilization_pct": cpu_req_pct_formatted["display"],
            "utilization_pct_current": cpu_req_pct_formatted["current"],
            "utilization_pct_min": cpu_req_pct_formatted["min"],
            "utilization_pct_max": cpu_req_pct_formatted["max"],
        })
        cpu_requests_data.append(cpu_req_row)

        # CPU limits vs usage (convert to millicores)
        cpu_limit_pct_formatted = format_percentage_values(
            cpu_limit_pct_min, cpu_limit_pct_current, cpu_limit_pct_max
        )
        
        cpu_limit_row = base_data.copy()
        cpu_limit_row.update({
            "limit": (
                f"{resource.cpu_limit_cores * 1000:.0f}m"
                if resource.cpu_limit_cores
                else "Not set"
            ),
            "actual": cpu_actual_formatted["display"],
            "actual_current": cpu_actual_formatted["current"],
            "actual_min": cpu_actual_formatted["min"],
            "actual_max": cpu_actual_formatted["max"],
            "utilization_pct": cpu_limit_pct_formatted["display"],
            "utilization_pct_current": cpu_limit_pct_formatted["current"],
            "utilization_pct_min": cpu_limit_pct_formatted["min"],
            "utilization_pct_max": cpu_limit_pct_formatted["max"],
        })
        cpu_limits_data.append(cpu_limit_row)

        # Memory requests vs usage
        memory_actual_formatted = format_memory_values(
            hist_stats.get("memory_min", 0),
            resource.memory_usage_bytes or 0,
            hist_stats.get("memory_max", 0)
        )
        mem_req_pct_formatted = format_percentage_values(
            mem_req_pct_min, mem_req_pct_current, mem_req_pct_max
        )
        
        mem_req_row = base_data.copy()
        mem_req_row.update({
            "requested": (
                f"{resource.memory_request_bytes // (1024 ** 2)}Mi"
                if resource.memory_request_bytes
                else "Not set"
            ),
            "actual": memory_actual_formatted["display"],
            "actual_current": memory_actual_formatted["current"],
            "actual_min": memory_actual_formatted["min"],
            "actual_max": memory_actual_formatted["max"],
            "utilization_pct": mem_req_pct_formatted["display"],
            "utilization_pct_current": mem_req_pct_formatted["current"],
            "utilization_pct_min": mem_req_pct_formatted["min"],
            "utilization_pct_max": mem_req_pct_formatted["max"],
        })
        memory_requests_data.append(mem_req_row)

        # Memory limits vs usage
        mem_limit_pct_formatted = format_percentage_values(
            mem_limit_pct_min, mem_limit_pct_current, mem_limit_pct_max
        )
        
        mem_limit_row = base_data.copy()
        mem_limit_row.update({
            "limit": (
                f"{resource.memory_limit_bytes // (1024 ** 2)}Mi"
                if resource.memory_limit_bytes
                else "Not set"
            ),
            "actual": memory_actual_formatted["display"],
            "actual_current": memory_actual_formatted["current"],
            "actual_min": memory_actual_formatted["min"],
            "actual_max": memory_actual_formatted["max"],
            "utilization_pct": mem_limit_pct_formatted["display"],
            "utilization_pct_current": mem_limit_pct_formatted["current"],
            "utilization_pct_min": mem_limit_pct_formatted["min"],
            "utilization_pct_max": mem_limit_pct_formatted["max"],
        })
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


@router.get("/api/recommendations/{pod_name}/{container_name}")
async def get_resource_recommendations(
        pod_name: str,
        container_name: str,
        namespace: Optional[str] = Query(None),
        db: Session = Depends(get_database_session)
):
    """API endpoint for resource recommendations based on historical data."""
    from sqlalchemy import func, and_
    
    # Build query for this specific pod/container
    query = db.query(ResourceMetric).filter(
        ResourceMetric.pod_name == pod_name,
        ResourceMetric.container_name == container_name
    )
    
    if namespace:
        query = query.filter(ResourceMetric.namespace == namespace)
    
    # Get all historical data for this pod/container
    historical_data = query.all()
    
    if not historical_data:
        return {"error": "No historical data found for this pod/container"}
    
    # Calculate min, max, current values
    cpu_values = [m.cpu_usage_cores or 0 for m in historical_data]
    memory_values = [m.memory_usage_bytes or 0 for m in historical_data]
    
    # Get latest record for current values and settings
    latest_record = max(historical_data, key=lambda x: x.timestamp)
    
    stats = {
        "cpu_min": min(cpu_values) if cpu_values else 0,
        "cpu_max": max(cpu_values) if cpu_values else 0,
        "cpu_current": latest_record.cpu_usage_cores or 0,
        "memory_min": min(memory_values) if memory_values else 0,
        "memory_max": max(memory_values) if memory_values else 0,
        "memory_current": latest_record.memory_usage_bytes or 0,
        "cpu_request": latest_record.cpu_request_cores or 0,
        "cpu_limit": latest_record.cpu_limit_cores or 0,
        "memory_request": latest_record.memory_request_bytes or 0,
        "memory_limit": latest_record.memory_limit_bytes or 0,
    }
    
    # Calculate recommendations based on max values (for limits)
    recommendations = calculate_resource_recommendations(
        current_cpu_cores=stats["cpu_current"],
        max_cpu_cores=stats["cpu_max"],
        current_memory_bytes=stats["memory_current"],
        max_memory_bytes=stats["memory_max"]
    )
    
    return {
        "pod_name": pod_name,
        "container_name": container_name,
        "namespace": latest_record.namespace,
        "node_name": latest_record.node_name,
        "status": latest_record.pod_phase,
        "current_usage": {
            "cpu_cores": stats["cpu_current"],
            "memory_bytes": stats["memory_current"],
            "cpu_millicores": int(stats["cpu_current"] * 1000),
            "memory_mi": int(stats["memory_current"] / (1024 * 1024))
        },
        "historical_stats": {
            "cpu": {
                "min": stats["cpu_min"],
                "max": stats["cpu_max"],
                "current": stats["cpu_current"]
            },
            "memory": {
                "min": stats["memory_min"],
                "max": stats["memory_max"],
                "current": stats["memory_current"]
            }
        },
        "current_settings": {
            "cpu_request": stats["cpu_request"],
            "cpu_limit": stats["cpu_limit"],
            "memory_request": stats["memory_request"],
            "memory_limit": stats["memory_limit"]
        },
        "recommendations": recommendations
    }


def calculate_resource_recommendations(current_cpu_cores: float, max_cpu_cores: float, 
                                     current_memory_bytes: int, max_memory_bytes: int):
    """Calculate resource recommendations based on current and max usage."""
    
    # Convert to more convenient units
    current_cpu_millicores = int(current_cpu_cores * 1000)
    max_cpu_millicores = int(max_cpu_cores * 1000)
    current_memory_mi = current_memory_bytes / (1024 * 1024)
    max_memory_mi = max_memory_bytes / (1024 * 1024)
    
    # CPU recommendations
    # Requests based on current usage
    if current_cpu_millicores < 50:
        cpu_request_millicores = 50  # Minimum 50m
    elif current_cpu_millicores <= 1000:
        # Round to nearest 50m increment
        cpu_request_millicores = ((current_cpu_millicores + 49) // 50) * 50
    else:
        # Round to nearest 100m increment for values above 1000m
        cpu_request_millicores = ((current_cpu_millicores + 99) // 100) * 100
    
    # Limits based on max usage - ensure max usage is within 80% of limit
    target_cpu_limit = max(max_cpu_millicores / 0.8, cpu_request_millicores * 1.25)
    if target_cpu_limit <= 1000:
        cpu_limit_millicores = int(((target_cpu_limit + 49) // 50) * 50)
    else:
        cpu_limit_millicores = int(((target_cpu_limit + 99) // 100) * 100)
    
    # Memory recommendations
    # Requests based on current usage
    if current_memory_mi < 10:
        memory_request = {"value": 64, "unit": "Mi"}
    elif current_memory_mi < 512:
        # Round up to 64Mi increments
        rounded = int(((current_memory_mi + 63) // 64) * 64)
        memory_request = {"value": rounded, "unit": "Mi"}
    elif current_memory_mi < 1000:
        # Round up to 128Mi increments
        rounded = int(((current_memory_mi + 127) // 128) * 128)
        memory_request = {"value": rounded, "unit": "Mi"}
    else:
        # Round up to 0.1Gi increments
        rounded_gi = round((current_memory_mi / 1024) * 10) / 10
        memory_request = {"value": rounded_gi, "unit": "Gi"}
    
    # Limits based on max usage - ensure max usage is within 80% of limit
    target_memory_mi = max(max_memory_mi / 0.8, current_memory_mi * 1.25)
    if target_memory_mi < 512:
        rounded = int(((target_memory_mi + 63) // 64) * 64)
        memory_limit = {"value": rounded, "unit": "Mi"}
    elif target_memory_mi < 1000:
        rounded = int(((target_memory_mi + 127) // 128) * 128)
        memory_limit = {"value": rounded, "unit": "Mi"}
    else:
        rounded_gi = round((target_memory_mi / 1024) * 10) / 10
        memory_limit = {"value": rounded_gi, "unit": "Gi"}
    
    return {
        "cpu": {
            "request": {
                "millicores": cpu_request_millicores,
                "cores": cpu_request_millicores / 1000.0
            },
            "limit": {
                "millicores": cpu_limit_millicores,
                "cores": cpu_limit_millicores / 1000.0
            }
        },
        "memory": {
            "request": memory_request,
            "limit": memory_limit
        },
        "yaml": generate_yaml_config(cpu_request_millicores, cpu_limit_millicores, memory_request, memory_limit),
        "rationale": {
            "cpu_request": f"Based on current usage of {current_cpu_millicores}m, rounded to appropriate increment",
            "cpu_limit": f"Based on max usage of {max_cpu_millicores}m with 25% headroom for spikes",
            "memory_request": f"Based on current usage of {int(current_memory_mi)}Mi, rounded to appropriate increment",
            "memory_limit": f"Based on max usage of {int(max_memory_mi)}Mi with 25% headroom for spikes"
        }
    }


def generate_yaml_config(cpu_request_millicores: int, cpu_limit_millicores: int, 
                        memory_request: dict, memory_limit: dict) -> str:
    """Generate YAML configuration for the recommendations."""
    return f"""resources:
  requests:
    cpu: "{cpu_request_millicores}m"
    memory: "{memory_request['value']}{memory_request['unit']}"
  limits:
    cpu: "{cpu_limit_millicores}m"
    memory: "{memory_limit['value']}{memory_limit['unit']}"
"""
