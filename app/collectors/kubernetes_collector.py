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
        """
        Backward-compatible image pull health collector.

        Keeps the existing component contract (`image_pull_health`) but fixes the logic by:
        - using active pod/container waiting state as primary truth
        - using recent Kubernetes events as supporting evidence
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        pods = []
        events = []

        if self.namespaces:
            for namespace in self.namespaces:
                pods.extend(self._list_pods(namespace=namespace))
                events.extend(self._list_events(namespace=namespace))
        else:
            pods = self._list_pods()
            events = self._list_events()

        active_failure_reasons = {"ErrImagePull", "ImagePullBackOff", "InvalidImageName"}

        active_pull_failures = 0
        recent_pull_failure_events = 0
        affected_registries: set[str] = set()
        affected_pods: set[str] = set()

        def extract_registry(image: str) -> str:
            if not image:
                return "unknown"
            return image.split("/")[0] if "/" in image else "docker.io"

        # Primary truth: active pod/container waiting state
        for pod in pods:
            metadata = getattr(pod, "metadata", None)
            status = getattr(pod, "status", None)

            if metadata is None or status is None:
                continue

            namespace = getattr(metadata, "namespace", "unknown")
            pod_name = getattr(metadata, "name", "unknown")

            container_statuses = getattr(status, "container_statuses", None) or []
            init_container_statuses = getattr(status, "init_container_statuses", None) or []
            all_statuses = list(init_container_statuses) + list(container_statuses)

            pod_has_active_failure = False

            for container_status in all_statuses:
                state = getattr(container_status, "state", None)
                waiting = getattr(state, "waiting", None) if state else None
                if waiting is None:
                    continue

                reason = getattr(waiting, "reason", "") or ""
                image = getattr(container_status, "image", "") or ""

                if reason in active_failure_reasons:
                    pod_has_active_failure = True
                    affected_registries.add(extract_registry(image))

            if pod_has_active_failure:
                active_pull_failures += 1
                affected_pods.add(f"{namespace}/{pod_name}")

        # Supporting evidence: recent events
        for event in events:
            event_time = (
                    getattr(event, "last_timestamp", None)
                    or getattr(event, "event_time", None)
                    or getattr(event, "first_timestamp", None)
            )
            if event_time is None:
                continue

            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)

            if event_time < cutoff:
                continue

            reason = getattr(event, "reason", "") or ""
            message = getattr(event, "message", "") or ""

            if (
                    "ErrImagePull" in message
                    or "ImagePullBackOff" in message
                    or "Failed to pull image" in message
                    or "Back-off pulling image" in message
                    or "Error: ErrImagePull" in message
                    or (reason == "BackOff" and "pull" in message.lower())
                    or (reason == "Failed" and "image" in message.lower())
            ):
                recent_pull_failure_events += 1

                involved_object = getattr(event, "involved_object", None)
                namespace = getattr(involved_object, "namespace", "unknown") if involved_object else "unknown"
                pod_name = getattr(involved_object, "name", "unknown") if involved_object else "unknown"

                if pod_name != "unknown":
                    affected_pods.add(f"{namespace}/{pod_name}")

                match = re.search(r'image "([^"]+)"', message)
                if match:
                    image = match.group(1)
                    affected_registries.add(extract_registry(image))

        # Backward compatibility:
        # keep pull_failures_15m for existing scorer/raw payload expectations
        result = {
            "pull_failures_15m": recent_pull_failure_events,
            "active_pull_failures": active_pull_failures,
            "recent_pull_failure_events": recent_pull_failure_events,
            "affected_pods": sorted(affected_pods),
            "affected_registries": sorted(affected_registries),
            "window_minutes": window_minutes,
        }

        logger.info(
            "Collected image pull health active_pull_failures=%d recent_pull_failure_events=%d affected_pods=%s affected_registries=%s",
            result["active_pull_failures"],
            result["recent_pull_failure_events"],
            result["affected_pods"],
            result["affected_registries"],
        )

        return result

    # def collect_image_pull_health(self, window_minutes: int = 15) -> dict[str, Any]:
    #     cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    #     events = []
    #
    #     if self.namespaces:
    #         for namespace in self.namespaces:
    #             events.extend(self._list_events(namespace=namespace))
    #     else:
    #         events = self._list_events()
    #
    #     pull_failures = 0
    #     affected_registries: set[str] = set()
    #
    #     for event in events:
    #         event_time = getattr(event, "last_timestamp", None) or getattr(event, "event_time", None)
    #         if event_time is None:
    #             continue
    #
    #         if event_time.tzinfo is None:
    #             event_time = event_time.replace(tzinfo=timezone.utc)
    #
    #         if event_time < cutoff:
    #             continue
    #
    #         reason = getattr(event, "reason", "") or ""
    #         message = getattr(event, "message", "") or ""
    #
    #         if (
    #             "ErrImagePull" in reason
    #             or "ImagePullBackOff" in reason
    #             or "Failed to pull image" in message
    #             or "Error: ErrImagePull" in message
    #         ):
    #             pull_failures += 1
    #
    #             match = re.search(r'image "([^"]+)"', message)
    #             if match:
    #                 image = match.group(1)
    #                 registry = image.split("/")[0] if "/" in image else "docker.io"
    #                 affected_registries.add(registry)
    #
    #     result = {
    #         "pull_failures_15m": pull_failures,
    #         "affected_registries": sorted(affected_registries),
    #     }
    #
    #     logger.info(
    #         "Collected image pull health pull_failures_15m=%d affected_registries=%s",
    #         result["pull_failures_15m"],
    #         result["affected_registries"],
    #     )
    #
    #     return result

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

            labels = getattr(metadata, "labels", {}) or {}
            if labels.get("app") != "deploy-confidence-service":
                continue

            created_at = getattr(metadata, "creation_timestamp", None)
            if created_at is None:
                continue

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            if created_at < cutoff:
                continue

            ready_at = None
            conditions = getattr(status, "conditions", None) or []

            for condition in conditions:
                condition_type = getattr(condition, "type", None)
                condition_status = getattr(condition, "status", None)

                if condition_type == "Ready" and condition_status == "True":
                    ready_at = getattr(condition, "last_transition_time", None)
                    break

            if ready_at is None:
                continue

            if ready_at.tzinfo is None:
                ready_at = ready_at.replace(tzinfo=timezone.utc)

            duration_seconds = (ready_at - created_at).total_seconds()
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
            "sample_count": len(startup_durations),
        }

        logger.info(
            "Collected startup latency p95_startup_seconds=%.2f sample_count=%d",
            result["p95_startup_seconds"],
            result["sample_count"],
        )

        return result

    # def collect_startup_latency(self, window_minutes: int = 30) -> dict[str, Any]:
    #     cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    #     pods = []
    #
    #     if self.namespaces:
    #         for namespace in self.namespaces:
    #             pods.extend(self._list_pods(namespace=namespace))
    #     else:
    #         pods = self._list_pods()
    #
    #     startup_durations: list[float] = []
    #
    #     for pod in pods:
    #         metadata = getattr(pod, "metadata", None)
    #         status = getattr(pod, "status", None)
    #
    #         if metadata is None or status is None:
    #             continue
    #
    #         created_at = getattr(metadata, "creation_timestamp", None)
    #         started_at = getattr(status, "start_time", None)
    #
    #         if created_at is None or started_at is None:
    #             continue
    #
    #         if created_at.tzinfo is None:
    #             created_at = created_at.replace(tzinfo=timezone.utc)
    #         if started_at.tzinfo is None:
    #             started_at = started_at.replace(tzinfo=timezone.utc)
    #
    #         if created_at < cutoff:
    #             continue
    #
    #         duration_seconds = (started_at - created_at).total_seconds()
    #         if duration_seconds < 0:
    #             continue
    #
    #         startup_durations.append(duration_seconds)
    #
    #     if not startup_durations:
    #         p95 = 0.0
    #     elif len(startup_durations) == 1:
    #         p95 = float(startup_durations[0])
    #     else:
    #         p95 = float(quantiles(startup_durations, n=100, method="inclusive")[94])
    #
    #     result = {
    #         "p95_startup_seconds": round(p95, 2),
    #     }
    #
    #     logger.info(
    #         "Collected startup latency p95_startup_seconds=%.2f",
    #         result["p95_startup_seconds"],
    #     )
    #
    #     return result

    def collect_kubernetes_inputs(self) -> dict[str, dict[str, Any]]:
        return {
            "image_pull_health": self.collect_image_pull_health(),
            "startup_latency": self.collect_startup_latency(),
        }