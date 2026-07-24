"""Structured Markdown ingestion and parent-child chunk construction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .models import KnowledgeMetadata


@dataclass(frozen=True)
class ParentChunk:
    parent_id: str
    content: str
    metadata: KnowledgeMetadata


@dataclass(frozen=True)
class ChildChunk:
    child_id: str
    parent_id: str
    content: str
    metadata: KnowledgeMetadata


@dataclass(frozen=True)
class KnowledgeCorpus:
    parents: tuple[ParentChunk, ...]
    children: tuple[ChildChunk, ...]

    def parent_by_id(self) -> dict[str, ParentChunk]:
        return {parent.parent_id: parent for parent in self.parents}


def load_markdown_corpus(
    knowledge_dir: Path,
    *,
    child_max_chars: int = 320,
) -> KnowledgeCorpus:
    if child_max_chars < 80:
        raise ValueError("child_max_chars must be at least 80.")
    if not knowledge_dir.exists():
        raise FileNotFoundError(f"Knowledge directory not found: {knowledge_dir}")

    parents: list[ParentChunk] = []
    children: list[ChildChunk] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        document_parents, document_children = parse_markdown_document(
            source_name=path.name,
            text=path.read_text(encoding="utf-8"),
            child_max_chars=child_max_chars,
        )
        parents.extend(document_parents)
        children.extend(document_children)

    if not children:
        raise RuntimeError(f"No indexable Markdown knowledge found in: {knowledge_dir}")
    return KnowledgeCorpus(parents=tuple(parents), children=tuple(children))


def parse_markdown_document(
    *,
    source_name: str,
    text: str,
    child_max_chars: int = 320,
) -> tuple[tuple[ParentChunk, ...], tuple[ChildChunk, ...]]:
    front_matter, body = _parse_front_matter(source_name, text)
    document_title, sections = _parse_sections(body)
    source_id = front_matter.get("source_id", source_name).strip()
    if not source_id:
        raise ValueError(f"Knowledge source_id is empty in {source_name}")

    knowledge_type = front_matter.get("knowledge_type", "unknown").strip()
    version = front_matter.get("version") or None
    updated_at = _parse_date(
        front_matter.get("updated_at"),
        source_name,
        field_name="updated_at",
    )
    valid_from = _parse_date(
        front_matter.get("valid_from"),
        source_name,
        field_name="valid_from",
    )
    valid_until = _parse_date(
        front_matter.get("valid_until"),
        source_name,
        field_name="valid_until",
    )
    positions = tuple(
        item.strip()
        for item in front_matter.get("positions", "").split(",")
        if item.strip()
    )

    parents: list[ParentChunk] = []
    children: list[ChildChunk] = []
    for section_title, section_body in sections:
        parent_content = f"## {section_title}\n\n{section_body}".strip()
        parent_id = _content_id("parent", source_id, section_title, parent_content)
        metadata = KnowledgeMetadata(
            source_id=source_id,
            title=section_title,
            knowledge_type=knowledge_type,
            version=version,
            updated_at=updated_at,
            valid_from=valid_from,
            valid_until=valid_until,
            positions=positions,
            attributes={
                "document_title": document_title,
                "knowledge_key": front_matter.get(
                    "knowledge_key",
                    f"{source_id}#{section_title}",
                ),
            },
        )
        parents.append(
            ParentChunk(
                parent_id=parent_id,
                content=parent_content,
                metadata=metadata,
            )
        )
        for child_body in _split_child_content(section_body, child_max_chars):
            child_content = f"{section_title}\n{child_body}".strip()
            children.append(
                ChildChunk(
                    child_id=_content_id(
                        "child",
                        source_id,
                        section_title,
                        child_content,
                    ),
                    parent_id=parent_id,
                    content=child_content,
                    metadata=metadata,
                )
            )
    return tuple(parents), tuple(children)


def _parse_front_matter(source_name: str, text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValueError(f"Unclosed front matter in {source_name}") from exc

    values: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid front matter line in {source_name}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key or key in values:
            raise ValueError(f"Invalid or duplicate front matter key in {source_name}")
        values[key] = value.strip()
    return values, "\n".join(lines[closing_index + 1 :])


def _parse_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    document_title = "Untitled"
    current_title: str | None = None
    current_lines: list[str] = []
    sections: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal current_lines
        content = "\n".join(current_lines).strip()
        if content:
            sections.append((current_title or document_title, content))
        current_lines = []

    for line in body.splitlines():
        if line.startswith("# "):
            if current_title is None:
                document_title = line[2:].strip() or document_title
            else:
                current_lines.append(line)
        elif line.startswith("## "):
            flush()
            current_title = line[3:].strip()
        else:
            current_lines.append(line)
    flush()
    return document_title, sections


def _split_child_content(content: str, max_chars: int) -> tuple[str, ...]:
    paragraphs = [paragraph.strip() for paragraph in content.split("\n\n") if paragraph.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph_parts = _hard_split(paragraph, max_chars)
        for part in paragraph_parts:
            candidate = f"{current}\n\n{part}".strip() if current else part
            if current and len(candidate) > max_chars:
                pieces.append(current)
                current = part
            else:
                current = candidate
    if current:
        pieces.append(current)
    return tuple(pieces)


def _hard_split(text: str, max_chars: int) -> tuple[str, ...]:
    return tuple(text[index : index + max_chars] for index in range(0, len(text), max_chars))


def _parse_date(
    value: str | None,
    source_name: str,
    *,
    field_name: str,
) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name} date in {source_name}") from exc


def _content_id(kind: str, source_id: str, title: str, content: str) -> str:
    digest = hashlib.sha256(
        f"{kind}\0{source_id}\0{title}\0{content}".encode("utf-8")
    ).hexdigest()[:16]
    return f"{source_id}:{kind}:{digest}"
