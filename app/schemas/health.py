from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    app_healthy: bool
    database_healthy: bool
    scheduler_healthy: bool
    score_fresh: bool
    last_successful_score_update: str | None
    last_run_started_at: str | None
    last_run_failed_at: str | None
    last_error: str | None
    version: str