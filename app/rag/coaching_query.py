"""Opt-in coaching query recovery; at most two local searches, no model I/O."""

from __future__ import annotations

from dataclasses import replace
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import KnowledgeQuery, KnowledgeSearchResult
from .provider import KnowledgeProvider
from .retriever import tokenize


POLICY_ID = "coaching-query-recovery-v1"
# This text is intended for a future candidate-only trusted context section.
# It is deliberately not copied into retrieval diagnostics or evidence
# artifacts, which must remain body-free.
COACHING_QUERY_GUIDANCE_V1 = (
    "知识库是中文教练方法资料。检索时使用明确的教练概念（如早期死亡、生存、补刀经济、"
    "事实与复盘假设、训练目标），不要把账号或整段比赛数据当关键词。若工具仍返回零片段，"
    "可在既有工具预算内澄清相关概念后再查；无相关资料时说明证据不足，不能虚构来源或引用。"
)
Topic = Literal["review", "survival", "economy", "vision", "damage", "training", "sample", "unmapped"]
Reason = Literal["insufficient_evidence", "no_applicable_evidence", "unresolved_conflict", "evidence_available", "unknown"]
_REASONS = {"insufficient_evidence", "no_applicable_evidence", "unresolved_conflict", "evidence_available"}

# Natural-language wrappers which do not carry domain meaning themselves.
# Keeping this allowlist small prevents an arbitrary query containing a topic
# word (for example, “股票复盘”) from receiving an unrelated expansion.
_SAFE_QUERY_WRAPPERS = (
    "请帮我",
    "可以帮我",
    "能帮我",
    "帮我",
    "请",
    "我想",
    "我想知道",
    "帮忙",
    "看看",
    "看一下",
    "分析",
    "分析一下",
    "了解",
    "说明",
    "告诉我",
    "最近",
    "早期",
    "前期",
    "这几局",
    "最近几局",
    "当前",
    "我的",
    "我",
    "的",
    "一下",
    "情况",
    "状态",
    "表现",
    "问题",
    "事实",
    "相关性",
    "相关资料",
    "资料",
    "相关",
    "假设",
    "证据",
    "方法",
    "回看",
    "录像",
    "重点",
    "建议",
    "如何",
    "怎么",
    "哪些",
    "有没有",
    "需要",
    "调整",
    "上分",
    "吗",
    "呢",
    "please",
    "can you",
    "could you",
    "help me",
    "tell me",
    "look at",
    "analyze",
    "analysis",
    "my",
    "me",
    "recent",
    "games",
    "game",
    "matches",
    "match",
    "for",
    "form",
    "evidence",
    "facts",
    "assumption",
    "state",
    "situation",
    "what should i do",
)
_SAFE_QUERY_WRAPPER_PATTERN = tuple(
    sorted(_SAFE_QUERY_WRAPPERS, key=len, reverse=True)
)
_ASCII_WORD = re.compile(r"[a-z0-9]+")

# Generic coaching vocabulary, not case IDs, oracle answers or corpus excerpts.
_TOPICS = (
    ("review", ("复盘", "赛后复盘", "复盘方法", "review", "post-game review", "recent form"), "复盘 事实 相关性 假设 证据"),
    ("survival", ("生存", "阵亡", "死亡", "survival", "deaths", "early deaths"), "早期死亡 生存 风险 录像 复盘"),
    ("economy", ("补刀", "经济", "发育", "cs", "farming", "economy"), "补刀 经济 发育 位置 对局时长"),
    ("vision", ("视野", "插眼", "vision", "warding"), "视野 信息 目标资源 安全 范围"),
    ("damage", ("伤害", "输出", "damage", "damage share"), "伤害 输出占比 英雄定位 经济 参团"),
    ("training", ("训练", "练习", "training", "practice"), "训练 目标 观察 指标 假设 验证"),
    ("sample", ("样本", "胜率", "连败", "sample size", "win rate", "losing streak"), "样本 数量 胜负 差异 相关性 假设"),
)


class RetrievalAttemptDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_count: int | None = Field(default=None, ge=0)
    applicable_count: int | None = Field(default=None, ge=0)
    supported_count: int | None = Field(default=None, ge=0)
    returned_count: int = Field(ge=0)
    reason: Reason

    @model_validator(mode="after")
    def validate_counts(self):
        counts = (self.candidate_count, self.applicable_count, self.supported_count, self.returned_count)
        known = [count for count in counts if count is not None]
        if any(right > left for left, right in zip(known, known[1:])):
            raise ValueError("retrieval counts must not increase through filtering")
        return self


