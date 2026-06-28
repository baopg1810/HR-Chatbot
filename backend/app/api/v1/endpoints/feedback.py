from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.schemas import FeedbackCreate, FeedbackResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services.feedback import create_feedback

router = APIRouter()

@router.post("", response_model=FeedbackResponse)
async def feedback(
    request: FeedbackCreate,
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    try:
        await create_feedback(current_user, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FeedbackResponse(ok=True)
