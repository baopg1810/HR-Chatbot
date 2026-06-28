from types import SimpleNamespace

import pytest

from app.models.schemas import DocumentCreate
from app.rag.chunking import chunk_document
from app.rag.local_retriever import keyword_score
from app.services.demo_users import DEMO_USERS
from app.services import documents, retrieval
from app.services.documents import create_document, list_chunks, query_chunks, reset_document_store
from app.services.llm import embed_query_text
from app.services.retrieval import search_policy_chunks


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


def test_cohere_rerank_reorders_hybrid_candidates(monkeypatch):
    class FakeRerankClient:
        def rerank(self, **kwargs):
            assert kwargs["model"] == "rerank-v4.0-pro"
            assert kwargs["top_n"] == 2
            assert kwargs["max_tokens_per_doc"] == 2048
            return SimpleNamespace(
                results=[
                    SimpleNamespace(index=1, relevance_score=0.96),
                    SimpleNamespace(index=0, relevance_score=0.42),
                ]
            )

    fake_settings = SimpleNamespace(
        cohere_api_key="test-cohere-key",
        cohere_rerank_model="rerank-v4.0-pro",
        cohere_rerank_candidate_limit=40,
        cohere_rerank_max_tokens_per_doc=2048,
    )
    first = retrieval.HybridCandidate(
        chunk=SimpleNamespace(
            document_title="Chinh sach chung",
            section="1.1",
            excerpt="Nhan vien tuan thu noi quy chung.",
            metadata={},
        ),
        semantic_score=0.9,
    )
    second = retrieval.HybridCandidate(
        chunk=SimpleNamespace(
            document_title="Chinh sach nghi phep",
            section="2.1",
            excerpt="Nhan vien co 12 ngay nghi phep nam.",
            metadata={"policy_type": "leave"},
        ),
        semantic_score=0.8,
    )

    monkeypatch.setattr(retrieval, "_running_under_pytest", lambda: False)
    monkeypatch.setattr(retrieval, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(retrieval, "_cohere_client", lambda _api_key: FakeRerankClient())

    reranked = retrieval._rerank_candidates("nghi phep nam", [first, second], limit=2)

    assert reranked == [second, first]
    assert reranked[0].rerank_score == 0.96


def test_keyword_score_boosts_matching_policy_phrase():
    metadata = {"section_title": "Nghi phep nam", "policy_type": "leave"}
    matching = keyword_score("nghi phep nam", "Nhan vien co 12 ngay nghi phep nam.", metadata)
    unrelated = keyword_score("nghi phep nam", "Quy dinh cap phat tai san cong ty.", {})

    assert matching > unrelated
