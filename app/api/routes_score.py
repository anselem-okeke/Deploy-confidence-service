from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.score import ScoreResponse
from app.services.score_service import get_latest_score_response

router = APIRouter(tags=["score"])


@router.get("/score", response_model=ScoreResponse)
def get_score(db: Session = Depends(get_db)) -> ScoreResponse:
    result = get_latest_score_response(db)
    if result is None:
        raise HTTPException(status_code=404, detail="No deployment confidence score available yet.")
    return result