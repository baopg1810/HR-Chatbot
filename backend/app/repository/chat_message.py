from app.repository.base import BaseRepository
from app.models.chat import ChatMessage

class ChatMessageRepository(BaseRepository[ChatMessage]):
    pass

chat_message_repository = ChatMessageRepository(ChatMessage)
