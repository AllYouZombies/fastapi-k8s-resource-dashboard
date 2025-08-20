from fastapi import APIRouter, Request, Query, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional
from ...core.dependencies import get_database_session
from ...models.database import ResourceMetric
from ...core.config import get_settings
import json

router = APIRouter()
templates = Jinja2Templates(directory="app/static/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_home(
        request: Request,
        page: int = Query(1, ge=1),
        search: Optional[str] = Query(None),
        namespace: Optional[str] = Query(None),
        db: Session = Depends(get_database_session)
):
    """Main dashboard page."""
    settings = get_settings()

    # Build query
    query = db.query(ResourceMetric).filter(
        ResourceMetric.timestamp == db.query(func.max(ResourceMetric.timestamp)).scalar()
    )

    if search:
        query = query.filter(ResourceMetric.pod_name.contains(search))

    if namespace:
        query = query.filter(ResourceMetric.namespace == namespace)

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
        cpu_req_pct = (resource.cpu_usage_cores / resource.cpu_request_cores * 100) if resource.cpu_request_cores else 0
        cpu_limit_pct = (resource.cpu_usage_cores / resource.cpu_limit_cores * 100) if resource.cpu_limit_cores else 0
        mem_req_pct = (
                    resource.memory_usage_bytes / resource.memory_request_bytes * 100) if resource.memory_request_bytes else 0
        mem_limit_pct = (
                    resource.memory_usage_bytes / resource.memory_limit_bytes * 100) if resource.memory_limit_bytes else 0

        base_data = {
            'pod_name': resource.pod_name,
            'namespace': resource.namespace,
            'container_name': resource.container_name,
            'node_name': resource.node_name,
            'status': resource.pod_phase
        }

        # CPU requests vs usage
        cpu_req_row = base_data.copy()
        cpu_req_row.update({
            'requested': f"{resource.cpu_request_cores:.2f}" if resource.cpu_request_cores else "Not set",
            'actual': f"{resource.cpu_usage_cores:.2f}" if resource.cpu_usage_cores else "0.00",
            'utilization_pct': f"{cpu_req_pct:.1f}%" if cpu_req_pct else "N/A"
        })
        cpu_requests_data.append(cpu_req_row)

        # CPU limits vs usage
        cpu_limit_row = base_data.copy()
        cpu_limit_row.update({
            'limit': f"{resource.cpu_limit_cores:.2f}" if resource.cpu_limit_cores else "Not set",
            'actual': f"{resource.cpu_usage_cores:.2f}" if resource.cpu_usage_cores else "0.00",
            'utilization_pct': f"{cpu_limit_pct:.1f}%" if cpu_limit_pct else "N/A"
        })
        cpu_limits_data.append(cpu_limit_row)

        # Memory requests vs usage
        mem_req_row = base_data.copy()
        mem_req_row.update({
            'requested': f"{resource.memory_request_bytes // (1024 ** 2)}Mi" if resource.memory_request_bytes else "Not set",
            'actual': f"{resource.memory_usage_bytes // (1024 ** 2)}Mi" if resource.memory_usage_bytes else "0Mi",
            'utilization_pct': f"{mem_req_pct:.1f}%" if mem_req_pct else "N/A"
        })
        memory_requests_data.append(mem_req_row)

        # Memory limits vs usage
        mem_limit_row = base_data.copy()
        mem_limit_row.update({
            'limit': f"{resource.memory_limit_bytes // (1024 ** 2)}Mi" if resource.memory_limit_bytes else "Not set",
            'actual': f"{resource.memory_usage_bytes // (1024 ** 2)}Mi" if resource.memory_usage_bytes else "0Mi",
            'utilization_pct': f"{mem_limit_pct:.1f}%" if mem_limit_pct else "N/A"
        })
        memory_limits_data.append(mem_limit_row)

    # Calculate summary statistics
    summary_stats = {
        'total_pods': len(set(r.pod_name for r in resources)),
        'total_containers': len(resources),
        'running_pods': len([r for r in resources if r.pod_phase == 'Running']),
        'avg_cpu_usage': sum(r.cpu_usage_cores or 0 for r in resources) / len(resources) if resources else 0,
        'avg_memory_usage': sum(r.memory_usage_bytes or 0 for r in resources) / len(resources) if resources else 0
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
            "page_size": settings.page_size
        }
    )


@router.get("/api/chart-data")
async def get_chart_data(db: Session = Depends(get_database_session)):
    """API endpoint for chart data."""
    # Get recent metrics for charts
    recent_metrics = db.query(ResourceMetric) \
        .order_by(desc(ResourceMetric.timestamp)) \
        .limit(100) \
        .all()

    # Aggregate data for charts
    chart_data = {
        'cpu_utilization': [],
        'memory_utilization': [],
        'timestamps': []
    }

    # Group by timestamp and calculate averages
    from collections import defaultdict
    time_groups = defaultdict(list)

    for metric in recent_metrics:
        time_key = metric.timestamp.strftime('%H:%M')
        time_groups[time_key].append(metric)

    for time_key in sorted(time_groups.keys()):
        metrics = time_groups[time_key]
        avg_cpu = sum(m.cpu_usage_cores or 0 for m in metrics) / len(metrics)
        avg_memory = sum(m.memory_usage_bytes or 0 for m in metrics) / len(metrics) / (1024 ** 2)  # Convert to MB

        chart_data['timestamps'].append(time_key)
        chart_data['cpu_utilization'].append(round(avg_cpu, 3))
        chart_data['memory_utilization'].append(round(avg_memory, 1))

    return chart_data