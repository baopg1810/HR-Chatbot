from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
NUMBERED_HEADING_RE = re.compile(r"^(?:#+\s*)?(\d+(?:\.\d+){1,5})\.?\s*(.*)$")
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
ROMAN_RE = re.compile(r"^CHUONG\s+([IVXLCDM]+)\s*(?:[-:]\s*)?(.*)$", re.IGNORECASE)
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    number: str
    title: str
    raw: str
    is_chapter: bool = False


@dataclass(frozen=True, slots=True)
class RagChunk:
    content: str
    metadata: dict[str, Any]
    embedding_text: str


@dataclass(slots=True)
class SectionState:
    chapter: str = ""
    chapter_title: str = ""
    section: str = ""
    section_title: str = ""
    heading: Heading | None = None
    blocks: list[str] = field(default_factory=list)


def chunk_document(
    text: str,
    document_metadata: dict[str, Any],
    *,
    target_tokens: int = 700,
    max_tokens: int = 900,
    overlap_tokens: int = 100,
    created_at: str | None = None,
) -> list[RagChunk]:
    normalized = normalize_text(text)
    blocks = _split_blocks(normalized)
    chunks: list[RagChunk] = []
    state = SectionState()
    heading_counters = {level: 0 for level in range(2, 7)}

    for block in blocks:
        heading = detect_heading(block)
        if heading is None:
            if state.chapter and not state.chapter_title and state.heading and state.blocks == [state.heading.raw]:
                state.chapter_title = block
                state.blocks.append(block)
                continue
            state.blocks.append(block)
            continue

        if (
            heading.number == ""
            and heading.level == 1
            and state.chapter
            and not state.chapter_title
            and not _strip_accents(heading.title).upper().startswith("CHUONG")
        ):
            state.chapter_title = heading.title
            state.blocks.append(heading.raw)
            continue

        _flush_section(
            state,
            chunks=chunks,
            document_metadata=document_metadata,
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            created_at=created_at,
        )

        if heading.is_chapter:
            heading_counters = {level: 0 for level in range(2, 7)}
            state = SectionState(
                chapter=heading.number,
                chapter_title=heading.title,
                heading=heading,
                blocks=[heading.raw],
            )
            continue

        section_number = heading.number
        if not section_number:
            logical_level = min(max(heading.level, 2), 6)
            heading_counters[logical_level] += 1
            for deeper_level in range(logical_level + 1, 7):
                heading_counters[deeper_level] = 0
            current_chapter_number = _chapter_number(state.chapter)
            if current_chapter_number:
                parts = [str(current_chapter_number)]
                for level in range(2, logical_level + 1):
                    counter = heading_counters[level]
                    if counter:
                        parts.append(str(counter))
                section_number = ".".join(parts)

        state = SectionState(
            chapter=state.chapter,
            chapter_title=state.chapter_title,
            section=section_number,
            section_title=heading.title,
            heading=heading,
            blocks=[heading.raw],
        )

    _flush_section(
        state,
        chunks=chunks,
        document_metadata=document_metadata,
        target_tokens=target_tokens,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        created_at=created_at,
    )
    return chunks or [_fallback_chunk(normalized, document_metadata, created_at)]


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    lines = _remove_repeated_headers_footers(lines)
    lines = [line for line in lines if not _is_page_number(line)]
    normalized = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", normalized).strip()


def detect_heading(line: str) -> Heading | None:
    stripped = line.strip()
    if not stripped:
        return None

    normalized = _strip_accents(stripped).upper()
    chapter_match = ROMAN_RE.match(normalized)
    if chapter_match:
        raw_prefix = stripped[: len(chapter_match.group(0))].strip()
        title = stripped[len(raw_prefix) :].strip(" -:")
        number = f"CHUONG {chapter_match.group(1).upper()}"
        return Heading(level=1, number=number, title=title or chapter_match.group(2).strip(), raw=stripped, is_chapter=True)

    numbered_match = NUMBERED_HEADING_RE.match(stripped)
    if numbered_match:
        number = numbered_match.group(1)
        return Heading(
            level=number.count(".") + 1,
            number=number,
            title=numbered_match.group(2).strip(),
            raw=stripped,
        )

    markdown_match = MARKDOWN_HEADING_RE.match(stripped)
    if markdown_match:
        return Heading(level=len(markdown_match.group(1)), number="", title=markdown_match.group(2).strip(), raw=stripped)

    return None


