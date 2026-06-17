from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import math
from typing import Any
from uuid import uuid4

from src.config import get_settings
from src.models.schemas import Document, DocumentCreate, Role
from src.rag.chunking import chunk_document
from src.rag.loaders import load_policy_document
from src.services.llm import Embedding, embed_document_texts


@dataclass
class DocumentChunk:
    id: str
    document_id: str
    document_title: str
    section: str | None
    excerpt: str
    page: int | None
    visibility_roles: list[Role]
    department_ids: list[str]
    embedding: Embedding
    metadata: dict[str, Any]


_DOCUMENTS: dict[str, Document] = {}
_CHUNKS: list[DocumentChunk] = []
_CHROMA_COLLECTION = None
_CHROMA_AVAILABLE: bool | None = None
_LOCAL_DENSE_DIMENSIONS = 3072


def create_document(payload: DocumentCreate) -> tuple[Document, int, list[str]]:
    document_id = f"doc-{uuid4()}"
    created_at = datetime.now(UTC).isoformat()
    chunks = chunk_document(
        payload.content,
        {
            "document_name": payload.title,
            "document_type": "hr_policy",
            "language": "vi",
            "source_path": document_id,
        },
        created_at=created_at,
    )
    document = Document(
        id=document_id,
        title=payload.title,
        status="indexed",
        visibility_roles=payload.visibility_roles,
        department_ids=payload.department_ids,
        created_at=created_at,
        chunk_count=len(chunks),
    )
    if not _using_chroma():
        _DOCUMENTS[document_id] = document

    embeddings = embed_document_texts(payload.title, [chunk.embedding_text for chunk in chunks])
    for index, chunk in enumerate(chunks, start=1):
        section = _display_section(chunk.metadata, fallback=f"chunk-{index}")
        document_chunk = DocumentChunk(
            id=f"{document_id}:chunk-{index}",
            document_id=document_id,
            document_title=payload.title,
            section=section,
            excerpt=chunk.content,
            page=None,
            visibility_roles=payload.visibility_roles,
            department_ids=payload.department_ids,
            embedding=embeddings[index - 1],
            metadata=chunk.metadata,
        )
        if _using_chroma():
            _add_chunk_to_chroma(document, document_chunk)
        else:
            _CHUNKS.append(document_chunk)

    warnings: list[str] = []
    if len(chunks) == 1:
        warnings.append("Document indexed as a single chunk.")
    return document, len(chunks), warnings


def create_document_from_upload(
    *,
    filename: str,
    content: bytes,
    title: str | None = None,
    visibility_roles: list[Role] | None = None,
    department_ids: list[str] | None = None,
) -> tuple[Document, int, list[str]]:
    loaded = load_policy_document(content, filename=filename)
    document_title = title or loaded.metadata["document_name"]
    document, chunk_count, warnings = create_document(
        DocumentCreate(
            title=document_title,
            content=loaded.text,
            visibility_roles=visibility_roles or ["employee", "department_admin", "hr_admin"],
            department_ids=department_ids or [],
        )
    )
    if not loaded.text.strip():
        warnings.append("Tài liệu tải lên không có nội dung văn bản có thể trích xuất.")
    return document, chunk_count, warnings


def list_documents(status: str | None = None) -> list[Document]:
    if _using_chroma():
        documents = _list_documents_from_chroma()
        if status:
            documents = [document for document in documents if document.status == status]
        return sorted(documents, key=lambda document: document.created_at, reverse=True)

    documents = list(_DOCUMENTS.values())
    if status:
        documents = [document for document in documents if document.status == status]
    return sorted(documents, key=lambda document: document.created_at, reverse=True)


def delete_document(document_id: str) -> Document | None:
    if _using_chroma():
        documents = {document.id: document for document in _list_documents_from_chroma()}
        document = documents.get(document_id)
        if document is None:
            return None
        _chroma_collection().delete(where={"document_id": document_id})
        return document

    document = _DOCUMENTS.pop(document_id, None)
    if document is None:
        return None

    _CHUNKS[:] = [chunk for chunk in _CHUNKS if chunk.document_id != document_id]
    return document


def list_chunks() -> list[DocumentChunk]:
    if _using_chroma():
        return _list_chunks_from_chroma()
    return list(_CHUNKS)


def query_chunks(query_embedding: Embedding, limit: int = 20) -> list[tuple[float, DocumentChunk]]:
    if not _using_chroma():
        return []

    collection = _chroma_collection()
    try:
        result = collection.query(
            query_embeddings=[_embedding_to_chroma_vector(query_embedding)],
            n_results=max(1, limit),
            include=["documents", "embeddings", "metadatas", "distances"],
        )
    except Exception:
        return []

    ids = _nested_collection_values(result, "ids")
    documents = _nested_collection_values(result, "documents")
    embeddings = _nested_collection_values(result, "embeddings")
    metadatas = _nested_collection_values(result, "metadatas")
    distances = _nested_collection_values(result, "distances")

    matches: list[tuple[float, DocumentChunk]] = []
    for index, chunk_id in enumerate(ids):
        chunk = _chunk_from_chroma_values(
            chunk_id=chunk_id,
            excerpt=documents[index] if index < len(documents) else "",
            embedding=embeddings[index] if index < len(embeddings) else [],
            metadata=metadatas[index] if index < len(metadatas) and metadatas[index] else {},
        )
        distance = distances[index] if index < len(distances) else None
        score = 1.0 - float(distance) if isinstance(distance, (float, int)) else 0.0
        matches.append((score, chunk))
    return matches


def reset_document_store() -> None:
    _DOCUMENTS.clear()
    _CHUNKS.clear()
    if _using_chroma():
        collection = _chroma_collection()
        existing = collection.get(include=[])
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)


