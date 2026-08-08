from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.evaluation.coach_report import (
    EvaluationResponseModel,
    build_evaluation_repair_prompt,
    evaluation_response_contract,
)
from app.providers.models import (
    ChatResponse,
    StructuredResponseContract,
    TokenUsage,
)
from app.providers.structured import decode_structured_response
from app.tools.runtime import ToolRuntime

from .knowledge import knowledge_evidence_from_search_payloads
from .steps import (
    CoachDraft,
    DraftPreparationRequest,
    DraftPreparationResult,
    EvaluationRequest,
    EvaluationResult,
    EvaluationVerdict,
    GenerationRequest,
    GeneratorStep,
    KnowledgeEvidence,
    RetrievalRequest,
    RetrieverStep,
    RevisionRequest,
)


SummaryCompactor = Callable[[dict[str, Any]], dict[str, Any]]
RetrievalQueryBuilder = Callable[[dict[str, Any]], str]
RetrievalFilterBuilder = Callable[[dict[str, Any]], dict[str, Any]]
GenerationPromptBuilder = Callable[[dict[str, Any], str, str], str]
FactPackBuilder = Callable[[dict[str, Any]], dict[str, Any]]
EvaluationPromptBuilder = Callable[[dict[str, Any], str], str]
RevisionPromptBuilder = Callable[[str, dict[str, Any]], str]
RevisionValidator = Callable[[str, str], None]


class SequentialDraftPreparer:
    """Adapt the legacy retrieve-then-generate path to one preparation step."""

    def __init__(
        self,
        *,
        retriever: RetrieverStep,
        generator: GeneratorStep,
    ) -> None:
        self.retriever = retriever
        self.generator = generator

    def prepare(
        self,
        request: DraftPreparationRequest,
    ) -> DraftPreparationResult:
        knowledge = self.retriever.retrieve(
            RetrievalRequest(
                player_summary=request.player_summary,
                deterministic_report=request.deterministic_report,
            )
        )
        if not isinstance(knowledge, KnowledgeEvidence):
            raise TypeError("Retriever must return KnowledgeEvidence.")

        draft = self.generator.generate(
            GenerationRequest(
                player_summary=request.player_summary,
                deterministic_report=request.deterministic_report,
                knowledge=knowledge,
            )
        )
        if not isinstance(draft, CoachDraft):
            raise TypeError("Generator must return CoachDraft.")
        return DraftPreparationResult(draft=draft, knowledge=knowledge)


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
    """Evaluate through one strict contract and at most one format repair."""

    def __init__(
        self,
        *,
        runtime: ToolRuntime,
        system_prompt: str,
        fact_pack_builder: FactPackBuilder,
        prompt_builder: EvaluationPromptBuilder,
        temperature: float = 0.0,
    ) -> None:
        self.runtime = runtime
        self.system_prompt = system_prompt
        self.fact_pack_builder = fact_pack_builder
        self.prompt_builder = prompt_builder
        self.temperature = temperature

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        fact_pack = self.fact_pack_builder(dict(request.player_summary))
        prompt = self.prompt_builder(fact_pack, request.report)
        contract = evaluation_response_contract()
        response = _chat_response(
            self.runtime,
            system_prompt=self.system_prompt,
            user_prompt=prompt,
            temperature=self.temperature,
            harness_step="evaluate",
            response_contract=contract,
        )
        decoded = decode_structured_response(
            response=response,
            contract=contract,
            output_model=EvaluationResponseModel,
            repair=lambda repair_request: _chat_response(
                self.runtime,
                system_prompt=self.system_prompt,
                user_prompt=build_evaluation_repair_prompt(
                    contract=repair_request.contract,
                    invalid_content=repair_request.invalid_content,
                ),
                temperature=self.temperature,
                harness_step="evaluate_repair",
                response_contract=repair_request.contract,
            ),
        )
        payload = decoded.value
        return EvaluationResult(
            score=payload.score,
            verdict=EvaluationVerdict(payload.verdict),
            issues=tuple(
                issue.model_dump(mode="json") for issue in payload.issues
            ),
            passed_checks=tuple(payload.passed_checks),
            summary=payload.summary,
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
    response = _chat_response(
        runtime,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        harness_step=harness_step,
    )
    content = response.content
    if content is None:
        raise ValueError("Chat model returned empty content.")
    return content


def _chat_response(
    runtime: ToolRuntime,
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    harness_step: str,
    response_contract: StructuredResponseContract | None = None,
) -> ChatResponse:
    params: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if response_contract is not None:
        params["response_contract"] = {
            "name": response_contract.name,
            "version": response_contract.version,
            "json_schema": response_contract.schema_dict(),
            "strict": response_contract.strict,
        }
    result = runtime.execute(
        "llm.chat",
        params,
        metadata={"harness_step": harness_step},
    )
    data = _require_success(result, "llm.chat")
    usage = data["usage"]
    return ChatResponse(
        content=data["content"],
        model=data["model"],
        provider=data["provider"],
        finish_reason=data["finish_reason"],
        usage=TokenUsage(
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        ),
        request_id=data["request_id"],
    )


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
