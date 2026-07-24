from datetime import date

from app.rag.models import KnowledgeHit, KnowledgeMetadata, KnowledgeQuery
from app.rag.policy import EvidencePolicy


def hit(
    name: str,
    *,
    source: str,
    content: str,
    bm25_score: float = 30.0,
    bm25_rank: int = 1,
    dense_rank: int = 1,
    version: str = "evergreen",
    updated_at: date | None = date(2026, 7, 24),
    valid_from: date | None = None,
    valid_until: date | None = None,
    positions: tuple[str, ...] = ("ALL",),
    knowledge_key: str | None = None,
) -> KnowledgeHit:
    return KnowledgeHit(
        chunk_id=f"child-{name}",
        parent_id=f"parent-{name}",
        content=content,
        matched_content=content,
        score=0.03,
        rank=bm25_rank,
        metadata=KnowledgeMetadata(
            source_id=source,
            title=name,
            version=version,
            updated_at=updated_at,
            valid_from=valid_from,
            valid_until=valid_until,
            positions=positions,
            attributes={
                "bm25_score": bm25_score,
                "bm25_rank": bm25_rank,
                "dense_rank": dense_rank,
                "knowledge_key": knowledge_key or name,
            },
        ),
    )


def test_policy_abstains_when_lexical_support_is_too_weak():
    outcome = EvidencePolicy().apply(
        KnowledgeQuery(text="今天北京天气降雨", top_k=3),
        (
            hit(
                "unrelated",
                source="rules.md",
                content="当前版本复盘规则",
                bm25_score=3.0,
            ),
        ),
    )

    assert outcome.abstained is True
    assert outcome.hits == ()
    assert outcome.diagnostics["reason"] == "insufficient_evidence"


def test_policy_diversifies_sources_after_reranking():
    outcome = EvidencePolicy().apply(
        KnowledgeQuery(text="早期死亡差异复盘", top_k=2),
        (
            hit(
                "first",
                source="metric.md",
                content="早期死亡差异复盘",
                bm25_rank=1,
            ),
            hit(
                "duplicate-source",
                source="metric.md",
                content="早期死亡差异复盘规则",
                bm25_rank=2,
            ),
            hit(
                "second-source",
                source="method.md",
                content="早期死亡差异需要复盘",
                bm25_rank=3,
            ),
        ),
    )

    assert [row.metadata.source_id for row in outcome.hits] == [
        "metric.md",
        "method.md",
    ]
    assert outcome.diagnostics["rejected_for_diversity"] == 1


def test_policy_filters_version_position_and_expired_knowledge():
    query = KnowledgeQuery(
        text="中路视野规则",
        top_k=3,
        filters={
            "version": "16.14",
            "position": "MIDDLE",
            "as_of": "2026-07-24",
        },
    )
    outcome = EvidencePolicy().apply(
        query,
        (
            hit(
                "applicable",
                source="current.md",
                content="中路视野规则",
                version="16.14",
                positions=("MIDDLE",),
                valid_until=date(2026, 8, 1),
            ),
            hit(
                "wrong-version",
                source="old-patch.md",
                content="中路视野规则",
                version="16.13",
                positions=("MIDDLE",),
            ),
            hit(
                "expired",
                source="expired.md",
                content="中路视野规则",
                version="16.14",
                positions=("MIDDLE",),
                valid_until=date(2026, 7, 1),
            ),
            hit(
                "wrong-position",
                source="top.md",
                content="中路视野规则",
                version="16.14",
                positions=("TOP",),
            ),
        ),
    )

    assert [row.metadata.source_id for row in outcome.hits] == ["current.md"]
    assert outcome.diagnostics["applicable_count"] == 1


def test_policy_rejects_unresolved_same_priority_conflicts():
    outcome = EvidencePolicy().apply(
        KnowledgeQuery(text="视野规则判断", top_k=3),
        (
            hit(
                "claim-a",
                source="a.md",
                content="视野规则判断支持结论 A",
                knowledge_key="vision-rule",
            ),
            hit(
                "claim-b",
                source="b.md",
                content="视野规则判断支持结论 B",
                knowledge_key="vision-rule",
            ),
        ),
    )

    assert outcome.abstained is True
    assert outcome.diagnostics["reason"] == "unresolved_conflict"
    assert outcome.diagnostics["conflict_keys"] == ["vision-rule"]


def test_policy_keeps_newest_revision_for_the_same_knowledge_key():
    outcome = EvidencePolicy().apply(
        KnowledgeQuery(text="视野规则判断", top_k=3),
        (
            hit(
                "old",
                source="old.md",
                content="视野规则判断旧版本",
                updated_at=date(2026, 7, 1),
                knowledge_key="vision-rule",
            ),
            hit(
                "new",
                source="new.md",
                content="视野规则判断新版本",
                updated_at=date(2026, 7, 24),
                knowledge_key="vision-rule",
            ),
        ),
    )

    assert [row.metadata.source_id for row in outcome.hits] == ["new.md"]
