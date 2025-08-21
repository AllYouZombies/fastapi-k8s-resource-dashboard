import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from ..core.config import get_settings
from ..core.database import SessionLocal
from ..models.database import ResourceMetric, ResourceSummary
from .kubernetes_service import KubernetesService
from .prometheus_service import PrometheusService

logger = logging.getLogger(__name__)


class ResourceCollectorService:
    def __init__(self):
        self.settings = get_settings()
        self.k8s_service = KubernetesService()

    async def initialize(self):
        """Initialize services."""
        await self.k8s_service.initialize()

    async def cleanup(self):
        """Cleanup resources."""
        await self.k8s_service.close()

    async def collect_and_store_metrics(self):
        """Main collection method - collects from K8s and Prometheus, stores in DB."""
        logger.info("Starting resource metrics collection")

        try:
            # Collect Kubernetes resource data
            pods_data = await self.k8s_service.get_all_pods()

            # Collect Prometheus usage data
            async with PrometheusService() as prom_service:
                usage_metrics = await prom_service.get_all_usage_metrics()

            # Combine and store data
            await self._store_metrics(pods_data, usage_metrics)

            # Clean old data
            await self._cleanup_old_data()

            logger.info("Resource metrics collection completed successfully")

        except Exception as e:
            logger.error(f"Error in resource collection: {e}")
            raise

    async def _store_metrics(self, pods_data: List[Dict], usage_metrics: Dict):
        """Store collected metrics in database."""
        timestamp = datetime.utcnow()
        metrics_to_store = []

        for pod in pods_data:
            pod_key = f"{pod['namespace']}/{pod['name']}"
            cpu_usage = usage_metrics["cpu_usage"].get(pod_key, 0.0)
            memory_usage = usage_metrics["memory_usage"].get(pod_key, 0)

            for container in pod["containers"]:
                metric = ResourceMetric(
                    timestamp=timestamp,
                    namespace=pod["namespace"],
                    pod_name=pod["name"],
                    container_name=container["name"],
                    node_name=pod.get("node_name"),
                    pod_phase=pod.get("phase"),
                    # Resource requests and limits
                    cpu_request_cores=container["requests"]["cpu"],
                    memory_request_bytes=container["requests"]["memory"],
                    cpu_limit_cores=container["limits"]["cpu"],
                    memory_limit_bytes=container["limits"]["memory"],
                    # Actual usage
                    cpu_usage_cores=cpu_usage
                    / len(pod["containers"]),  # Distribute evenly
                    memory_usage_bytes=memory_usage // len(pod["containers"]),
                )
                metrics_to_store.append(metric)

        # Batch insert
        db = SessionLocal()
        try:
            db.add_all(metrics_to_store)
            db.commit()
            logger.info(f"Stored {len(metrics_to_store)} resource metrics")
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing metrics: {e}")
            raise
        finally:
            db.close()

    async def _cleanup_old_data(self):
        """Remove data older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(days=self.settings.retention_days)

        db = SessionLocal()
        try:
            # Delete old metrics in batches to avoid locks
            while True:
                # Get IDs of records to delete
                ids_to_delete = [
                    row.id
                    for row in db.query(ResourceMetric.id)
                    .filter(ResourceMetric.timestamp < cutoff_time)
                    .limit(1000)
                ]

                if not ids_to_delete:
                    break

                # Delete by IDs
                db.query(ResourceMetric).filter(
                    ResourceMetric.id.in_(ids_to_delete)
                ).delete(synchronize_session=False)

                db.commit()
                await asyncio.sleep(0.1)  # Brief pause

            # Delete old summaries
            db.query(ResourceSummary).filter(
                ResourceSummary.timestamp < cutoff_time
            ).delete(synchronize_session=False)

            db.commit()
            logger.info(f"Cleaned up data older than {cutoff_time}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error cleaning up old data: {e}")
        finally:
            db.close()
