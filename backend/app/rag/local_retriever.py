from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

STOPWORDS = {
    "anh",
    "ban",
    "bi",
    "cac",
    "can",
    "cho",
    "chinh",
    "co",
    "cong",
    "cua",
    "duoc",
    "gi",
    "hoi",
    "khong",
    "la",
    "lam",
    "may",
    "mot",
    "nao",
    "nhan",
    "nhu",
    "sach",
    "the",
    "thi",
    "toi",
    "ty",
    "va",
    "viec",
    "vien",
}


def keyword_score(question: str, content: str, metadata: dict[str, Any] | None = None) -> float:
    metadata = metadata or {}
    searchable = "\n".join(
        [
            str(metadata.get("section_title", "")),
            str(metadata.get("chapter_title", "")),
            str(metadata.get("policy_type", "")),
            content,
        ]
    )
    query_terms = _tokenize(question)
    if not query_terms:
        return 0.0

    content_terms = Counter(_tokenize(searchable))
    normalized_content = " ".join(_tokenize(searchable))
    score = 0.0
    for term in query_terms:
        tf = content_terms.get(term, 0)
        if tf:
            score += 1.0 + math.log(tf)

    for width in (2, 3):
        for index in range(0, max(0, len(query_terms) - width + 1)):
            phrase = " ".join(query_terms[index : index + width])
            if phrase in normalized_content:
                score += 2.5 * width
    return score


def has_keyword_overlap(question: str, content: str, metadata: dict[str, Any] | None = None) -> bool:
    metadata = metadata or {}
    searchable = "\n".join([str(metadata.get("section_title", "")), str(metadata.get("policy_type", "")), content])
    return bool(set(_tokenize(question)).intersection(_tokenize(searchable)))


def _tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    tokens = re.findall(r"[a-z0-9.%/]+", ascii_text)
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]
