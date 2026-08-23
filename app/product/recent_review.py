"""Compile a bounded recent-review product request into Runtime V1 input."""

from __future__ import annotations

import copy
import unicodedata
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.harness.run_ids import normalize_run_id
from app.memory.context_models import MemoryContextBinding
from app.runtime.models import RuntimePolicySnapshot, RuntimeRunRequest
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.loader import LoadedSkill
from app.skills.recent_form_review import RecentFormReviewInput
from app.skills.routing_models import (
    RouteEvidence,
    RouteOutcome,
    RouteReason,
    RouterDecision,
)


_RECENT_SKILL_NAME = "recent-form-review"
_TYPED_ENTRYPOINT_SIGNAL = "entrypoint:reviews.recent"
_RUNTIME_POLICY_VERSION = "1.0.0"
_RUNTIME_EVENT_BUDGET = 256
_RUNTIME_MAX_REVISIONS = 1
_MAX_GAME_NAME_LENGTH = 64
_MAX_TAG_LINE_LENGTH = 32
_MAX_RIOT_ID_LENGTH = (
    _MAX_GAME_NAME_LENGTH + 1 + _MAX_TAG_LINE_LENGTH
)


class ProductRequestCompilationError(ValueError):
    """Raised before Runtime execution when trusted compilation fails."""


class RecentReviewProductRequest(BaseModel):
    """The complete client-controlled surface for a recent review."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    riot_id: str = Field(min_length=3, max_length=_MAX_RIOT_ID_LENGTH)
    routing_region: Literal["americas", "asia", "europe", "sea"]
    count: int = Field(default=10, ge=5, le=20)
    queue: Literal[420] | None = 420
    focus: Literal[
        "overall",
        "laning",
        "survival",
        "economy",
        "vision",
    ] = "overall"

    @field_validator("riot_id")
    @classmethod
    def normalize_riot_id(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value.strip())
        if any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        ):
            raise ValueError("riot_id must not contain control characters")

        game_name, separator, tag_line = normalized.rpartition("#")
        game_name = game_name.strip()
        tag_line = tag_line.strip()
        if not separator or not game_name or not tag_line:
            raise ValueError(
                "riot_id must contain non-blank game name and tag line"
            )
        if len(game_name) > _MAX_GAME_NAME_LENGTH:
            raise ValueError("riot_id game name exceeds the local bound")
        if len(tag_line) > _MAX_TAG_LINE_LENGTH:
            raise ValueError("riot_id tag line exceeds the local bound")
        return f"{game_name}#{tag_line}"

    @property
    def game_name(self) -> str:
        return self.riot_id.rpartition("#")[0]

    @property
    def tag_line(self) -> str:
        return self.riot_id.rpartition("#")[2]


class ConversationRecentReviewRequest(BaseModel):
    """Client-controlled parameters after identity comes from Conversation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    count: int = Field(default=10, ge=5, le=20)
    queue: Literal[420] | None = 420
    focus: Literal[
        "overall",
        "laning",
        "survival",
        "economy",
        "vision",
    ] = "overall"


RunIdFactory = Callable[[], str]


def _default_run_id_factory() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"review_{timestamp}_{uuid4().hex[:12]}"


def _select_recent_skill(
    catalog: SkillCatalog,
) -> tuple[LoadedSkill, RouterDecision]:
    skill = catalog.get(_RECENT_SKILL_NAME)
    if skill is None:
        raise ProductRequestCompilationError(
            "recent-form-review Skill is not available"
        )
    if skill.input_model is not RecentFormReviewInput:
        raise ProductRequestCompilationError(
            "recent-form-review input contract is incompatible"
        )

    decision = RouterDecision(
        outcome=RouteOutcome.SELECTED,
        reason=RouteReason.MATCHED_SKILL,
        selected_skill=skill.manifest.name,
        selected_skill_version=skill.manifest.version,
        candidate_skills=(skill.manifest.name,),
        evidence=(
            RouteEvidence(
                skill_name=skill.manifest.name,
                positive_signals=(_TYPED_ENTRYPOINT_SIGNAL,),
            ),
        ),
        explanation="Trusted typed recent-review entrypoint.",
    )
    return skill, decision


def _compile_runtime_policy(skill: LoadedSkill) -> RuntimePolicySnapshot:
    budgets = skill.manifest.budgets
    quality_gate = skill.manifest.quality_gate
    return RuntimePolicySnapshot(
        policy_version=_RUNTIME_POLICY_VERSION,
        event_budget=_RUNTIME_EVENT_BUDGET,
        max_iterations=budgets.max_iterations,
        max_tool_calls=budgets.max_tool_calls,
        timeout_s=budgets.timeout_s,
        max_context_tokens=budgets.max_context_tokens,
        publish_score_threshold=quality_gate.minimum_score,
        max_revisions=_RUNTIME_MAX_REVISIONS,
        allow_deterministic_fallback=(
            quality_gate.allow_deterministic_fallback
        ),
    )


class RecentReviewRuntimeRequestCompiler:
    """Translate validated product fields into existing Runtime contracts."""

    def __init__(
        self,
        catalog: SkillCatalog,
        *,
        run_id_factory: RunIdFactory = _default_run_id_factory,
    ) -> None:
        self._catalog = catalog
        self._run_id_factory = run_id_factory

    def compile(
        self,
        request: RecentReviewProductRequest | ConversationRecentReviewRequest,
        *,
        player_summary: Mapping[str, Any],
        deterministic_report: str,
        run_id: str | None = None,
        memory_context_binding: MemoryContextBinding | None = None,
    ) -> RuntimeRunRequest:
        """Compile after request count/queue/riot_id drove summary collection."""

        skill, decision = _select_recent_skill(self._catalog)
        typed_input = RecentFormReviewInput(
            player_summary=copy.deepcopy(dict(player_summary)),
            deterministic_report=deterministic_report,
            focus=request.focus,
        )
        input_payload = typed_input.model_dump(mode="python")

        if run_id is None:
            try:
                normalized_run_id = normalize_run_id(self._run_id_factory())
            except (TypeError, ValueError) as exc:
                raise ProductRequestCompilationError(
                    "server run_id generation returned an invalid value"
                ) from exc
        else:
            try:
                normalized_run_id = normalize_run_id(run_id)
            except (TypeError, ValueError) as exc:
                raise ProductRequestCompilationError(
                    "trusted run_id is invalid"
                ) from exc
        if (
            memory_context_binding is not None
            and memory_context_binding.run_id != normalized_run_id
        ):
            raise ProductRequestCompilationError(
                "Memory Context binding run_id does not match the trusted run"
            )

        binding = SkillInputArtifactBinding.from_content(
            run_id=normalized_run_id,
            player_summary=typed_input.player_summary,
            deterministic_report=typed_input.deterministic_report,
        )
        execution_request = SkillExecutionRequest(
            run_id=normalized_run_id,
            user_utterance=(
                "typed-entrypoint reviews.recent "
                f"focus={request.focus}"
            ),
            router_decision=decision,
            input_payload=input_payload,
            input_artifacts=binding,
        )
        return RuntimeRunRequest(
            execution_request=execution_request,
            policy=_compile_runtime_policy(skill),
            memory_context_binding=memory_context_binding,
        )


__all__ = [
    "ConversationRecentReviewRequest",
    "ProductRequestCompilationError",
    "RecentReviewProductRequest",
    "RecentReviewRuntimeRequestCompiler",
]
