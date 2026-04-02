from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.score import ScoreDetailsResponse
from app.services.score_service import get_latest_score_details_response

router = APIRouter(tags=["details"])


@router.get("/details", response_model=ScoreDetailsResponse)
def get_details(db: Session = Depends(get_db)) -> ScoreDetailsResponse:
    result = get_latest_score_details_response(db)
    if result is None:
        raise HTTPException(status_code=404, detail="No deployment confidence score available yet.")
    return result