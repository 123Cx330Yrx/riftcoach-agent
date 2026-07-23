from app.rag.bm25 import BM25Index
from app.rag.documents import ChildChunk
from app.rag.models import KnowledgeMetadata


def child(child_id: str, content: str) -> ChildChunk:
    return ChildChunk(
        child_id=child_id,
        parent_id=f"parent-{child_id}",
        content=content,
        metadata=KnowledgeMetadata(source_id=f"{child_id}.md", title=child_id),
    )


def test_bm25_ranks_the_matching_review_rule_first():
    index = BM25Index(
        (
            child("vision", "视野分 目标资源 信息准备 真眼"),
            child("economy", "经济分钟 补刀 发育路线"),
            child("safety", "实时辅助 自动操作 公平竞技"),
        )
    )

    results = index.search("输局视野分和真眼", top_k=2)

    assert results[0].child.child_id == "vision"
    assert results[0].score > results[1].score
    assert [result.rank for result in results] == [1, 2]


def test_bm25_length_normalization_avoids_rewarding_unrelated_padding():
    concise = child("concise", "视野分 信息准备")
    padded = child("padded", "视野分 信息准备 " + "无关内容 " * 100)
    index = BM25Index((concise, padded))

    results = index.search("视野分 信息准备", top_k=2)

    assert results[0].child.child_id == "concise"


def test_bm25_returns_empty_for_query_without_shared_terms():
    index = BM25Index((child("vision", "视野分 信息准备"),))

    assert index.search("北京天气降雨", top_k=3) == ()
