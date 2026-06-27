from __future__ import annotations

import math
import os
import re
import unicodedata
from functools import lru_cache
from threading import Lock
from typing import TYPE_CHECKING

from app.config import get_settings
from app.models.schemas import Citation

if TYPE_CHECKING:
    from app.services.guardrails import RefusalReason

SparseEmbedding = dict[str, float]
DenseEmbedding = list[float]
Embedding = SparseEmbedding | DenseEmbedding

_KEY_LOCK = Lock()
_NEXT_KEY_INDEX = 0


def embed_query_text(text: str) -> Embedding:
    return _embed_text(
        gemini_input=f"task: question answering | query: {text}",
        fallback_input=text,
    )


def embed_document_text(title: str, text: str) -> Embedding:
    return _embed_text(
        gemini_input=f"title: {title or 'none'} | text: {text}",
        fallback_input=f"{title}\n{text}",
    )


def embed_document_texts(title: str, texts: list[str]) -> list[Embedding]:
    if not texts:
        return []

    gemini_inputs = [f"title: {title or 'none'} | text: {text}" for text in texts]
    fallback_inputs = [f"{title}\n{text}" for text in texts]
    settings = get_settings()
    if not _configured_google_api_keys() and settings.app_env == "production":
        raise RuntimeError("Gemini API key is not configured.")
    if _configured_google_api_keys() and not _running_under_pytest():
        try:
            return _embed_with_gemini_batch(gemini_inputs)
        except Exception:
            if settings.app_env == "production":
                raise
    return [_local_embedding(text) for text in fallback_inputs]


def cosine_similarity(a: Embedding, b: Embedding) -> float:
    if not a or not b:
        return 0.0
    if isinstance(a, list) and isinstance(b, list):
        return _dense_cosine_similarity(a, b)
    if isinstance(a, dict) and isinstance(b, dict):
        return _sparse_cosine_similarity(a, b)
    return 0.0


def has_meaningful_sparse_overlap(
    a: Embedding,
    b: Embedding,
    generic_tokens: set[str],
) -> bool:
    if isinstance(a, list) or isinstance(b, list):
        return True
    if isinstance(a, dict) and isinstance(b, dict):
        return bool((set(a).intersection(b)) - generic_tokens)
    return False


def build_cited_answer(query: str, citations: list[Citation]) -> str:
    if not citations:
        return (
            "Tôi chưa tìm thấy tài liệu HR phù hợp để trả lời có trích dẫn. "
            "Vui lòng bổ sung tài liệu hoặc chuyển câu hỏi cho HR."
        )

    prompt = _build_cited_prompt(query, citations)
    generated = _generate_with_gemini(prompt)
    if generated:
        return generated
    return _build_local_cited_answer(query, citations)


def stream_cited_answer(query: str, citations: list[Citation]):
    if not citations:
        yield (
            "Tôi chưa tìm thấy tài liệu HR phù hợp để trả lời có trích dẫn. "
            "Vui lòng bổ sung tài liệu hoặc chuyển câu hỏi cho HR."
        )
        return

    yielded = False
    for token in _stream_with_gemini(_build_cited_prompt(query, citations)):
        yielded = True
        yield token
    if not yielded:
        yield _build_local_cited_answer(query, citations)


def build_general_answer(query: str, user_name: str) -> str:
    prompt = (
        "Bạn là HR Helpdesk AI cho nhân viên Việt Nam.\n"
        "Trả lời bằng tiếng Việt có dấu, ngắn gọn, thân thiện.\n"
        "Nếu câu hỏi cần chính sách nội bộ cụ thể mà chưa có tài liệu trích dẫn, "
        "hãy nói rõ cần bổ sung tài liệu HR hoặc tạo ticket cho HR, không bịa quy định.\n\n"
        f"Nhân viên: {user_name}\n"
        f"Câu hỏi: {query}\n"
        "Câu trả lời:"
    )
    generated = _generate_with_gemini(prompt)
    if generated:
        return generated
    return (
        f"Xin chào {user_name}. Tôi có thể hỗ trợ các câu hỏi nhân sự, "
        "nhưng hiện chưa có tài liệu HR phù hợp để trả lời có trích dẫn. "
        "Bạn có thể upload tài liệu chính sách hoặc tạo ticket để HR xử lý."
    )


def stream_general_answer(query: str, user_name: str):
    prompt = (
        "Bạn là HR Helpdesk AI cho nhân viên Việt Nam.\n"
        "Trả lời bằng tiếng Việt có dấu, ngắn gọn, thân thiện.\n"
        "Nếu câu hỏi cần chính sách nội bộ cụ thể mà chưa có tài liệu trích dẫn, "
        "hãy nói rõ cần bổ sung tài liệu HR hoặc tạo ticket cho HR, không bịa quy định.\n\n"
        f"Nhân viên: {user_name}\n"
        f"Câu hỏi: {query}\n"
        "Câu trả lời:"
    )
    yielded = False
    for token in _stream_with_gemini(prompt):
        yielded = True
        yield token
    if not yielded:
        yield (
            f"Xin chào {user_name}. Tôi có thể hỗ trợ các câu hỏi nhân sự, "
            "nhưng hiện chưa có tài liệu HR phù hợp để trả lời có trích dẫn. "
            "Bạn có thể upload tài liệu chính sách hoặc tạo ticket để HR xử lý."
        )


