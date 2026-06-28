from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.schemas.schemas import DocumentCreate, DocumentIngestResult, DocumentListResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services.documents import (
    create_document_async,
    create_document_from_upload_async,
    delete_document_async,
    list_documents,
)

router = APIRouter()


def _require_hr_admin(user: User) -> None:
    if user.role != "hr_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cần quyền HR admin")


@router.post(
    "",
    response_model=DocumentIngestResult,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/DocumentCreate"},
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "visibility_roles": {"type": "array", "items": {"type": "string"}},
                            "department_ids": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["title", "content"],
                    },
                },
            },
            "required": True,
        }
    },
)
async def ingest_document(
    request: DocumentCreate,
    current_user: User = Depends(get_current_user),
) -> DocumentIngestResult:
    _require_hr_admin(current_user)
    try:
        document, indexed_count, warnings = await create_document_async(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return DocumentIngestResult(document=document, indexed_chunk_count=indexed_count, warnings=warnings)


@router.post("/upload", response_model=DocumentIngestResult)
async def ingest_document_upload(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    visibility_roles: list[str] | None = Form(default=None),
    department_ids: list[str] | None = Form(default=None),
    current_user: User = Depends(get_current_user),
) -> DocumentIngestResult:
    _require_hr_admin(current_user)
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File tải lên phải có tên file")
    try:
        document, indexed_count, warnings = await create_document_from_upload_async(
            filename=file.filename,
            content=await file.read(),
            title=title,
            visibility_roles=visibility_roles,
            department_ids=department_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return DocumentIngestResult(document=document, indexed_chunk_count=indexed_count, warnings=warnings)


@router.get("", response_model=DocumentListResponse)
async def documents(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    _require_hr_admin(current_user)
    return DocumentListResponse(documents=list_documents(status_filter))


@router.delete("/{document_id}", response_model=DocumentIngestResult)
async def remove_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
) -> DocumentIngestResult:
    _require_hr_admin(current_user)
    document = await delete_document_async(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu")
    return DocumentIngestResult(document=document, indexed_chunk_count=0, warnings=[])
