import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.session import SessionLocal
from app.services.persistence_service import persist_score_calculation_result
from app.services.score_service import calculate_current_deployment_confidence

logger = logging.getLogger(__name__)


@dataclass
class SchedulerState:
    last_successful_score_update: datetime | None = None
    last_run_started_at: datetime | None = None
    last_run_failed_at: datetime | None = None
    last_error: str | None = None
    scheduler_started: bool = False


scheduler_state = SchedulerState()
scheduler = BackgroundScheduler(timezone="UTC")


def run_score_update_job() -> None:
    scheduler_state.last_run_started_at = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        result = calculate_current_deployment_confidence()
        persist_score_calculation_result(
            db,
            result=result,
            calculated_at=datetime.now(timezone.utc),
        )

        scheduler_state.last_successful_score_update = datetime.now(timezone.utc)
        scheduler_state.last_error = None

        logger.info(
            "Score update completed total_score=%.2f status=%s deploy_allowed=%s",
            result.total_score,
            result.status,
            result.deploy_allowed,
        )
    except Exception as exc:
        db.rollback()
        scheduler_state.last_run_failed_at = datetime.now(timezone.utc)
        scheduler_state.last_error = str(exc)
        logger.exception("Score update job failed: %s", exc)
    finally:
        db.close()


def start_scheduler(check_interval_seconds: int) -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        run_score_update_job,
        trigger="interval",
        seconds=check_interval_seconds,
        id="deployment-confidence-update",
        replace_existing=True,
    )
    scheduler.start()
    scheduler_state.scheduler_started = True

    logger.info(
        "Scheduler started with interval=%s seconds",
        check_interval_seconds,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")