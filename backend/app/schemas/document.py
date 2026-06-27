from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    content_snippet: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
