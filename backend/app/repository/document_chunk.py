from app.repository.base import BaseRepository
from app.models.document_chunk import DocumentChunk

class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    pass

document_chunk_repository = DocumentChunkRepository(DocumentChunk)
