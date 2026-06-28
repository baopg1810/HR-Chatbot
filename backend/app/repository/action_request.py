from app.repository.base import BaseRepository
from app.models.action_request import ActionRequest

class ActionRequestRepository(BaseRepository[ActionRequest]):
    pass

action_request_repository = ActionRequestRepository(ActionRequest)
