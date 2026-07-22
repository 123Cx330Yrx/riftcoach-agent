from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable


SummaryData = Mapping[str, Any]
IssueData = Mapping[str, Any]


class EvaluationVerdict(str, Enum):
    """A step-level verdict; publication remains a Harness Runtime decision."""

    PASS = "pass"
    NEEDS_REVISION = "needs_revision"
    FAIL = "fail"


@dataclass(frozen=True)
class KnowledgeEvidence:
    """Bounded knowledge supplied to generation, evaluation, and revision."""

    context: str
    source_ids: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def empty(cls) -> "KnowledgeEvidence":
        return cls(context="", source_ids=())


@dataclass(frozen=True)
class CoachDraft:
    """Markdown produced by either the generation or revision step."""

    report: str

    def __post_init__(self) -> None:
        if not self.report.strip():
            raise ValueError("Coach report must not be empty.")


@dataclass(frozen=True)
class EvaluationResult:
    """Structured evaluator output consumed by the deterministic runtime."""

    score: int
    verdict: EvaluationVerdict
    issues: tuple[IssueData, ...] = field(default_factory=tuple)
    passed_checks: tuple[str, ...] = field(default_factory=tuple)
    summary: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.verdict, EvaluationVerdict):
            raise ValueError("Evaluation verdict must be an EvaluationVerdict.")
        if isinstance(self.score, bool) or not isinstance(self.score, int):
            raise ValueError("Evaluation score must be an integer from 0 to 100.")
        if not 0 <= self.score <= 100:
            raise ValueError("Evaluation score must be an integer from 0 to 100.")


@dataclass(frozen=True)
class RetrievalRequest:
    player_summary: SummaryData
    deterministic_report: str


@dataclass(frozen=True)
class GenerationRequest:
    player_summary: SummaryData
    deterministic_report: str
    knowledge: KnowledgeEvidence


@dataclass(frozen=True)
class EvaluationRequest:
    player_summary: SummaryData
    deterministic_report: str
    knowledge: KnowledgeEvidence
    report: str


@dataclass(frozen=True)
class RevisionRequest:
    player_summary: SummaryData
    deterministic_report: str
    knowledge: KnowledgeEvidence
    report: str
    evaluation: EvaluationResult


@runtime_checkable
class RetrieverStep(Protocol):
    def retrieve(self, request: RetrievalRequest) -> KnowledgeEvidence:
        """Retrieve attributable knowledge without changing match facts."""


@runtime_checkable
class GeneratorStep(Protocol):
    def generate(self, request: GenerationRequest) -> CoachDraft:
        """Generate a Coach draft from facts and retrieved knowledge."""


@runtime_checkable
class EvaluatorStep(Protocol):
    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """Evaluate a report and return a structured, bounded verdict."""


@runtime_checkable
class ReviserStep(Protocol):
    def revise(self, request: RevisionRequest) -> CoachDraft:
        """Revise a report only within the supplied evaluation context."""
