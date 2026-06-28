from app.repository.base import BaseRepository
from app.models.chat import ChatSession

class ChatRepository(BaseRepository[ChatSession]):
    pass

chat_repository = ChatRepository(ChatSession)
