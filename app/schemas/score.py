from pydantic import BaseModel


class ScoreResponse(BaseModel):
    score: float
    status: str
    deploy_allowed: bool
    threshold: int
    summary: str
    updated_at: str


class ScoreComponentResponse(BaseModel):
    name: str
    score: float
    weight: float
    reason: str
    raw: dict


class ScoreDetailsResponse(BaseModel):
    score: float
    status: str
    deploy_allowed: bool
    threshold: int
    summary: str
    updated_at: str
    components: list[ScoreComponentResponse]