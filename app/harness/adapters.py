from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.rag.retriever import LocalKnowledgeRetriever, format_evidence

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
GenerationPromptBuilder = Callable[[dict[str, Any], str, str], str]
FactPackBuilder = Callable[[dict[str, Any]], dict[str, Any]]
EvaluationPromptBuilder = Callable[[dict[str, Any], str], str]
EvaluationResponseParser = Callable[[str], dict[str, Any]]
RevisionPromptBuilder = Callable[[str, dict[str, Any]], str]
RevisionValidator = Callable[[str, str], None]


class LocalRagAdapter:
    """Translate the local lexical retriever into the Harness retrieval contract."""

    def __init__(
        self,
        *,
        retriever: LocalKnowledgeRetriever,
        query_builder: RetrievalQueryBuilder,
        top_k: int = 5,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        self.retriever = retriever
        self.query_builder = query_builder
        self.top_k = top_k

    def retrieve(self, request: RetrievalRequest) -> KnowledgeEvidence:
        summary = dict(request.player_summary)
        query = self.query_builder(summary)
        chunks = self.retriever.search(query, top_k=self.top_k)
        source_ids = tuple(dict.fromkeys(chunk.source for chunk in chunks))
        return KnowledgeEvidence(
            context=format_evidence(chunks),
            source_ids=source_ids,
        )


class ChatCoachGenerator:
    """Adapt an OpenAI-compatible chat client to the Coach generation step."""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        system_prompt: str,
        summary_compactor: SummaryCompactor,
        prompt_builder: GenerationPromptBuilder,
        temperature: float = 0.3,
    ) -> None:
        self.client = client
        self.model = model
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
        content = _chat_content(
            self.client,
            model=self.model,
            system_prompt=self.system_prompt,
            user_prompt=prompt,
            temperature=self.temperature,
        )
        return CoachDraft(report=content)


class ChatEvaluationAdapter:
    """Reuse the existing fact pack, evaluation prompt, and parser."""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        system_prompt: str,
        fact_pack_builder: FactPackBuilder,
        prompt_builder: EvaluationPromptBuilder,
        response_parser: EvaluationResponseParser,
        temperature: float = 0.0,
    ) -> None:
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.fact_pack_builder = fact_pack_builder
        self.prompt_builder = prompt_builder
        self.response_parser = response_parser
        self.temperature = temperature

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        fact_pack = self.fact_pack_builder(dict(request.player_summary))
        prompt = self.prompt_builder(fact_pack, request.report)
        content = _chat_content(
            self.client,
            model=self.model,
            system_prompt=self.system_prompt,
            user_prompt=prompt,
            temperature=self.temperature,
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
    """Adapt bounded report revision and preserve the existing validator."""

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        system_prompt: str,
        prompt_builder: RevisionPromptBuilder,
        validator: RevisionValidator,
        temperature: float = 0.0,
    ) -> None:
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.prompt_builder = prompt_builder
        self.validator = validator
        self.temperature = temperature

    def revise(self, request: RevisionRequest) -> CoachDraft:
        evaluation = _evaluation_payload(request.evaluation)
        prompt = self.prompt_builder(request.report, evaluation)
        content = _chat_content(
            self.client,
            model=self.model,
            system_prompt=self.system_prompt,
            user_prompt=prompt,
            temperature=self.temperature,
        )
        self.validator(content, request.report)
        return CoachDraft(report=content)


def _chat_content(
    client: Any,
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    content = response.choices[0].message.content or ""
    content = content.strip()
    if not content:
        raise ValueError("Chat model returned empty content.")
    return content


def _evaluation_payload(result: EvaluationResult) -> dict[str, Any]:
    return {
        "score": result.score,
        "verdict": result.verdict.value,
        "issues": [dict(issue) for issue in result.issues],
        "passed_checks": list(result.passed_checks),
        "summary": result.summary,
    }
