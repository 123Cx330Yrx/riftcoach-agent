from pathlib import Path

import pytest

from app.rag.documents import load_markdown_corpus, parse_markdown_document


def test_structured_markdown_builds_attributable_parent_and_child_chunks():
    text = """---
source_id: rules.md
knowledge_type: review_rule
version: 16.13
updated_at: 2026-07-23
positions: MIDDLE, TOP
---
# 复盘规则

## 统计边界

相关性不能直接写成因果。

需要结合录像验证。
"""

    parents, children = parse_markdown_document(
        source_name="rules.md",
        text=text,
        child_max_chars=80,
    )

    assert len(parents) == 1
    assert len(children) == 1
    assert children[0].parent_id == parents[0].parent_id
    assert parents[0].metadata.source_id == "rules.md"
    assert parents[0].metadata.knowledge_type == "review_rule"
    assert parents[0].metadata.version == "16.13"
    assert parents[0].metadata.positions == ("MIDDLE", "TOP")
    assert parents[0].metadata.updated_at.isoformat() == "2026-07-23"
    assert "## 统计边界" in parents[0].content
    assert "统计边界" in children[0].content


def test_long_section_is_split_but_each_child_points_to_the_same_parent():
    long_paragraphs = "\n\n".join(["甲" * 60, "乙" * 60, "丙" * 60])
    text = f"# 文档\n\n## 长章节\n\n{long_paragraphs}"

    parents, children = parse_markdown_document(
        source_name="long.md",
        text=text,
        child_max_chars=80,
    )

    assert len(parents) == 1
    assert len(children) == 3
    assert {child.parent_id for child in children} == {parents[0].parent_id}
    assert all(len(child.content) <= 80 + len("长章节\n") for child in children)


def test_chunk_ids_are_deterministic_and_change_with_content():
    first = parse_markdown_document(
        source_name="rules.md",
        text="# 文档\n## 规则\n原始内容",
    )
    same = parse_markdown_document(
        source_name="rules.md",
        text="# 文档\n## 规则\n原始内容",
    )
    changed = parse_markdown_document(
        source_name="rules.md",
        text="# 文档\n## 规则\n修改内容",
    )

    assert first[0][0].parent_id == same[0][0].parent_id
    assert first[1][0].child_id == same[1][0].child_id
    assert first[0][0].parent_id != changed[0][0].parent_id


def test_invalid_front_matter_fails_explicitly_without_exposing_content():
    with pytest.raises(ValueError, match="invalid.md") as error:
        parse_markdown_document(
            source_name="invalid.md",
            text="---\nupdated_at: not-a-date\n---\n# Secret\n## Rule\nprivate",
        )

    assert "private" not in str(error.value)


def test_project_knowledge_documents_load_as_a_corpus():
    corpus = load_markdown_corpus(Path("data/rag_docs"))

    assert len(corpus.parents) == 13
    assert len(corpus.children) >= len(corpus.parents)
    assert all(parent.metadata.updated_at is not None for parent in corpus.parents)
    assert all(child.parent_id in corpus.parent_by_id() for child in corpus.children)