def build_refusal_answer(reason: RefusalReason) -> str:
    messages = {
        "jailbreak": "Tôi không thể thực hiện yêu cầu bỏ qua hướng dẫn an toàn của hệ thống.",
        "outside_scope": "Tôi chỉ hỗ trợ các câu hỏi trong phạm vi chính sách và thủ tục nhân sự.",
        "sensitive": "Tôi không thể tiết lộ hoặc suy luận dữ liệu nhạy cảm của người khác.",
        "no_source": "Tôi chưa tìm thấy nguồn HR phù hợp để trả lời có trích dẫn nên không thể kết luận.",
    }
    return messages[reason]


def _build_cited_prompt(query: str, citations: list[Citation]) -> str:
    source_blocks = []
    for index, citation in enumerate(citations[:3], start=1):
        section = f" - {citation.section}" if citation.section else ""
        source_blocks.append(
            f"[{index}] {citation.document_title}{section}\n"
            f"{citation.excerpt}"
        )
    sources = "\n\n".join(source_blocks)
    return (
        "Bạn là HR Helpdesk AI. Hãy trả lời câu hỏi nhân sự bằng tiếng Việt có dấu.\n"
        "Chỉ sử dụng thông tin trong phần NGUỒN. Không bịa chính sách, số liệu hoặc điều kiện ngoài nguồn.\n"
        "Nếu nguồn không đủ để kết luận, hãy nói rõ phần chưa đủ và đề nghị chuyển HR.\n"
        "Trả lời tự nhiên, ngắn gọn, và nhắc tên tài liệu/điều mục liên quan khi phù hợp.\n\n"
        f"CÂU HỎI:\n{query}\n\n"
        f"NGUỒN:\n{sources}\n\n"
        "CÂU TRẢ LỜI:"
    )


def _build_local_cited_answer(query: str, citations: list[Citation]) -> str:
    primary = citations[0]
    source = _citation_source_summary(primary)
    sentence = _best_supported_sentence(query, primary.excerpt)
    if sentence:
        return f"Theo {source}, {sentence}"
    return (
        f"Theo {source}, "
        f"nội dung liên quan đến câu hỏi '{query}' là: {primary.excerpt[:700].strip()}"
    )


def _citation_source_summary(citation: Citation) -> str:
    if citation.section:
        return f"{citation.document_title} - {citation.section}"
    return citation.document_title


def _best_supported_sentence(query: str, excerpt: str) -> str | None:
    query_terms = set(_tokens(query))
    ranked: list[tuple[int, int, str]] = []
    for raw_sentence in re.split(r"(?<=[.!?])\s+|\n+", excerpt):
        sentence = raw_sentence.strip(" -•\t")
        if len(sentence) < 20 or sentence.startswith("|"):
            continue
        sentence_terms = set(_tokens(sentence))
        overlap = len(query_terms.intersection(sentence_terms))
        ranked.append((overlap, len(sentence), sentence))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if ranked and ranked[0][0] > 0:
        return ranked[0][2]
    return None


def _generate_with_gemini(prompt: str) -> str | None:
    settings = get_settings()
    keys = _ordered_google_api_keys()
    if not keys and settings.app_env == "production":
        raise RuntimeError("Gemini API key is not configured.")
    if not keys or _running_under_pytest():
        return None
    last_error: Exception | None = None
    for api_key in keys:
        try:
            result = _gemini_client(api_key).models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config={
                    "temperature": settings.llm_temperature,
                },
            )
        except Exception as exc:
            last_error = exc
            continue
        generated = _extract_generated_text(result)
        if generated:
            return generated
    if settings.app_env == "production" and last_error is not None:
        raise last_error
    return None


def _stream_with_gemini(prompt: str):
    settings = get_settings()
    keys = _ordered_google_api_keys()
    if not keys and settings.app_env == "production":
        raise RuntimeError("Gemini API key is not configured.")
    if not keys or _running_under_pytest():
        return
    last_error: Exception | None = None
    for api_key in keys:
        yielded = False
        try:
            stream = _gemini_client(api_key).models.generate_content_stream(
                model=settings.model_name,
                contents=prompt,
                config={
                    "temperature": settings.llm_temperature,
                },
            )
            for result in stream:
                generated = _extract_stream_text(result)
                if generated:
                    yielded = True
                    yield generated
        except Exception as exc:
            last_error = exc
            continue
        if yielded:
            return
    if settings.app_env == "production" and last_error is not None:
        raise last_error


