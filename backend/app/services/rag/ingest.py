from pathlib import Path

from app.models.schemas import Role
from app.services.documents import create_document_from_upload_async


class DocumentIngestService:
    async def ingest_file(
        self,
        file_path: str,
        *,
        title: str | None = None,
        visibility_roles: list[Role] | None = None,
        department_ids: list[str] | None = None,
    ) -> dict:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(file_path)

        document, indexed_count, warnings = await create_document_from_upload_async(
            filename=path.name,
            content=path.read_bytes(),
            title=title,
            visibility_roles=visibility_roles,
            department_ids=department_ids,
        )
        return {
            "status": document.status,
            "file_path": str(path),
            "document_id": document.id,
            "indexed_chunk_count": indexed_count,
            "warnings": warnings,
        }
