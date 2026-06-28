from app.repository.base import BaseRepository
from app.models.trend_question import TrendQuestion

class TrendQuestionRepository(BaseRepository[TrendQuestion]):
    pass

trend_question_repository = TrendQuestionRepository(TrendQuestion)
