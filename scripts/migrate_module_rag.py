from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_settings


DEFAULT_CHUNKS_PATH = Path("Module RAG/data/processed/chunks_with_embeddings.json")
DEFAULT_COLLECTION = "hr_policy_chunks"
DEFAULT_DOCUMENT_ID = "doc-module-rag-so-tay-nhan-vien"
DEFAULT_TITLE = "So_tay_nhan_vien"
DEFAULT_ROLES = ["employee", "department_admin", "hr_admin"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Module RAG chunks into the app Chroma store.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--document-id", default=DEFAULT_DOCUMENT_ID)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--replace-collection", action="store_true")
    args = parser.parse_args()

    chunks = _load_chunks(args.chunks)
    if not chunks:
        raise SystemExit(f"No chunks found in {args.chunks}")

    import chromadb

    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    if args.replace_collection:
        try:
            client.delete_collection(args.collection)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"},
    )

    existing = collection.get(where={"document_id": args.document_id}, include=[])
    existing_ids = existing.get("ids", [])
    if existing_ids:
        collection.delete(ids=existing_ids)

    created_at = str(chunks[0].get("metadata", {}).get("created_at") or "")
    ids: list[str] = []
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, Any]] = []

    for index, chunk in enumerate(chunks, start=1):
        metadata = dict(chunk.get("metadata") or {})
        content = str(chunk.get("content") or "")
        embedding = chunk.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise SystemExit(f"Chunk {index} does not include a usable embedding")

        metadata.setdefault("document_name", args.title)
        metadata.setdefault("document_type", "employee_handbook")
        metadata.setdefault("language", "vi")
        metadata["source_path"] = metadata.get("source_path") or str(args.chunks)
        metadata["chunk_index"] = int(metadata.get("chunk_index", index - 1))

        ids.append(f"{args.document_id}:chunk-{index}")
        documents.append(content)
        embeddings.append([float(value) for value in embedding])
        metadatas.append(
            {
                "document_id": args.document_id,
                "document_title": args.title,
                "document_status": "indexed",
                "document_created_at": created_at,
                "document_chunk_count": len(chunks),
                "section": _display_section(metadata, fallback=f"chunk-{index}"),
                "page": -1,
                "visibility_roles_json": json.dumps(DEFAULT_ROLES),
                "department_ids_json": json.dumps([]),
                "chunk_metadata_json": json.dumps(metadata, ensure_ascii=False),
            }
        )

    collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    print(
        f"Migrated {len(chunks)} chunks from {args.chunks} into "
        f"{settings.chroma_persist_dir}/{args.collection} as {args.document_id}"
    )


def _load_chunks(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("chunks"), list):
        return list(data["chunks"])
    if isinstance(data, list):
        return data
    raise ValueError("chunks file must be a list or an object with a 'chunks' list")


def _display_section(metadata: dict[str, Any], *, fallback: str) -> str:
    section = str(metadata.get("section") or "").strip()
    title = str(metadata.get("section_title") or "").strip()
    if section and title:
        return f"{section} - {title}"
    return section or title or fallback


if __name__ == "__main__":
    main()
