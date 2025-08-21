import asyncio
import logging
from typing import Dict, List, Optional

from kubernetes.client.rest import ApiException
from kubernetes_asyncio import client, config

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class KubernetesService:
    def __init__(self):
        self.settings = get_settings()
        self.api_client = None
        self.v1 = None

    async def initialize(self):
        """Initialize Kubernetes client."""
        try:
            if self.settings.k8s_in_cluster:
                await config.load_incluster_config()
            else:
                await config.load_kube_config(
                    config_file=self.settings.k8s_config_path,
                    context=self.settings.k8s_context,
                )

            self.api_client = client.ApiClient()
            self.v1 = client.CoreV1Api(self.api_client)

            context_info = (
                f" (context: {self.settings.k8s_context})"
                if self.settings.k8s_context
                else ""
            )
            logger.info(f"Kubernetes client initialized successfully{context_info}")

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    async def close(self):
        """Close Kubernetes client."""
        if self.api_client:
            await self.api_client.close()

    async def get_all_pods(self) -> List[Dict]:
        """Get all pods excluding specified namespaces."""
        try:
            pods_list = await self.v1.list_pod_for_all_namespaces()
            pods_data = []

            for pod in pods_list.items:
                if pod.metadata.namespace in self.settings.excluded_namespaces_list:
                    continue

                pod_info = {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "node_name": pod.spec.node_name,
                    "phase": pod.status.phase,
                    "created": pod.metadata.creation_timestamp,
                    "containers": [],
                }

                if pod.spec.containers:
                    for container in pod.spec.containers:
                        container_info = {
                            "name": container.name,
                            "image": container.image,
                            "requests": {"cpu": 0.0, "memory": 0},
                            "limits": {"cpu": 0.0, "memory": 0},
                        }

                        if container.resources:
                            if container.resources.requests:
                                cpu_req = container.resources.requests.get("cpu", "0")
                                mem_req = container.resources.requests.get(
                                    "memory", "0"
                                )
                                container_info["requests"]["cpu"] = self._parse_cpu(
                                    cpu_req
                                )
                                container_info["requests"]["memory"] = (
                                    self._parse_memory(mem_req)
                                )

                            if container.resources.limits:
                                cpu_limit = container.resources.limits.get("cpu", "0")
                                mem_limit = container.resources.limits.get(
                                    "memory", "0"
                                )
                                container_info["limits"]["cpu"] = self._parse_cpu(
                                    cpu_limit
                                )
                                container_info["limits"]["memory"] = self._parse_memory(
                                    mem_limit
                                )

                        pod_info["containers"].append(container_info)

                pods_data.append(pod_info)

            logger.info(f"Retrieved {len(pods_data)} pods from Kubernetes")
            return pods_data

        except ApiException as e:
            logger.error(f"Kubernetes API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving pods: {e}")
            raise

    def _parse_cpu(self, cpu_str: str) -> float:
        """Parse CPU resource string to cores."""
        if not cpu_str or cpu_str == "0":
            return 0.0

        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000
        elif cpu_str.endswith("u"):
            return float(cpu_str[:-1]) / 1000000
        else:
            return float(cpu_str)

    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory resource string to bytes."""
        if not memory_str or memory_str == "0":
            return 0

        multipliers = {
            "Ki": 1024,
            "Mi": 1024**2,
            "Gi": 1024**3,
            "Ti": 1024**4,
            "K": 1000,
            "M": 1000**2,
            "G": 1000**3,
            "T": 1000**4,
        }

        for suffix, multiplier in multipliers.items():
            if memory_str.endswith(suffix):
                return int(float(memory_str[: -len(suffix)]) * multiplier)

        return int(memory_str)
