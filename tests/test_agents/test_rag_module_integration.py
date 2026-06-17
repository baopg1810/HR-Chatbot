import pytest

from src.models.schemas import DocumentCreate
from src.rag.chunking import chunk_document
from src.rag.local_retriever import keyword_score
from src.services.demo_users import DEMO_USERS
from src.services import documents
from src.services.documents import create_document, list_chunks, query_chunks, reset_document_store
from src.services.llm import embed_query_text
from src.services.retrieval import search_policy_chunks


@pytest.fixture(autouse=True)
def clean_document_store():
    reset_document_store()
    yield
    reset_document_store()


def test_section_chunker_preserves_heading_metadata():
    chunks = chunk_document(
        """
        CHUONG I - Chinh sach nhan su

        1.1 Nghi phep nam
        Nhan vien co 12 ngay nghi phep nam va can bao truoc 3 ngay lam viec.
        """,
        {"document_name": "So tay nhan vien", "source_path": "manual.md"},
    )

    assert chunks
    assert chunks[0].metadata["section"] == "1.1"
    assert chunks[0].metadata["section_title"] == "Nghi phep nam"
    assert chunks[0].metadata["policy_type"] == "leave"
    assert "Section: 1.1 - Nghi phep nam" in chunks[0].embedding_text


def test_section_chunker_handles_separate_chapter_title_and_repeated_headers():
    chunks = chunk_document(
        """
        So tay nhan vien

        CHUONG I
        Chinh sach nhan su

        1.1 Nghi phep nam
        Nhan vien co 12 ngay nghi phep nam moi nam.

        So tay nhan vien
        So tay nhan vien
        """,
        {"document_name": "So tay nhan vien", "source_path": "manual.md"},
    )

    assert chunks
    assert chunks[0].metadata["chapter"] == "CHUONG I"
    assert chunks[0].metadata["chapter_title"] == "Chinh sach nhan su"
    assert "So tay nhan vien" not in chunks[0].content


def test_document_ingestion_uses_rag_section_metadata_for_citations():
    create_document(
        DocumentCreate(
            title="So tay nhan vien",
            content="""
            CHUONG I - Chinh sach nhan su

            1.1 Nghi phep nam
            Nhan vien co 12 ngay nghi phep nam va can bao truoc 3 ngay lam viec.
            """,
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )

    stored_chunk = list_chunks()[0]
    citations = search_policy_chunks("Nhan vien co bao nhieu ngay nghi phep nam?", DEMO_USERS["employee@example.com"])

    assert stored_chunk.metadata["policy_type"] == "leave"
    assert citations
    assert citations[0].section == "1.1 - Nghi phep nam"


def test_chroma_query_returns_vector_candidates():
    create_document(
        DocumentCreate(
            title="So tay nhan vien",
            content="""
            1.1 Nghi phep nam
            Nhan vien co 12 ngay nghi phep nam va can bao truoc 3 ngay lam viec.
            """,
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )

    matches = query_chunks(embed_query_text("nghi phep nam"), limit=5)

    assert matches
    assert matches[0][1].document_title == "So tay nhan vien"


def test_hybrid_search_keeps_lexical_candidate_when_semantic_topk_misses(monkeypatch):
    create_document(
        DocumentCreate(
            title="Chinh sach nghi phep",
            content="1.1 Nghi phep nam\nNhan vien co 12 ngay nghi phep nam moi nam.",
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )
    create_document(
        DocumentCreate(
            title="Quy dinh tai san",
            content="1.1 Cap phat tai san\nCong ty cap laptop cho nhan vien.",
            visibility_roles=["employee", "hr_admin"],
            department_ids=[],
        )
    )
    chunks = list_chunks()
    asset_chunk = next(chunk for chunk in chunks if chunk.document_title == "Quy dinh tai san")
    monkeypatch.setattr(documents, "query_chunks", lambda query_embedding, limit=20: [(0.95, asset_chunk)])

    citations = search_policy_chunks("nghi phep nam", DEMO_USERS["employee@example.com"], limit=2)

    assert citations
    assert citations[0].document_title == "Chinh sach nghi phep"


def test_keyword_score_boosts_matching_policy_phrase():
    metadata = {"section_title": "Nghi phep nam", "policy_type": "leave"}
    matching = keyword_score("nghi phep nam", "Nhan vien co 12 ngay nghi phep nam.", metadata)
    unrelated = keyword_score("nghi phep nam", "Quy dinh cap phat tai san cong ty.", {})

    assert matching > unrelated
