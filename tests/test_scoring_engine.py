from app.constants import DEPLOY_STATUS_CAUTION, DEPLOY_STATUS_DEPLOY, DEPLOY_STATUS_HOLD
from app.scoring.engine import calculate_deployment_confidence
from app.services.score_service import calculate_current_deployment_confidence


def test_calculate_deployment_confidence_deploy():
    raw_inputs = {
        "node_headroom": {"max_worker_cpu_pct": 50, "max_worker_mem_pct": 55},
        "restart_pressure": {"recent_restarts_15m": 1},
        "image_pull_health": {"pull_failures_15m": 0, "affected_registries": []},
        "startup_latency": {"p95_startup_seconds": 20},
        "dependency_health": {"dns_ok": True, "registry_ok": True},
    }

    result = calculate_deployment_confidence(raw_inputs=raw_inputs, threshold=70)

    assert result.status == DEPLOY_STATUS_DEPLOY
    assert result.deploy_allowed is True
    assert result.total_score >= 85
    assert len(result.components) == 5


def test_calculate_deployment_confidence_caution():
    raw_inputs = {
        "node_headroom": {"max_worker_cpu_pct": 70, "max_worker_mem_pct": 72},
        "restart_pressure": {"recent_restarts_15m": 4},
        "image_pull_health": {"pull_failures_15m": 2, "affected_registries": ["quay.io"]},
        "startup_latency": {"p95_startup_seconds": 45},
        "dependency_health": {"dns_ok": True, "registry_ok": True},
    }

    result = calculate_deployment_confidence(raw_inputs=raw_inputs, threshold=70)

    assert result.status == DEPLOY_STATUS_CAUTION
    assert result.deploy_allowed is True
    assert 70 <= result.total_score < 85


def test_calculate_deployment_confidence_hold():
    raw_inputs = {
        "node_headroom": {"max_worker_cpu_pct": 90, "max_worker_mem_pct": 92},
        "restart_pressure": {"recent_restarts_15m": 12},
        "image_pull_health": {"pull_failures_15m": 5, "affected_registries": ["quay.io"]},
        "startup_latency": {"p95_startup_seconds": 150},
        "dependency_health": {"dns_ok": False, "registry_ok": False},
    }

    result = calculate_deployment_confidence(raw_inputs=raw_inputs, threshold=70)

    assert result.status == DEPLOY_STATUS_HOLD
    assert result.deploy_allowed is False
    assert result.total_score < 70


class FakePrometheusCollector:
    def collect_prometheus_inputs(self):
        return {
            "node_headroom": {"max_worker_cpu_pct": 60, "max_worker_mem_pct": 70},
            "restart_pressure": {"recent_restarts_15m": 3},
        }


class FakeKubernetesCollector:
    def collect_kubernetes_inputs(self):
        return {
            "image_pull_health": {
                "pull_failures_15m": 2,
                "affected_registries": ["quay.io"],
            },
            "startup_latency": {
                "p95_startup_seconds": 45,
            },
        }


class FakeDependencyChecker:
    def collect_dependency_health(self):
        return {
            "dns_ok": True,
            "registry_ok": True,
        }


def test_calculate_current_deployment_confidence_integration():
    result = calculate_current_deployment_confidence(
        prometheus_collector=FakePrometheusCollector(),
        kubernetes_collector=FakeKubernetesCollector(),
        dependency_checker=FakeDependencyChecker(),
    )

    assert result.status in {"DEPLOY", "CAUTION", "HOLD"}
    assert isinstance(result.total_score, float)
    assert len(result.components) == 5
    assert result.deploy_allowed is True