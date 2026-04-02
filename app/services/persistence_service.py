from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ScoreComponent, ScoreRun
from app.scoring.engine import ScoreCalculationResult


def create_score_run(
    db: Session,
    *,
    total_score: float,
    status: str,
    deploy_allowed: bool,
    threshold: int,
    summary: str,
    calculated_at,
) -> ScoreRun:
    score_run = ScoreRun(
        total_score=total_score,
        status=status,
        deploy_allowed=deploy_allowed,
        threshold=threshold,
        summary=summary,
        calculated_at=calculated_at,
    )
    db.add(score_run)
    db.flush()
    return score_run


def create_score_component(
    db: Session,
    *,
    score_run_id,
    component_name: str,
    component_score: float,
    weight: float,
    reason: str,
    raw_payload: dict,
) -> ScoreComponent:
    component = ScoreComponent(
        score_run_id=score_run_id,
        component_name=component_name,
        component_score=component_score,
        weight=weight,
        reason=reason,
        raw_payload=raw_payload,
    )
    db.add(component)
    db.flush()
    return component


def persist_score_calculation_result(
    db: Session,
    *,
    result: ScoreCalculationResult,
    calculated_at: datetime | None = None,
) -> ScoreRun:
    calculated_at = calculated_at or datetime.now(timezone.utc)

    score_run = create_score_run(
        db,
        total_score=result.total_score,
        status=result.status,
        deploy_allowed=result.deploy_allowed,
        threshold=result.threshold,
        summary=result.summary,
        calculated_at=calculated_at,
    )

    for component in result.components:
        create_score_component(
            db,
            score_run_id=score_run.id,
            component_name=component.name,
            component_score=component.score,
            weight=component.weight,
            reason=component.reason,
            raw_payload=component.raw,
        )

    db.commit()
    db.refresh(score_run)
    return score_run


def get_latest_score_run(db: Session) -> ScoreRun | None:
    stmt = (
        select(ScoreRun)
        .options(selectinload(ScoreRun.components))
        .order_by(ScoreRun.calculated_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()