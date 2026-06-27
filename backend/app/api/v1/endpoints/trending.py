from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.schemas import TrendCandidatesResponse, TrendPin, TrendPinsResponse, TrendRunRequest, TrendRunResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services.trending import approve_trend_candidate, list_trend_candidates, list_trend_pins, run_trending

router = APIRouter()

def _require_hr_admin(user: User) -> None:
    if user.role != "hr_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cần quyền HR admin")

@router.get("/trending/pins", response_model=TrendPinsResponse)
async def trending_pins(current_user: User = Depends(get_current_user)) -> TrendPinsResponse:
    return TrendPinsResponse(pins=list_trend_pins())

@router.post("/admin/trending/run", response_model=TrendRunResponse)
async def admin_trending_run(
    request: TrendRunRequest,
    current_user: User = Depends(get_current_user),
) -> TrendRunResponse:
    _require_hr_admin(current_user)
    created, skipped = run_trending(window_minutes=request.window_minutes, threshold=request.threshold)
    return TrendRunResponse(created_candidates=created, skipped_topics=skipped)


@router.get("/admin/trending/candidates", response_model=TrendCandidatesResponse)
async def admin_trending_candidates(current_user: User = Depends(get_current_user)) -> TrendCandidatesResponse:
    _require_hr_admin(current_user)
    return TrendCandidatesResponse(candidates=list_trend_candidates())


@router.post("/admin/trending/candidates/{candidate_id}/pin", response_model=TrendPin)
async def admin_approve_trending_candidate(
    candidate_id: str,
    current_user: User = Depends(get_current_user),
) -> TrendPin:
    _require_hr_admin(current_user)
    pin = approve_trend_candidate(candidate_id)
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy trend candidate")
    return pin
