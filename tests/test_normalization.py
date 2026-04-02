from app.scoring.normalization import (
    score_dependency_health,
    score_image_pull_health,
    score_node_headroom,
    score_restart_pressure,
    score_startup_latency,
)


def test_score_node_headroom_high_confidence():
    score, reason, raw = score_node_headroom(max_worker_cpu_pct=50, max_worker_mem_pct=55)
    assert score == 100.0
    assert "headroom" in reason.lower()
    assert raw["max_worker_cpu_pct"] == 50


def test_score_restart_pressure_critical():
    score, reason, raw = score_restart_pressure(recent_restarts_15m=12)
    assert score == 10.0
    assert raw["recent_restarts_15m"] == 12


def test_score_image_pull_health_medium():
    score, reason, raw = score_image_pull_health(
        pull_failures_15m=3,
        affected_registries=["quay.io"],
    )
    assert score == 45.0
    assert "quay.io" in raw["affected_registries"]


def test_score_startup_latency_good():
    score, reason, raw = score_startup_latency(p95_startup_seconds=20)
    assert score == 100.0
    assert raw["p95_startup_seconds"] == 20


def test_score_dependency_health_partial():
    score, reason, raw = score_dependency_health(dns_ok=True, registry_ok=False)
    assert score == 60.0
    assert raw["dns_ok"] is True
    assert raw["registry_ok"] is False