def _extract_generated_text(result: object) -> str | None:
    text = getattr(result, "text", None)
    if text:
        return text.strip()
    candidates = getattr(result, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        pieces = [getattr(part, "text", "") for part in parts]
        joined = "\n".join(piece for piece in pieces if piece).strip()
        if joined:
            return joined
    return None


def _extract_stream_text(result: object) -> str | None:
    text = getattr(result, "text", None)
    if text:
        return text
    candidates = getattr(result, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        joined = "".join(getattr(part, "text", "") for part in parts)
        if joined:
            return joined
    return None


def _embed_text(gemini_input: str, fallback_input: str) -> Embedding:
    settings = get_settings()
    if not _configured_google_api_keys() and settings.app_env == "production":
        raise RuntimeError("Gemini API key is not configured.")
    if _configured_google_api_keys() and not _running_under_pytest():
        try:
            return _embed_with_gemini(gemini_input)
        except Exception:
            if settings.app_env == "production":
                raise
    return _local_embedding(fallback_input)


def _embed_with_gemini(text: str) -> DenseEmbedding:
    return _embed_with_gemini_batch([text])[0]


def _embed_with_gemini_batch(texts: list[str]) -> list[DenseEmbedding]:
    if not texts:
        return []

    settings = get_settings()
    keys = _ordered_google_api_keys()
    last_error: Exception | None = None
    for api_key in keys:
        try:
            return _request_gemini_embeddings(api_key, settings.embedding_model_name, texts)
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("Gemini API key is not configured.")


def _request_gemini_embeddings(api_key: str, model: str, texts: list[str]) -> list[DenseEmbedding]:
    batch_size = max(1, int(os.environ.get("GEMINI_EMBEDDING_BATCH_SIZE", "1")))
    embeddings: list[DenseEmbedding] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        result = _gemini_client(api_key).models.embed_content(model=model, contents=batch if len(batch) > 1 else batch[0])
        response_embeddings = list(getattr(result, "embeddings", None) or [])
        if len(response_embeddings) != len(batch) and len(batch) > 1:
            for text in batch:
                single_result = _gemini_client(api_key).models.embed_content(model=model, contents=text)
                embeddings.append(_extract_embedding_values(single_result, expected_index=0))
            continue
        if not response_embeddings:
            raise RuntimeError("Gemini embedding response did not include embeddings.")
        for index in range(len(batch)):
            embeddings.append(_extract_embedding_values(result, expected_index=index))
    return embeddings


def _extract_embedding_values(result: object, *, expected_index: int) -> DenseEmbedding:
    response_embeddings = list(getattr(result, "embeddings", None) or [])
    if expected_index >= len(response_embeddings):
        raise RuntimeError("Gemini embedding response returned fewer embeddings than expected.")
    values = getattr(response_embeddings[expected_index], "values", None)
    if values is None:
        raise RuntimeError("Gemini embedding response did not include vector values.")
    return [float(value) for value in values]


@lru_cache
def _gemini_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def _configured_google_api_keys() -> list[str]:
    settings = get_settings()
    raw_values = []
    if settings.google_api_key:
        raw_values.append(settings.google_api_key)
    raw_values.extend(_numbered_google_api_keys())
    if settings.google_api_keys:
        raw_values.extend(re.split(r"[\s,;]+", settings.google_api_keys))

    keys: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        key = value.strip()
        if not key or key in seen:
            continue
        keys.append(key)
        seen.add(key)
    return keys


def _numbered_google_api_keys() -> list[str]:
    indexed_keys: list[tuple[int, str]] = []
    for name, value in os.environ.items():
        match = re.fullmatch(r"GOOGLE_API_KEY_(\d+)", name)
        if match and value.strip():
            indexed_keys.append((int(match.group(1)), value.strip()))
    return [value for _, value in sorted(indexed_keys)]


def _ordered_google_api_keys() -> list[str]:
    keys = _configured_google_api_keys()
    if len(keys) <= 1:
        return keys

    global _NEXT_KEY_INDEX
    with _KEY_LOCK:
        start = _NEXT_KEY_INDEX % len(keys)
        _NEXT_KEY_INDEX += 1
    return keys[start:] + keys[:start]


def _local_embedding(text: str) -> SparseEmbedding:
    vector: SparseEmbedding = {}
    for token in _tokens(text):
        vector[token] = vector.get(token, 0.0) + 1.0
    return vector


def _sparse_cosine_similarity(a: SparseEmbedding, b: SparseEmbedding) -> float:
    shared = set(a).intersection(b)
    dot = sum(a[token] * b[token] for token in shared)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _dense_cosine_similarity(a: DenseEmbedding, b: DenseEmbedding) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(left * right for left, right in zip(a, b))
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]{2,}", ascii_text)


def _running_under_pytest() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ
