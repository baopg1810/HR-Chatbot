from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
import os

from app.core.config import get_settings
from app.models.schemas import Citation, User
from app.rag.local_retriever import has_keyword_overlap, keyword_score
from app.services.llm import cosine_similarity, embed_query_text, has_meaningful_sparse_overlap

MIN_SCORE = 0.18
TOP_K = 5
SEMANTIC_WEIGHT = 0.7
LEXICAL_WEIGHT = 0.45
SEMANTIC_ONLY_FACTOR = 0.5
GENERIC_TOKENS = {
    "chinh",
    "sach",
    "noi",
    "bo",
    "hr",
    "nhan",
    "vien",
    "quy",
    "trinh",
}


@dataclass
class HybridCandidate:
    chunk: object
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    rerank_score: float | None = None

    @property
    def score(self) -> float:
        semantic_score = max(self.semantic_score, 0.0)
        if self.lexical_score <= 0:
            semantic_score *= SEMANTIC_ONLY_FACTOR
        return (SEMANTIC_WEIGHT * semantic_score) + (LEXICAL_WEIGHT * self.lexical_score)


def embed_text(text: str) -> dict[str, float]:
    vector: dict[str, float] = {}
    for token in _tokens(text):
        vector[token] = vector.get(token, 0.0) + 1.0
    return vector


def search_policy_chunks(query: str, user: User, limit: int = TOP_K) -> list[Citation]:
    from app.services.documents import list_chunks, query_chunks

    query_vector = embed_query_text(query)
    all_chunks = [
        chunk
        for chunk in list_chunks()
        if _can_user_read_chunk(user, chunk.visibility_roles, chunk.department_ids)
    ]
    if not all_chunks:
        return []

    candidates: dict[str, HybridCandidate] = {}
    candidate_limit = max(limit * 8, 40)

    for semantic_score, chunk in query_chunks(query_vector, limit=candidate_limit):
        if not _can_user_read_chunk(user, chunk.visibility_roles, chunk.department_ids):
            continue
        _candidate_for(candidates, chunk).semantic_score = max(semantic_score, 0.0)

    semantic_candidate_ids = set(candidates)
    for chunk in all_chunks:
        lexical_score = keyword_score(query, chunk.excerpt, chunk.metadata)
        lexical_match = lexical_score > 0 or _has_lexical_policy_overlap(
            query,
            chunk.document_title,
            chunk.excerpt,
            chunk.metadata,
        )
        if lexical_match:
            candidate = _candidate_for(candidates, chunk)
            candidate.lexical_score = max(candidate.lexical_score, _normalize_lexical_score(lexical_score))
            if chunk.id not in semantic_candidate_ids:
                candidate.semantic_score = max(candidate.semantic_score, cosine_similarity(query_vector, chunk.embedding))

    if not semantic_candidate_ids:
        for chunk in all_chunks:
            if not _has_meaningful_overlap(query_vector, chunk.embedding):
                continue
            semantic_score = cosine_similarity(query_vector, chunk.embedding)
            if semantic_score >= MIN_SCORE:
                _candidate_for(candidates, chunk).semantic_score = max(semantic_score, 0.0)

    scored = [
        candidate
        for candidate in candidates.values()
        if (candidate.semantic_score >= MIN_SCORE or candidate.lexical_score > 0)
        and candidate.score >= MIN_SCORE
    ]
    scored.sort(key=lambda item: item.score, reverse=True)
    scored = _rerank_candidates(query, scored, limit)
    return [
        Citation(
            document_id=candidate.chunk.document_id,
            document_title=candidate.chunk.document_title,
            section=candidate.chunk.section,
            excerpt=candidate.chunk.excerpt,
            page=candidate.chunk.page,
            score=round(candidate.rerank_score if candidate.rerank_score is not None else candidate.score, 4),
        )
        for candidate in scored
    ]


def user_has_readable_chunks(user: User) -> bool:
    from app.services.documents import list_chunks

    return any(
        _can_user_read_chunk(user, chunk.visibility_roles, chunk.department_ids)
        for chunk in list_chunks()
    )


def _has_meaningful_overlap(a, b) -> bool:
    return has_meaningful_sparse_overlap(a, b, GENERIC_TOKENS)


def _candidate_for(candidates: dict[str, HybridCandidate], chunk) -> HybridCandidate:
    candidate = candidates.get(chunk.id)
    if candidate is None:
        candidate = HybridCandidate(chunk=chunk)
        candidates[chunk.id] = candidate
    return candidate


def _normalize_lexical_score(score: float) -> float:
    return min(max(score, 0.0) / 20, 1.0)


def _rerank_candidates(query: str, candidates: list[HybridCandidate], limit: int) -> list[HybridCandidate]:
    if len(candidates) <= 1:
        return candidates[:limit]
    if _running_under_pytest():
        return candidates[:limit]

    settings = get_settings()
    if not settings.cohere_api_key:
        raise RuntimeError("COHERE_API_KEY is required for retrieval reranking.")

    rerank_limit = min(len(candidates), settings.cohere_rerank_candidate_limit)
    rerank_pool = candidates[:rerank_limit]
    response = _cohere_client(settings.cohere_api_key).rerank(
        model=settings.cohere_rerank_model,
        query=query,
        documents=[_candidate_rerank_text(candidate) for candidate in rerank_pool],
        top_n=min(limit, len(rerank_pool)),
        max_tokens_per_doc=settings.cohere_rerank_max_tokens_per_doc,
    )

    ordered: list[HybridCandidate] = []
    seen_indexes: set[int] = set()
    for result in response.results:
        index = int(result.index)
        if index < 0 or index >= len(rerank_pool) or index in seen_indexes:
            continue
        candidate = rerank_pool[index]
        candidate.rerank_score = float(result.relevance_score)
        ordered.append(candidate)
        seen_indexes.add(index)

    if len(ordered) < limit:
        ordered.extend(candidate for index, candidate in enumerate(candidates) if index not in seen_indexes)
    return ordered[:limit]


@lru_cache
def _cohere_client(api_key: str):
    import cohere

    return cohere.ClientV2(api_key=api_key)


def _candidate_rerank_text(candidate: HybridCandidate) -> str:
    metadata = candidate.chunk.metadata or {}
    fields = [
        f"document_title: {candidate.chunk.document_title}",
        f"section: {candidate.chunk.section or ''}",
        f"chapter_title: {metadata.get('chapter_title', '')}",
        f"section_title: {metadata.get('section_title', '')}",
        f"policy_type: {metadata.get('policy_type', '')}",
        f"text: {candidate.chunk.excerpt}",
    ]
    return "\n".join(fields)


def _running_under_pytest() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ


def _has_lexical_policy_overlap(query: str, title: str, excerpt: str, metadata: dict | None = None) -> bool:
    query_vector = embed_text(query)
    chunk_vector = embed_text(f"{title}\n{excerpt}")
    return bool((set(query_vector).intersection(chunk_vector)) - GENERIC_TOKENS) or has_keyword_overlap(
        query,
        f"{title}\n{excerpt}",
        metadata,
    )


def _can_user_read_chunk(user: User, visibility_roles: list[str], department_ids: list[str]) -> bool:
    if user.role not in visibility_roles:
        return False
    if not department_ids:
        return True
    return user.department_id in department_ids


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]{2,}", ascii_text)
