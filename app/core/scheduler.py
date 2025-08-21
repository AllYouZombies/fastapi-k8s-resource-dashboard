import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..services.collector_service import ResourceCollectorService
from .config import get_settings

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.collector_service = None
        self.settings = get_settings()

    async def initialize(self):
        """Initialize the collector service."""
        self.collector_service = ResourceCollectorService()
        await self.collector_service.initialize()

    def start(self):
        """Start the background scheduler."""
        if self.scheduler.running:
            return

        # Add resource collection job
        self.scheduler.add_job(
            func=self._collect_resources,
            trigger=IntervalTrigger(minutes=self.settings.collection_interval_minutes),
            id="resource_collection",
            name="Kubernetes Resource Collection",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
            coalesce=True,
        )

        self.scheduler.start()
        logger.info(
            f"Scheduler started with {self.settings.collection_interval_minutes} minute intervals"
        )

    def stop(self):
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    async def cleanup(self):
        """Cleanup resources."""
        if self.collector_service:
            await self.collector_service.cleanup()

    async def _collect_resources(self):
        """Background task to collect resources."""
        try:
            await self.collector_service.collect_and_store_metrics()
        except Exception as e:
            logger.error(f"Resource collection failed: {e}")


# Global scheduler instance
task_scheduler = TaskScheduler()


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager."""
    # Startup
    settings = get_settings()

    if settings.enable_scheduler:
        await task_scheduler.initialize()
        task_scheduler.start()

    yield

    # Shutdown
    task_scheduler.stop()
    await task_scheduler.cleanup()
