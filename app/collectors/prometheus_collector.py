import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class PrometheusCollectorError(Exception):
    """Raised when Prometheus collection fails."""


class PrometheusCollector:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or settings.prometheus_url).rstrip("/")
        self.timeout = timeout

    def _query(self, promql: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/query"
        params = {"query": promql}

        try:
            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise PrometheusCollectorError(f"Prometheus query failed: {exc}") from exc

        if payload.get("status") != "success":
            raise PrometheusCollectorError(f"Prometheus returned non-success status: {payload}")

        data = payload.get("data", {})
        result = data.get("result", [])

        if not isinstance(result, list):
            raise PrometheusCollectorError(f"Unexpected Prometheus result structure: {payload}")

        return result

    @staticmethod
    def _extract_max_value(result: list[dict[str, Any]]) -> float:
        if not result:
            return 0.0

        values: list[float] = []
        for item in result:
            value = item.get("value")
            if not value or len(value) < 2:
                continue
            try:
                values.append(float(value[1]))
            except (TypeError, ValueError):
                continue

        return max(values) if values else 0.0

    @staticmethod
    def _extract_single_value(result: list[dict[str, Any]]) -> float:
        if not result:
            return 0.0

        first = result[0].get("value")
        if not first or len(first) < 2:
            return 0.0

        try:
            return float(first[1])
        except (TypeError, ValueError):
            return 0.0

    def collect_node_headroom(self) -> dict[str, float]:
        cpu_query = '100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))'
        mem_query = '100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))'

        cpu_result = self._query(cpu_query)
        mem_result = self._query(mem_query)

        max_worker_cpu_pct = self._extract_max_value(cpu_result)
        max_worker_mem_pct = self._extract_max_value(mem_result)

        logger.info(
            "Collected node headroom inputs max_worker_cpu_pct=%.2f max_worker_mem_pct=%.2f",
            max_worker_cpu_pct,
            max_worker_mem_pct,
        )

        return {
            "max_worker_cpu_pct": round(max_worker_cpu_pct, 2),
            "max_worker_mem_pct": round(max_worker_mem_pct, 2),
        }

    def collect_restart_pressure(self) -> dict[str, int]:
        restart_query = 'sum(increase(kube_pod_container_status_restarts_total[15m]))'

        result = self._query(restart_query)
        recent_restarts = int(round(self._extract_single_value(result), 0))

        logger.info("Collected restart pressure input recent_restarts_15m=%d", recent_restarts)

        return {
            "recent_restarts_15m": recent_restarts,
        }

    def collect_prometheus_inputs(self) -> dict[str, dict[str, float | int]]:
        return {
            "node_headroom": self.collect_node_headroom(),
            "restart_pressure": self.collect_restart_pressure(),
        }