import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...core.dependencies import get_database_session
from ...models.schemas import HealthCheckResponse
from ...services.kubernetes_service import KubernetesService
from ...services.prometheus_service import PrometheusService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_database_session)):
    """Health check endpoint for Kubernetes probes"""

    # Check database connectivity
    database_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_status = "unhealthy"

    # Check Kubernetes API connectivity
    kubernetes_status = "healthy"
    try:
        k8s_service = KubernetesService()
        await k8s_service.initialize()
        # Try to list pods to verify connectivity
        await k8s_service.get_all_pods()
        await k8s_service.close()
    except Exception as e:
        logger.error(f"Kubernetes health check failed: {e}")
        kubernetes_status = "unhealthy"

    # Check Prometheus connectivity
    prometheus_status = "healthy"
    try:
        async with PrometheusService() as prom_service:
            # Simple query to check connectivity
            await prom_service.query_prometheus("up")
    except Exception as e:
        logger.error(f"Prometheus health check failed: {e}")
        prometheus_status = "unhealthy"

    # Overall status
    overall_status = (
        "healthy"
        if all(
            [
                database_status == "healthy",
                kubernetes_status == "healthy",
                prometheus_status == "healthy",
            ]
        )
        else "unhealthy"
    )

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        database_status=database_status,
        kubernetes_status=kubernetes_status,
        prometheus_status=prometheus_status,
    )


@router.get("/liveness")
async def liveness_probe():
    """Simple liveness probe for Kubernetes"""
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/readiness")
async def readiness_probe(db: Session = Depends(get_database_session)):
    """Readiness probe - checks if service is ready to handle requests"""
    try:
        # Check if database is accessible
        db.execute(text("SELECT 1"))
        return {"status": "ready", "timestamp": datetime.utcnow()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "error": str(e), "timestamp": datetime.utcnow()}
