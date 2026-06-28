from app.repository.base import BaseRepository
from app.models.feedback import Feedback

class FeedbackRepository(BaseRepository[Feedback]):
    pass

feedback_repository = FeedbackRepository(Feedback)
