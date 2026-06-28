from app.repository.base import BaseRepository
from app.models.query_log import QueryLog

class QueryLogRepository(BaseRepository[QueryLog]):
    pass

query_log_repository = QueryLogRepository(QueryLog)
