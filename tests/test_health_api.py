from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.scheduler.updater import scheduler_state


client = TestClient(app)


def reset_scheduler_state() -> None:
    scheduler_state.last_successful_score_update = None
    scheduler_state.last_run_started_at = None
    scheduler_state.last_run_failed_at = None
    scheduler_state.last_error = None
    scheduler_state.scheduler_started = False


def test_health_ok():
    reset_scheduler_state()
    scheduler_state.scheduler_started = True
    scheduler_state.last_successful_score_update = datetime.now(timezone.utc)
    scheduler_state.last_run_started_at = datetime.now(timezone.utc)

    with patch("app.api.routes_health.check_database_connection", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["app_healthy"] is True
    assert payload["database_healthy"] is True
    assert payload["scheduler_healthy"] is True
    assert payload["score_fresh"] is True
    assert payload["last_error"] is None


def test_health_degraded_when_scheduler_not_started():
    reset_scheduler_state()

    with patch("app.api.routes_health.check_database_connection", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "degraded"
    assert payload["database_healthy"] is True
    assert payload["scheduler_healthy"] is False
    assert payload["score_fresh"] is False


def test_health_degraded_when_score_stale():
    reset_scheduler_state()
    scheduler_state.scheduler_started = True
    scheduler_state.last_successful_score_update = datetime.now(timezone.utc) - timedelta(hours=1)

    with patch("app.api.routes_health.check_database_connection", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "degraded"
    assert payload["scheduler_healthy"] is True
    assert payload["score_fresh"] is False


def test_health_failed_when_database_unhealthy():
    reset_scheduler_state()
    scheduler_state.scheduler_started = True
    scheduler_state.last_successful_score_update = datetime.now(timezone.utc)

    with patch("app.api.routes_health.check_database_connection", return_value=False):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "failed"
    assert payload["database_healthy"] is False


def test_health_includes_last_error():
    reset_scheduler_state()
    scheduler_state.scheduler_started = True
    scheduler_state.last_successful_score_update = datetime.now(timezone.utc)
    scheduler_state.last_error = "Prometheus query failed"

    with patch("app.api.routes_health.check_database_connection", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "degraded"
    assert payload["last_error"] == "Prometheus query failed"