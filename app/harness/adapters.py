from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.tools.runtime import ToolRuntime

from .knowledge import knowledge_evidence_from_search_payloads
from .steps import (
    CoachDraft,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    GenerationRequest,
    KnowledgeEvidence,
    RetrievalRequest,
    RevisionRequest,
)


SummaryCompactor = Callable[[dict[str, Any]], dict[str, Any]]
RetrievalQueryBuilder = Callable[[dict[str, Any]], str]
RetrievalFilterBuilder = Callable[[dict[str, Any]], dict[str, Any]]
GenerationPromptBuilder = Callable[[dict[str, Any], str, str], str]
FactPackBuilder = Callable[[dict[str, Any]], dict[str, Any]]
EvaluationPromptBuilder = Callable[[dict[str, Any], str], str]
EvaluationResponseParser = Callable[[str], dict[str, Any]]
RevisionPromptBuilder = Callable[[str, dict[str, Any]], str]
RevisionValidator = Callable[[str, str], None]


class LocalRagAdapter:
    """Translate knowledge.search results into the Harness evidence contract."""

    def __init__(
        self,
        *,
        runtime: ToolRuntime,
        query_builder: RetrievalQueryBuilder,
        filter_builder: RetrievalFilterBuilder | None = None,
        top_k: int = 5,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        self.runtime = runtime
        self.query_builder = query_builder
        self.filter_builder = filter_builder
        self.top_k = top_k

    def retrieve(self, request: RetrievalRequest) -> KnowledgeEvidence:
        query = self.query_builder(dict(request.player_summary))
        filters = (
            self.filter_builder(dict(request.player_summary))
            if self.filter_builder is not None
            else {}
        )
        result = self.runtime.execute(
            "knowledge.search",
            {"query": query, "top_k": self.top_k, "filters": filters},
            metadata={"harness_step": "retrieve"},
        )
        data = _require_success(result, "knowledge.search")
        return knowledge_evidence_from_search_payloads((data,))


class ChatCoachGenerator:
    """Translate the generation step into one llm.chat tool call."""

    def __init__(
        self,
        *,
        runtime: ToolRuntime,
        system_prompt: str,
        summary_compactor: SummaryCompactor,
        prompt_builder: GenerationPromptBuilder,
        temperature: float = 0.3,
    ) -> None:
        self.runtime = runtime
        self.system_prompt = system_prompt
        self.summary_compactor = summary_compactor
        self.prompt_builder = prompt_builder
        self.temperature = temperature

    def generate(self, request: GenerationRequest) -> CoachDraft:
        summary = self.summary_compactor(dict(request.player_summary))
        prompt = self.prompt_builder(
            summary,
            request.deterministic_report,
            request.knowledge.context,
        )
        return CoachDraft(
            report=_chat_content(
                self.runtime,
                system_prompt=self.system_prompt,
                user_prompt=prompt,
                temperature=self.temperature,
                harness_step="generate",
            )
        )


class ChatEvaluationAdapter:
    """Reuse the deterministic fact pack and parser around llm.chat."""

    def __init__(
        self,
        *,
        runtime: ToolRuntime,
        system_prompt: str,
        fact_pack_builder: FactPackBuilder,
        prompt_builder: EvaluationPromptBuilder,
        response_parser: EvaluationResponseParser,
        temperature: float = 0.0,
    ) -> None:
        self.runtime = runtime
        self.system_prompt = system_prompt
        self.fact_pack_builder = fact_pack_builder
        self.prompt_builder = prompt_builder
        self.response_parser = response_parser
        self.temperature = temperature

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        fact_pack = self.fact_pack_builder(dict(request.player_summary))
        prompt = self.prompt_builder(fact_pack, request.report)
        content = _chat_content(
            self.runtime,
            system_prompt=self.system_prompt,
            user_prompt=prompt,
            temperature=self.temperature,
            harness_step="evaluate",
        )
        payload = self.response_parser(content)
        return EvaluationResult(
            score=payload["score"],
            verdict=EvaluationVerdict(payload["verdict"]),
            issues=tuple(payload.get("issues", [])),
            passed_checks=tuple(payload.get("passed_checks", [])),
            summary=payload.get("summary", ""),
        )


class ChatCoachReviser:
    """Perform bounded revision through llm.chat and preserve validation."""

    def __init__(
        self,
        *,
        runtime: ToolRuntime,
        system_prompt: str,
        prompt_builder: RevisionPromptBuilder,
        validator: RevisionValidator,
        temperature: float = 0.0,
    ) -> None:
        self.runtime = runtime
        self.system_prompt = system_prompt
        self.prompt_builder = prompt_builder
        self.validator = validator
        self.temperature = temperature

    def revise(self, request: RevisionRequest) -> CoachDraft:
        prompt = self.prompt_builder(
            request.report,
            _evaluation_payload(request.evaluation),
        )
        content = _chat_content(
            self.runtime,
            system_prompt=self.system_prompt,
            user_prompt=prompt,
            temperature=self.temperature,
            harness_step="revise",
        )
        self.validator(content, request.report)
        return CoachDraft(report=content)


def _chat_content(
    runtime: ToolRuntime,
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    harness_step: str,
) -> str:
    result = runtime.execute(
        "llm.chat",
        {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        },
        metadata={"harness_step": harness_step},
    )
    data = _require_success(result, "llm.chat")
    content = data["content"].strip()
    if not content:
        raise ValueError("Chat model returned empty content.")
    return content


def _require_success(result: Any, tool_name: str) -> dict[str, Any]:
    if not result.success:
        code = result.error.code if result.error is not None else "unknown"
        raise RuntimeError(f"{tool_name} failed with safe code: {code}")
    if result.data is None:
        raise RuntimeError(f"{tool_name} returned no data")
    return dict(result.data)


def _evaluation_payload(result: EvaluationResult) -> dict[str, Any]:
    return {
        "score": result.score,
        "verdict": result.verdict.value,
        "issues": [dict(issue) for issue in result.issues],
        "passed_checks": list(result.passed_checks),
        "summary": result.summary,
    }