def _display_section(metadata: dict[str, Any], *, fallback: str) -> str:
    section = str(metadata.get("section") or "").strip()
    title = str(metadata.get("section_title") or "").strip()
    if section and title:
        return f"{section} - {title}"
    return section or title or fallback


def _using_chroma() -> bool:
    global _CHROMA_AVAILABLE
    if _CHROMA_AVAILABLE is not None:
        return _CHROMA_AVAILABLE
    try:
        import chromadb  # noqa: F401
    except ImportError:
        _CHROMA_AVAILABLE = False
    else:
        _CHROMA_AVAILABLE = True
    return _CHROMA_AVAILABLE


def _chroma_collection():
    global _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is not None:
        return _CHROMA_COLLECTION

    import chromadb

    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    _CHROMA_COLLECTION = client.get_or_create_collection(
        name="hr_policy_chunks",
        metadata={"hnsw:space": "cosine"},
    )
    return _CHROMA_COLLECTION


def _add_chunk_to_chroma(document: Document, chunk: DocumentChunk) -> None:
    collection = _chroma_collection()
    collection.add(
        ids=[chunk.id],
        documents=[chunk.excerpt],
        embeddings=[_embedding_to_chroma_vector(chunk.embedding)],
        metadatas=[
            {
                "document_id": chunk.document_id,
                "document_title": chunk.document_title,
                "document_status": document.status,
                "document_created_at": document.created_at,
                "document_chunk_count": document.chunk_count,
                "section": chunk.section or "",
                "page": chunk.page or -1,
                "visibility_roles_json": json.dumps(chunk.visibility_roles),
                "department_ids_json": json.dumps(chunk.department_ids),
                "chunk_metadata_json": json.dumps(chunk.metadata),
            }
        ],
    )


def _list_documents_from_chroma() -> list[Document]:
    result = _chroma_collection().get(include=["metadatas"])
    grouped: dict[str, dict[str, Any]] = {}
    for metadata in result.get("metadatas", []) or []:
        if not metadata:
            continue
        document_id = str(metadata.get("document_id", ""))
        if not document_id:
            continue
        grouped.setdefault(document_id, metadata)

    documents = []
    for document_id, metadata in grouped.items():
        documents.append(
            Document(
                id=document_id,
                title=str(metadata.get("document_title", "")),
                status=str(metadata.get("document_status", "indexed")),
                visibility_roles=_json_list(metadata.get("visibility_roles_json")),
                department_ids=_json_list(metadata.get("department_ids_json")),
                created_at=str(metadata.get("document_created_at", "")),
                chunk_count=int(metadata.get("document_chunk_count", 0)),
            )
        )
    return documents


def _list_chunks_from_chroma() -> list[DocumentChunk]:
    result = _chroma_collection().get(include=["documents", "embeddings", "metadatas"])
    chunks: list[DocumentChunk] = []
    ids = _collection_values(result, "ids")
    documents = _collection_values(result, "documents")
    embeddings = _collection_values(result, "embeddings")
    metadatas = _collection_values(result, "metadatas")
    for index, chunk_id in enumerate(ids):
        chunks.append(
            _chunk_from_chroma_values(
                chunk_id=chunk_id,
                excerpt=documents[index] if index < len(documents) and documents[index] else "",
                embedding=embeddings[index] if index < len(embeddings) else [],
                metadata=metadatas[index] if index < len(metadatas) and metadatas[index] else {},
            )
        )
    return chunks


def _collection_values(result: dict[str, Any], key: str) -> list:
    value = result.get(key)
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return value if isinstance(value, list) else list(value)


def _nested_collection_values(result: dict[str, Any], key: str) -> list:
    values = _collection_values(result, key)
    if values and isinstance(values[0], list):
        return values[0]
    return values


def _chunk_from_chroma_values(
    *,
    chunk_id: object,
    excerpt: object,
    embedding: object,
    metadata: dict[str, Any],
) -> DocumentChunk:
    page = int(metadata.get("page", -1))
    return DocumentChunk(
        id=str(chunk_id),
        document_id=str(metadata.get("document_id", "")),
        document_title=str(metadata.get("document_title", "")),
        section=str(metadata.get("section", "")) or None,
        excerpt=str(excerpt or ""),
        page=page if page >= 0 else None,
        visibility_roles=_json_list(metadata.get("visibility_roles_json")),
        department_ids=_json_list(metadata.get("department_ids_json")),
        embedding=[float(value) for value in _collection_vector_values(embedding)],
        metadata=_json_dict(metadata.get("chunk_metadata_json")),
    )


def _collection_vector_values(value: object) -> list:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    while isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if isinstance(value, list) and value and isinstance(value[0], list):
        value = value[0]
    return value if isinstance(value, list) else list(value)


def _embedding_to_chroma_vector(embedding: Embedding) -> list[float]:
    if isinstance(embedding, list):
        return _project_dense_vector([float(value) for value in embedding])

    vector = [0.0] * _LOCAL_DENSE_DIMENSIONS
    for token, weight in embedding.items():
        index = hash(token) % _LOCAL_DENSE_DIMENSIONS
        vector[index] += float(weight)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def _project_dense_vector(values: list[float]) -> list[float]:
    if len(values) == _LOCAL_DENSE_DIMENSIONS:
        return values

    vector = [0.0] * _LOCAL_DENSE_DIMENSIONS
    for index, value in enumerate(values):
        vector[index % _LOCAL_DENSE_DIMENSIONS] += value
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def _json_list(value: object) -> list:
    if not value:
        return []
    try:
        loaded = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return loaded if isinstance(loaded, list) else []


def _json_dict(value: object) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}
