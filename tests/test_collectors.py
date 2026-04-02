from unittest.mock import patch
import socket
import httpx
from app.collectors.prometheus_collector import PrometheusCollector
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.collectors.kubernetes_collector import KubernetesCollector
from unittest.mock import patch

from app.collectors.dependency_checks import DependencyChecker

def test_collect_node_headroom():
    cpu_payload = {
        "status": "success",
        "data": {
            "result": [
                {"metric": {"instance": "node-a"}, "value": [1710000000, "42.5"]},
                {"metric": {"instance": "node-b"}, "value": [1710000000, "61.0"]},
            ]
        },
    }

    mem_payload = {
        "status": "success",
        "data": {
            "result": [
                {"metric": {"instance": "node-a"}, "value": [1710000000, "55.0"]},
                {"metric": {"instance": "node-b"}, "value": [1710000000, "67.0"]},
            ]
        },
    }

    with patch("app.collectors.prometheus_collector.httpx.get") as mock_get:
        mock_get.side_effect = [
            _mock_response(cpu_payload),
            _mock_response(mem_payload),
        ]

        collector = PrometheusCollector(base_url="http://fake-prometheus:9090")
        result = collector.collect_node_headroom()

        assert result["max_worker_cpu_pct"] == 61.0
        assert result["max_worker_mem_pct"] == 67.0


