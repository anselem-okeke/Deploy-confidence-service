from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Response, status

from app.config import settings
from app.constants import APP_STATUS_DEGRADED, APP_STATUS_FAILED, APP_STATUS_OK, SERVICE_NAME
from app.db.init_db import check_database_connection
from app.schemas.health import HealthResponse
from app.scheduler.updater import scheduler_state

router = APIRouter(tags=["health"])


def _to_iso_z(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _is_score_fresh(last_update: datetime | None) -> bool:
    if last_update is None:
        return False

    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)

    max_age = timedelta(seconds=settings.check_interval_seconds * 3)
    return datetime.now(timezone.utc) - last_update <= max_age


@router.get("/live")
def get_liveness() -> dict:
    return {
        "status": "alive",
        "service": SERVICE_NAME,
    }


@router.get("/ready")
def get_readiness(response: Response) -> dict:
    database_healthy = check_database_connection()
    scheduler_healthy = scheduler_state.scheduler_started
    score_fresh = _is_score_fresh(scheduler_state.last_successful_score_update)

    ready = database_healthy and scheduler_healthy and score_fresh

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "ready": ready,
        "database_healthy": database_healthy,
        "scheduler_healthy": scheduler_healthy,
        "score_fresh": score_fresh,
    }


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    app_healthy = True
    database_healthy = check_database_connection()
    scheduler_healthy = scheduler_state.scheduler_started
    score_fresh = _is_score_fresh(scheduler_state.last_successful_score_update)

    if not app_healthy or not database_healthy:
        status_value = APP_STATUS_FAILED
    elif scheduler_healthy and score_fresh and scheduler_state.last_error is None:
        status_value = APP_STATUS_OK
    else:
        status_value = APP_STATUS_DEGRADED

    return HealthResponse(
        status=status_value,
        service=SERVICE_NAME,
        app_healthy=app_healthy,
        database_healthy=database_healthy,
        scheduler_healthy=scheduler_healthy,
        score_fresh=score_fresh,
        last_successful_score_update=_to_iso_z(scheduler_state.last_successful_score_update),
        last_run_started_at=_to_iso_z(scheduler_state.last_run_started_at),
        last_run_failed_at=_to_iso_z(scheduler_state.last_run_failed_at),
        last_error=scheduler_state.last_error,
        version=settings.app_version,
    )

























# from datetime import datetime, timedelta, timezone
#
# from fastapi import APIRouter
#
# from app.config import settings
# from app.constants import APP_STATUS_DEGRADED, APP_STATUS_FAILED, APP_STATUS_OK, SERVICE_NAME
# from app.db.init_db import check_database_connection
# from app.schemas.health import HealthResponse
# from app.scheduler.updater import scheduler_state
#
# router = APIRouter(tags=["health"])
#
#
# def _to_iso_z(dt: datetime | None) -> str | None:
#     if dt is None:
#         return None
#     if dt.tzinfo is None:
#         dt = dt.replace(tzinfo=timezone.utc)
#     return dt.isoformat().replace("+00:00", "Z")
#
#
# def _is_score_fresh(last_update: datetime | None) -> bool:
#     if last_update is None:
#         return False
#
#     if last_update.tzinfo is None:
#         last_update = last_update.replace(tzinfo=timezone.utc)
#
#     max_age = timedelta(seconds=settings.check_interval_seconds * 3)
#     return datetime.now(timezone.utc) - last_update <= max_age
#
#
# @router.get("/health", response_model=HealthResponse)
# def get_health() -> HealthResponse:
#     app_healthy = True
#     database_healthy = check_database_connection()
#     scheduler_healthy = scheduler_state.scheduler_started
#     score_fresh = _is_score_fresh(scheduler_state.last_successful_score_update)
#
#     if not app_healthy or not database_healthy:
#         status = APP_STATUS_FAILED
#     elif scheduler_healthy and score_fresh and scheduler_state.last_error is None:
#         status = APP_STATUS_OK
#     else:
#         status = APP_STATUS_DEGRADED
#
#     return HealthResponse(
#         status=status,
#         service=SERVICE_NAME,
#         app_healthy=app_healthy,
#         database_healthy=database_healthy,
#         scheduler_healthy=scheduler_healthy,
#         score_fresh=score_fresh,
#         last_successful_score_update=_to_iso_z(scheduler_state.last_successful_score_update),
#         last_run_started_at=_to_iso_z(scheduler_state.last_run_started_at),
#         last_run_failed_at=_to_iso_z(scheduler_state.last_run_failed_at),
#         last_error=scheduler_state.last_error,
#         version=settings.app_version,
#     )