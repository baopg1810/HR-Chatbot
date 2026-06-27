from fastapi import APIRouter

from app.api.v1.endpoints import auth, document, chat, ticket, trending, feedback, hr_metrics
from app.schemas.auth import UserResponse

api_router = APIRouter()

# Mount endpoints
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(document.router, prefix="/documents", tags=["documents"])
api_router.include_router(ticket.router, tags=["tickets"])
api_router.include_router(trending.router, tags=["trending"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(hr_metrics.router, tags=["hr-metrics"])

# Direct routes
api_router.get("/me", response_model=UserResponse, tags=["auth"])(auth.get_me)