class CoachingRetrievalDiagnostics(BaseModel):
    """Only fixed labels/counts; never query text or filter values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: Literal["coaching-query-recovery-v1"] = POLICY_ID
    topic: Topic
    query_term_count: int = Field(ge=0)
    filter_names: tuple[Literal["as_of", "position", "version"], ...] = ()
    attempts: tuple[RetrievalAttemptDiagnostics, ...] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def validate_recovery(self):
        if tuple(sorted(set(self.filter_names))) != self.filter_names:
            raise ValueError("filter names must be unique and sorted")
        if len(self.attempts) == 2 and (
            self.topic == "unmapped"
            or self.attempts[0].returned_count != 0
            or self.attempts[0].reason != "insufficient_evidence"
        ):
            raise ValueError("only recognized insufficient-evidence queries can recover")
        return self


def _topic(text: str) -> tuple[Topic, str | None]:
    normalized = _normalize(text)
    candidates: set[tuple[Topic, str]] = set()
    for topic, aliases, terms in _TOPICS:
        for alias in sorted(aliases, key=len, reverse=True):
            if not _contains_alias(normalized, alias):
                continue
            remainder = _remove_alias(normalized, alias)
            if _is_safe_wrapper(remainder):
                candidates.add((topic, terms))
    # A query which mixes concepts is intentionally left to the original
    # retriever.  Expanding one arbitrarily would be an unsafe semantic guess.
    if len(candidates) == 1:
        return next(iter(candidates))
    return "unmapped", None


def _normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Punctuation is a separator; retaining only normalized text makes the
    # wrapper check deterministic across the common Chinese/English forms.
    text = text.casefold().replace("\u3000", " ")
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
    return " ".join(text.split())


def _contains_alias(normalized: str, alias: str) -> bool:
    alias = _normalize(alias)
    if not alias:
        return False
    if _ASCII_WORD.fullmatch(alias):
        return re.search(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
            normalized,
        ) is not None
    if any(character.isascii() and character.isalnum() for character in alias):
        return re.search(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
            normalized,
        ) is not None
    return alias in normalized


def _remove_alias(normalized: str, alias: str) -> str:
    alias = _normalize(alias)
    if _ASCII_WORD.fullmatch(alias) or any(
        character.isascii() and character.isalnum() for character in alias
    ):
        return re.sub(
            rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
            " ",
            normalized,
            count=1,
        )
    return normalized.replace(alias, " ", 1)


def _is_safe_wrapper(remainder: str) -> bool:
    value = remainder
    for phrase in _SAFE_QUERY_WRAPPER_PATTERN:
        value = value.replace(phrase, " ")
    value = re.sub(r"\d+", " ", value)
    return not value.strip()


def _attempt(result: KnowledgeSearchResult) -> RetrievalAttemptDiagnostics:
    raw = result.diagnostics
    counts = {}
    for name in ("candidate_count", "applicable_count", "supported_count"):
        value = raw.get(name)
        counts[name] = value if type(value) is int and value >= 0 else None
    reason = raw.get("reason")
    return RetrievalAttemptDiagnostics(
        **counts,
        returned_count=len(result.hits),
        reason=reason if isinstance(reason, str) and reason in _REASONS else "unknown",
    )


class CoachingQueryKnowledgeProvider:
    """Preserve evidence policy and attribution while recovering known terse intents."""

    provider_name = "candidate-coaching-query-recovery"

    def __init__(self, base: KnowledgeProvider) -> None:
        self._base = base

    def search(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        topic, terms = _topic(query.text)
        result = self._base.search(query)
        attempts = [_attempt(result)]
        if (
            not result.hits
            and result.abstained
            and attempts[0].reason == "insufficient_evidence"
            and terms is not None
        ):
            expanded = KnowledgeQuery(
                text=f"{query.text} {terms}", top_k=query.top_k, filters=query.filters
            )
            result = self._base.search(expanded)
            attempts.append(_attempt(result))
        diagnostics = CoachingRetrievalDiagnostics(
            topic=topic,
            query_term_count=len(set(tokenize(query.text))),
            filter_names=tuple(sorted(query.filters)),
            attempts=tuple(attempts),
        )
        payload = {
            **result.diagnostics,
            "query_recovery": diagnostics.model_dump(mode="json"),
        }
        return replace(result, query=query, diagnostics=payload)
