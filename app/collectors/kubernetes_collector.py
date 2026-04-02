import logging
import re
from datetime import datetime, timedelta, timezone
from statistics import quantiles
from typing import Any

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from app.config import settings

logger = logging.getLogger(__name__)


class KubernetesCollectorError(Exception):
    """Raised when Kubernetes collection fails."""


class KubernetesCollector:
    def __init__(
        self,
        in_cluster: bool | None = None,
        namespaces: list[str] | None = None,
        core_v1_api: client.CoreV1Api | None = None,
    ) -> None:
        self.in_cluster = settings.kubernetes_in_cluster if in_cluster is None else in_cluster
        self.namespaces = namespaces or []
        self._core_v1_api = core_v1_api

        if self._core_v1_api is None:
            self._load_config()
            self._core_v1_api = client.CoreV1Api()

    def _load_config(self) -> None:
        try:
            if self.in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config()
        except ConfigException as exc:
            raise KubernetesCollectorError(f"Failed to load Kubernetes config: {exc}") from exc

    @property
    def core_v1_api(self) -> client.CoreV1Api:
        return self._core_v1_api

    def _list_events(self, namespace: str | None = None):
        try:
            if namespace:
                return self.core_v1_api.list_namespaced_event(namespace=namespace).items
            return self.core_v1_api.list_event_for_all_namespaces().items
        except Exception as exc:
            raise KubernetesCollectorError(f"Failed to list Kubernetes events: {exc}") from exc

    def _list_pods(self, namespace: str | None = None):
        try:
            if namespace:
                return self.core_v1_api.list_namespaced_pod(namespace=namespace).items
            return self.core_v1_api.list_pod_for_all_namespaces().items
        except Exception as exc:
            raise KubernetesCollectorError(f"Failed to list Kubernetes pods: {exc}") from exc

    def collect_image_pull_health(self, window_minutes: int = 15) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        events = []

        if self.namespaces:
            for namespace in self.namespaces:
                events.extend(self._list_events(namespace=namespace))
        else:
            events = self._list_events()

        pull_failures = 0
        affected_registries: set[str] = set()

        for event in events:
            event_time = getattr(event, "last_timestamp", None) or getattr(event, "event_time", None)
            if event_time is None:
                continue

            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)

            if event_time < cutoff:
                continue

            reason = getattr(event, "reason", "") or ""
            message = getattr(event, "message", "") or ""

            if (
                "ErrImagePull" in reason
                or "ImagePullBackOff" in reason
                or "Failed to pull image" in message
                or "Error: ErrImagePull" in message
            ):
                pull_failures += 1

                match = re.search(r'image "([^"]+)"', message)
                if match:
                    image = match.group(1)
                    registry = image.split("/")[0] if "/" in image else "docker.io"
                    affected_registries.add(registry)

        result = {
            "pull_failures_15m": pull_failures,
            "affected_registries": sorted(affected_registries),
        }

        logger.info(
            "Collected image pull health pull_failures_15m=%d affected_registries=%s",
            result["pull_failures_15m"],
            result["affected_registries"],
        )

        return result

    def collect_startup_latency(self, window_minutes: int = 30) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        pods = []

        if self.namespaces:
            for namespace in self.namespaces:
                pods.extend(self._list_pods(namespace=namespace))
        else:
            pods = self._list_pods()

        startup_durations: list[float] = []

        for pod in pods:
            metadata = getattr(pod, "metadata", None)
            status = getattr(pod, "status", None)

            if metadata is None or status is None:
                continue

            created_at = getattr(metadata, "creation_timestamp", None)
            started_at = getattr(status, "start_time", None)

            if created_at is None or started_at is None:
                continue

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)

            if created_at < cutoff:
                continue

            duration_seconds = (started_at - created_at).total_seconds()
            if duration_seconds < 0:
                continue

            startup_durations.append(duration_seconds)

        if not startup_durations:
            p95 = 0.0
        elif len(startup_durations) == 1:
            p95 = float(startup_durations[0])
        else:
            p95 = float(quantiles(startup_durations, n=100, method="inclusive")[94])

        result = {
            "p95_startup_seconds": round(p95, 2),
        }

        logger.info(
            "Collected startup latency p95_startup_seconds=%.2f",
            result["p95_startup_seconds"],
        )

        return result

    def collect_kubernetes_inputs(self) -> dict[str, dict[str, Any]]:
        return {
            "image_pull_health": self.collect_image_pull_health(),
            "startup_latency": self.collect_startup_latency(),
        }