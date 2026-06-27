from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Nội dung tin nhắn")

class ChatResponse(BaseModel):
    response: str