def build_embedding_text(content: str, metadata: dict[str, Any]) -> str:
    lines = [f"Document: {metadata.get('document_name', '')}"]
    if metadata.get("chapter") or metadata.get("chapter_title"):
        lines.append(f"Chapter: {metadata.get('chapter', '')} - {metadata.get('chapter_title', '')}".strip(" -"))
    if metadata.get("section") or metadata.get("section_title"):
        lines.append(f"Section: {metadata.get('section', '')} - {metadata.get('section_title', '')}".strip(" -"))
    lines.extend(["", "Content:", content])
    return "\n".join(lines)


def _flush_section(
    section: SectionState,
    *,
    chunks: list[RagChunk],
    document_metadata: dict[str, Any],
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
    created_at: str | None,
) -> None:
    content = "\n\n".join(block for block in section.blocks if block.strip()).strip()
    if not content or (section.heading and content == section.heading.raw) or _all_blocks_are_headings(section.blocks):
        return

    split_chunks = [content]
    if approximate_tokens(content) > target_tokens:
        split_chunks = _split_long_blocks(section.blocks, max_tokens=max_tokens, overlap_tokens=overlap_tokens)

    for split_content in split_chunks:
        metadata = _chunk_metadata(
            document_metadata,
            chunk_index=len(chunks),
            chapter=section.chapter,
            chapter_title=section.chapter_title,
            section=section.section,
            section_title=section.section_title,
            policy_type=infer_policy_type(section.section_title, split_content),
            created_at=created_at,
        )
        chunks.append(RagChunk(content=split_content, metadata=metadata, embedding_text=build_embedding_text(split_content, metadata)))


def _fallback_chunk(text: str, document_metadata: dict[str, Any], created_at: str | None) -> RagChunk:
    metadata = _chunk_metadata(document_metadata, chunk_index=0, policy_type=infer_policy_type("", text), created_at=created_at)
    return RagChunk(content=text, metadata=metadata, embedding_text=build_embedding_text(text, metadata))


def _chunk_metadata(
    document_metadata: dict[str, Any],
    *,
    chunk_index: int,
    chapter: str = "",
    chapter_title: str = "",
    section: str = "",
    section_title: str = "",
    policy_type: str = "general",
    created_at: str | None = None,
) -> dict[str, Any]:
    return {
        "document_name": document_metadata.get("document_name", ""),
        "document_type": document_metadata.get("document_type", "hr_policy"),
        "language": document_metadata.get("language", "vi"),
        "chapter": chapter,
        "chapter_title": chapter_title,
        "section": section or f"chunk-{chunk_index + 1}",
        "section_title": section_title,
        "policy_type": policy_type,
        "chunk_index": chunk_index,
        "source_path": document_metadata.get("source_path", ""),
        "created_at": created_at or datetime.now(UTC).isoformat(),
    }


def _split_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current_table: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            blocks.append("\n".join(paragraph_lines).strip())
            paragraph_lines = []

    def flush_table() -> None:
        nonlocal current_table
        if current_table:
            blocks.append("\n".join(current_table).strip())
            current_table = []

    for line in text.splitlines():
        if detect_heading(line):
            flush_table()
            flush_paragraph()
            blocks.append(line.strip())
        elif TABLE_LINE_RE.match(line):
            flush_paragraph()
            current_table.append(line.strip())
        elif not line.strip():
            flush_table()
            flush_paragraph()
        else:
            flush_table()
            paragraph_lines.append(line.strip())

    flush_table()
    flush_paragraph()
    return [block for block in blocks if block]