def test_collect_restart_pressure():
    restart_payload = {
        "status": "success",
        "data": {
            "result": [
                {"metric": {}, "value": [1710000000, "3"]}
            ]
        },
    }

    with patch("app.collectors.prometheus_collector.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(restart_payload)

        collector = PrometheusCollector(base_url="http://fake-prometheus:9090")
        result = collector.collect_restart_pressure()

        assert result["recent_restarts_15m"] == 3


def test_collect_prometheus_inputs():
    cpu_payload = {
        "status": "success",
        "data": {
            "result": [
                {"metric": {"instance": "node-a"}, "value": [1710000000, "40.0"]},
                {"metric": {"instance": "node-b"}, "value": [1710000000, "60.0"]},
            ]
        },
    }

    mem_payload = {
        "status": "success",
        "data": {
            "result": [
                {"metric": {"instance": "node-a"}, "value": [1710000000, "50.0"]},
                {"metric": {"instance": "node-b"}, "value": [1710000000, "70.0"]},
            ]
        },
    }

    restart_payload = {
        "status": "success",
        "data": {
            "result": [
                {"metric": {}, "value": [1710000000, "4"]}
            ]
        },
    }

    with patch("app.collectors.prometheus_collector.httpx.get") as mock_get:
        mock_get.side_effect = [
            _mock_response(cpu_payload),
            _mock_response(mem_payload),
            _mock_response(restart_payload),
        ]

        collector = PrometheusCollector(base_url="http://fake-prometheus:9090")
        result = collector.collect_prometheus_inputs()

        assert result["node_headroom"]["max_worker_cpu_pct"] == 60.0
        assert result["node_headroom"]["max_worker_mem_pct"] == 70.0
        assert result["restart_pressure"]["recent_restarts_15m"] == 4


def test_collect_image_pull_health():
    now = datetime.now(timezone.utc)

    events = [
        SimpleNamespace(
            last_timestamp=now - timedelta(minutes=5),
            event_time=None,
            reason="Failed",
            message='Failed to pull image "quay.io/argoproj/argocd:v3.3.6": rpc error',
        ),
        SimpleNamespace(
            last_timestamp=now - timedelta(minutes=3),
            event_time=None,
            reason="ImagePullBackOff",
            message='Back-off pulling image "public.ecr.aws/docker/library/redis:8.2.3-alpine"',
        ),
        SimpleNamespace(
            last_timestamp=now - timedelta(minutes=20),
            event_time=None,
            reason="ImagePullBackOff",
            message='Back-off pulling image "docker.io/nginx:latest"',
        ),
    ]

    fake_api = _FakeCoreV1Api(events=events, pods=[])

    collector = KubernetesCollector(
        in_cluster=False,
        core_v1_api=fake_api,
    )

    result = collector.collect_image_pull_health(window_minutes=15)

    assert result["pull_failures_15m"] == 2
    assert "quay.io" in result["affected_registries"]
    assert "public.ecr.aws" in result["affected_registries"]


def test_collect_startup_latency():
    now = datetime.now(timezone.utc)

    pods = [
        SimpleNamespace(
            metadata=SimpleNamespace(creation_timestamp=now - timedelta(minutes=10)),
            status=SimpleNamespace(start_time=now - timedelta(minutes=9, seconds=30)),
        ),
        SimpleNamespace(
            metadata=SimpleNamespace(creation_timestamp=now - timedelta(minutes=8)),
            status=SimpleNamespace(start_time=now - timedelta(minutes=7, seconds=10)),
        ),
        SimpleNamespace(
            metadata=SimpleNamespace(creation_timestamp=now - timedelta(minutes=6)),
            status=SimpleNamespace(start_time=now - timedelta(minutes=4, seconds=30)),
        ),
    ]

    fake_api = _FakeCoreV1Api(events=[], pods=pods)

    collector = KubernetesCollector(
        in_cluster=False,
        core_v1_api=fake_api,
    )

    result = collector.collect_startup_latency(window_minutes=30)

    assert result["p95_startup_seconds"] > 0
    assert isinstance(result["p95_startup_seconds"], float)


def test_collect_kubernetes_inputs():
    now = datetime.now(timezone.utc)

    events = [
        SimpleNamespace(
            last_timestamp=now - timedelta(minutes=5),
            event_time=None,
            reason="ErrImagePull",
            message='Error: ErrImagePull image "quay.io/prometheus/busybox:latest"',
        ),
    ]

    pods = [
        SimpleNamespace(
            metadata=SimpleNamespace(creation_timestamp=now - timedelta(minutes=5)),
            status=SimpleNamespace(start_time=now - timedelta(minutes=4, seconds=20)),
        ),
    ]

    fake_api = _FakeCoreV1Api(events=events, pods=pods)

    collector = KubernetesCollector(
        in_cluster=False,
        core_v1_api=fake_api,
    )

    result = collector.collect_kubernetes_inputs()

    assert "image_pull_health" in result
    assert "startup_latency" in result
    assert result["image_pull_health"]["pull_failures_15m"] == 1
    assert result["startup_latency"]["p95_startup_seconds"] > 0


def test_collect_dependency_health_success():
    with patch("app.collectors.dependency_checks.socket.getaddrinfo") as mock_dns, \
         patch("app.collectors.dependency_checks.httpx.get") as mock_http:
        mock_dns.return_value = [("ok",)]
        mock_http.side_effect = [
            _mock_http_response(200),
            _mock_http_response(200),
        ]

        checker = DependencyChecker(
            dns_target="quay.io",
            registry_urls=["https://quay.io", "https://public.ecr.aws"],
        )
        result = checker.collect_dependency_health()

        assert result["dns_ok"] is True
        assert result["registry_ok"] is True


def test_collect_dependency_health_partial_failure():
    with patch("app.collectors.dependency_checks.socket.getaddrinfo") as mock_dns, \
         patch("app.collectors.dependency_checks.httpx.get") as mock_http:
        mock_dns.return_value = [("ok",)]
        mock_http.side_effect = [
            _mock_http_response(200),
            httpx.ConnectError("connection failed"),
        ]

        checker = DependencyChecker(
            dns_target="quay.io",
            registry_urls=["https://quay.io", "https://public.ecr.aws"],
        )
        result = checker.collect_dependency_health()

        assert result["dns_ok"] is True
        assert result["registry_ok"] is False


def test_collect_dependency_health_dns_failure():
    with patch("app.collectors.dependency_checks.socket.getaddrinfo") as mock_dns, \
         patch("app.collectors.dependency_checks.httpx.get") as mock_http:
        mock_dns.side_effect = socket.gaierror("dns failed")
        mock_http.side_effect = [
            _mock_http_response(200),
            _mock_http_response(200),
        ]

        checker = DependencyChecker(
            dns_target="quay.io",
            registry_urls=["https://quay.io", "https://public.ecr.aws"],
        )
        result = checker.collect_dependency_health()

        assert result["dns_ok"] is False
        assert result["registry_ok"] is True


class _mock_http_response:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeCoreV1Api:
    def __init__(self, events, pods):
        self._events = events
        self._pods = pods

    def list_event_for_all_namespaces(self):
        return SimpleNamespace(items=self._events)

    def list_namespaced_event(self, namespace):
        return SimpleNamespace(items=self._events)

    def list_pod_for_all_namespaces(self):
        return SimpleNamespace(items=self._pods)

    def list_namespaced_pod(self, namespace):
        return SimpleNamespace(items=self._pods)


class _mock_response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload