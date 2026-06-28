from fastapi import APIRouter, Depends
from app.schemas.schemas import PersonalHrMetrics
from app.api.deps import get_current_user
from app.models.user import User
from app.services.hris import get_personal_hr_metrics

router = APIRouter()

@router.get("/me/hr-metrics", response_model=PersonalHrMetrics)
async def my_hr_metrics(current_user: User = Depends(get_current_user)) -> PersonalHrMetrics:
    return get_personal_hr_metrics(current_user)