def _split_long_blocks(blocks: list[str], max_tokens: int, overlap_tokens: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for block in blocks:
        block_tokens = approximate_tokens(block)
        if current and current_tokens + block_tokens > max_tokens:
            chunks.append("\n\n".join(current).strip())
            current = _overlap_blocks(current, overlap_tokens)
            current_tokens = sum(approximate_tokens(item) for item in current)

        if block_tokens > max_tokens and not _block_is_table(block):
            for sentence in re.split(r"(?<=[.!?])\s+", block):
                sentence = sentence.strip()
                if not sentence:
                    continue
                if current and current_tokens + approximate_tokens(sentence) > max_tokens:
                    chunks.append("\n\n".join(current).strip())
                    current = []
                    current_tokens = 0
                current.append(sentence)
                current_tokens += approximate_tokens(sentence)
        else:
            current.append(block)
            current_tokens += block_tokens

    if current:
        chunks.append("\n\n".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def _overlap_blocks(blocks: list[str], overlap_tokens: int) -> list[str]:
    overlap: list[str] = []
    overlap_count = 0
    for previous in reversed(blocks):
        if _block_is_table(previous):
            continue
        previous_tokens = approximate_tokens(previous)
        if overlap and overlap_count + previous_tokens > overlap_tokens:
            break
        overlap.insert(0, previous)
        overlap_count += previous_tokens
    return overlap


def infer_policy_type(section_title: str, content: str) -> str:
    haystack = _strip_accents(f"{section_title}\n{content}").lower()
    rules = [
        ("recruitment", ["tuyen dung"]),
        ("probation", ["thu viec"]),
        ("training", ["dao tao", "phat trien"]),
        ("salary", ["luong", "thu nhap"]),
        ("insurance", ["bao hiem", "cong doan"]),
        ("benefit", ["phuc loi", "sinh nhat", "kham suc khoe", "thai san"]),
        ("reward", ["khen thuong", "de bat", "thuong"]),
        ("discipline", ["ky luat", "vi pham", "buoc thoi viec", "tu y bo viec"]),
        ("complaint", ["khieu nai"]),
        ("working_time", ["thoi gian lam viec", "gio lam viec"]),
        ("leave", ["nghi phep", "nghi khong huong luong", "nghi theo che do", "nghi om", "ket hon", "tang"]),
        ("holiday", ["nghi le", "le tet"]),
        ("dress_code", ["dong phuc", "trang phuc", "tac phong"]),
        ("company_access", ["ra vao cong ty", "the nhan vien"]),
        ("internet_email_data", ["internet", "email", "mang noi bo", "du lieu"]),
        ("phone", ["dien thoai"]),
        ("asset_management", ["tai san"]),
        ("guest_policy", ["tiep khach"]),
        ("emergency", ["khan cap"]),
        ("code_of_conduct", ["ung xu"]),
        ("privacy", ["bao mat", "rieng tu"]),
        ("fairness", ["cong bang"]),
        ("external_relations", ["doi ngoai"]),
        ("customer_partner", ["khach hang", "doi tac"]),
        ("conflict_of_interest", ["xung dot loi ich"]),
        ("employee_relationship", ["quan he nhan vien", "dong nghiep"]),
        ("company_intro", ["gioi thieu chung"]),
    ]
    for policy_type, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return policy_type
    return "general"


def approximate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


def _all_blocks_are_headings(blocks: list[str]) -> bool:
    return bool(blocks) and all(detect_heading(block) is not None for block in blocks)


def _block_is_table(block: str) -> bool:
    lines = [line for line in block.splitlines() if line.strip()]
    return bool(lines) and all(TABLE_LINE_RE.match(line) for line in lines)


def _chapter_number(chapter: str) -> int | None:
    match = re.search(r"\b([IVXLCDM]+)\b$", chapter, flags=re.IGNORECASE)
    return _roman_to_int(match.group(1)) if match else None


def _roman_to_int(value: str) -> int | None:
    total = 0
    previous = 0
    for char in reversed(value.upper()):
        current = ROMAN_VALUES.get(char)
        if current is None:
            return None
        total = total - current if current < previous else total + current
        previous = max(previous, current)
    return total


def _is_page_number(line: str) -> bool:
    return bool(re.match(r"^\s*(?:trang\s*)?\d+\s*(?:/\s*\d+)?\s*$", _strip_accents(line), re.IGNORECASE))


def _remove_repeated_headers_footers(lines: list[str]) -> list[str]:
    stripped_lines = [line.strip() for line in lines if line.strip()]
    counts = Counter(stripped_lines)
    repeated = {
        line
        for line, count in counts.items()
        if count >= 3
        and len(line) <= 120
        and detect_heading(line) is None
        and not _is_page_number(line)
    }
    return [line for line in lines if line.strip() not in repeated]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))
