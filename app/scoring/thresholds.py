from app.constants import (
    DEPLOY_STATUS_CAUTION,
    DEPLOY_STATUS_DEPLOY,
    DEPLOY_STATUS_HOLD,
)


def classify_score(score: float) -> str:
    if score >= 85:
        return DEPLOY_STATUS_DEPLOY
    if score >= 70:
        return DEPLOY_STATUS_CAUTION
    return DEPLOY_STATUS_HOLD


def deploy_allowed(score: float, threshold: int) -> bool:
    return score >= threshold