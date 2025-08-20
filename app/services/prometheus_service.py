import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from ..core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class PrometheusService:
    def __init__(self):
        self.settings = get_settings()
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.settings.prometheus_timeout),
            connector=aiohttp.TCPConnector(limit=10)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def query_prometheus(self, query: str, time: Optional[datetime] = None) -> Dict:
        """Execute PromQL query."""
        params = {'query': query}
        if time:
            params['time'] = time.isoformat()

        url = f"{self.settings.prometheus_url}/api/v1/query"

        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                if data['status'] != 'success':
                    raise Exception(f"Prometheus query failed: {data.get('error', 'Unknown error')}")

                return data['data']

        except Exception as e:
            logger.error(f"Prometheus query error for '{query}': {e}")
            raise

    async def get_pod_cpu_usage(self) -> Dict[str, float]:
        """Get CPU usage by pod."""
        query = '''
        sum(rate(container_cpu_usage_seconds_total{container!="POD",container!=""}[5m])) by (namespace, pod)
        '''

        try:
            data = await self.query_prometheus(query)
            usage_by_pod = {}

            for result in data['result']:
                metric = result['metric']
                namespace = metric.get('namespace', '')
                pod = metric.get('pod', '')
                usage = float(result['value'][1])

                if namespace and pod:
                    key = f"{namespace}/{pod}"
                    usage_by_pod[key] = usage

            return usage_by_pod

        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return {}

    async def get_pod_memory_usage(self) -> Dict[str, int]:
        """Get memory usage by pod."""
        query = '''
        sum(container_memory_working_set_bytes{container!="POD",container!=""}) by (namespace, pod)
        '''

        try:
            data = await self.query_prometheus(query)
            usage_by_pod = {}

            for result in data['result']:
                metric = result['metric']
                namespace = metric.get('namespace', '')
                pod = metric.get('pod', '')
                usage = int(float(result['value'][1]))

                if namespace and pod:
                    key = f"{namespace}/{pod}"
                    usage_by_pod[key] = usage

            return usage_by_pod

        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}

    async def get_all_usage_metrics(self) -> Dict:
        """Get all usage metrics concurrently."""
        try:
            cpu_task = self.get_pod_cpu_usage()
            memory_task = self.get_pod_memory_usage()

            cpu_usage, memory_usage = await asyncio.gather(
                cpu_task, memory_task, return_exceptions=True
            )

            return {
                'cpu_usage': cpu_usage if not isinstance(cpu_usage, Exception) else {},
                'memory_usage': memory_usage if not isinstance(memory_usage, Exception) else {}
            }

        except Exception as e:
            logger.error(f"Error getting usage metrics: {e}")
            return {'cpu_usage': {}, 'memory_usage': {}}