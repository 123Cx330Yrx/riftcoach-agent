"""Application service for one bounded recent-form review use case.

The service owns product ordering and safe error projection.  It deliberately
does not own match calculations, Agent/Harness execution, HTTP, persistence,
or provider construction.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)

from app.harness.run_ids import normalize_run_id
from app.lol.report_renderer import render_deterministic_report
from app.lol.summary_schema import SummaryValidationError, validate_summary_document
from app.prompt_program import PromptProgramCatalogError, PromptProgramContractError
from app.runtime.models import (
    RuntimeRunRequest,
    RuntimeRunResult,
    RuntimeStatus,
    RuntimeTraceReference,
)
from app.runtime.runtime import RuntimeCompositionError
from app.runtime.signals import RuntimePublicationStatus
from app.skills.recent_form_review import RecentFormReviewOutput

from .recent_review import (
    ConversationRecentReviewRequest,
    ProductRequestCompilationError,
    RecentReviewProductRequest,
    RecentReviewRuntimeRequestCompiler,
)
from .run_receipts import ApiRunReceipt, RunReceiptWriter


RecentReviewErrorCode = Literal[
    "player_not_found",
    "riot_authentication_failed",
    "riot_rate_limited",
    "upstream_timeout",
    "upstream_unavailable",
    "insufficient_match_data",
    "service_configuration_invalid",
    "review_runtime_failed",
]

_ERROR_CODES = frozenset(
    {
        "player_not_found",
        "riot_authentication_failed",
        "riot_rate_limited",
        "upstream_timeout",
        "upstream_unavailable",
        "insufficient_match_data",
        "service_configuration_invalid",
        "review_runtime_failed",
    }
)
_PUBLIC_RUNTIME_FAILURE_REASONS = frozenset(
    {
        "artifact_integrity_failed",
        "context_build_failed",
        "execution_validation_failed",
        "harness_execution_failed",
        "observation_failed",
        "publication_missing",
        "runtime_policy_rejected",
        "trace_persistence_failed",
        "typed_output_build_failed",
    }
)
_SAFE_CODE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_MAX_RETRY_AFTER_SECONDS = 300


class RecentReviewSummaryBuilder(Protocol):
    """The only upstream data method needed by this product use case."""

    def build(
        self,
        *,
        game_name: str,
        tag_line: str,
        count: int,
        queue: int | None,
    ) -> dict: ...

    def build_by_puuid(
        self,
        *,
        puuid: str,
        game_name: str,
        tag_line: str,
        count: int,
        queue: int | None,
    ) -> dict: ...


class RecentReviewRuntime(Protocol):
    """The Runtime surface consumed by the application layer."""

    def run(
        self,
        request: RuntimeRunRequest,
    ) -> RuntimeRunResult[RecentFormReviewOutput]: ...


ReportRenderer = Callable[[dict], str]


class RecentReviewApplicationResult(BaseModel):
    """Strict product projection of a completed Runtime result."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    runtime_status: RuntimeStatus
    publication_status: RuntimePublicationStatus
    terminal_reason: str
    output: RecentFormReviewOutput
    trace_reference: RuntimeTraceReference

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return normalize_run_id(value)

    @field_validator("terminal_reason")
    @classmethod
    def validate_terminal_reason(cls, value: str) -> str:
        if not _SAFE_CODE_PATTERN.fullmatch(value):
            raise ValueError("terminal_reason must be a safe code")
        return value

    @model_validator(mode="after")
    def validate_projection(self) -> "RecentReviewApplicationResult":
        if self.runtime_status is not RuntimeStatus.COMPLETED:
            raise ValueError("application result requires a completed Runtime")
        if self.output.run_id != self.run_id:
            raise ValueError("output run_id must match application result")
        if self.trace_reference.run_id != self.run_id:
            raise ValueError("trace run_id must match application result")
        if self.output.status != self.publication_status.value:
            raise ValueError("output status must match publication status")
        return self


class RecentReviewApplicationError(RuntimeError):
    """Body-free safe failure emitted at the product boundary."""

    def __init__(
        self,
        code: RecentReviewErrorCode,
        *,
        run_id: str | None = None,
        terminal_reason: str | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unsupported recent-review application error code")
        if run_id is not None:
            run_id = normalize_run_id(run_id)
        if (
            terminal_reason is not None
            and terminal_reason not in _PUBLIC_RUNTIME_FAILURE_REASONS
        ):
            raise ValueError("terminal_reason is not allowlisted")
        if retry_after_seconds is not None:
            if (
                code != "riot_rate_limited"
                or isinstance(retry_after_seconds, bool)
                or not isinstance(retry_after_seconds, int)
                or not 1 <= retry_after_seconds <= _MAX_RETRY_AFTER_SECONDS
            ):
                raise ValueError("retry_after_seconds is not safely bounded")

        self.code = code
        self.run_id = run_id
        self.terminal_reason = terminal_reason
        self.retry_after_seconds = retry_after_seconds
        # Exception args contain only the stable code.  Raw upstream/provider
        # errors are intentionally not retained on this public object.
        super().__init__(code)

    def to_public_dict(self) -> dict[str, str | int | None]:
        return {
            "code": self.code,
            "run_id": self.run_id,
            "terminal_reason": self.terminal_reason,
            "retry_after_seconds": self.retry_after_seconds,
        }


class RecentReviewApplicationService:
    """Orchestrate one recent review without duplicating domain or Runtime."""

    def __init__(
        self,
        *,
        summary_builder: RecentReviewSummaryBuilder,
        compiler: RecentReviewRuntimeRequestCompiler,
        runtime: RecentReviewRuntime,
        receipt_writer: RunReceiptWriter,
        report_renderer: ReportRenderer = render_deterministic_report,
    ) -> None:
        if not callable(getattr(summary_builder, "build", None)):
            raise TypeError("summary_builder must expose build()")
        if not callable(getattr(compiler, "compile", None)):
            raise TypeError("compiler must expose compile()")
        if not callable(getattr(runtime, "run", None)):
            raise TypeError("runtime must expose run()")
        if not callable(getattr(receipt_writer, "write_result", None)):
            raise TypeError("receipt_writer must expose write_result()")
        if not callable(report_renderer):
            raise TypeError("report_renderer must be callable")
        self._summary_builder = summary_builder
        self._compiler = compiler
        self._runtime = runtime
        self._receipt_writer = receipt_writer
        self._report_renderer = report_renderer

    def review(
        self,
        request: RecentReviewProductRequest,
        *,
        run_id: str | None = None,
    ) -> RecentReviewApplicationResult:
        if not isinstance(request, RecentReviewProductRequest):
            raise TypeError("request must be a RecentReviewProductRequest")
        run_id = self._normalize_optional_run_id(run_id)

        summary = self._build_summary(request)
        return self._review_from_summary(
            request,
            summary=summary,
            run_id=run_id,
        )

    def review_by_puuid(
        self,
        request: ConversationRecentReviewRequest,
        *,
        puuid: str,
        game_name: str,
        tag_line: str,
        run_id: str | None = None,
    ) -> RecentReviewApplicationResult:
        if not isinstance(request, ConversationRecentReviewRequest):
            raise TypeError("request must be a ConversationRecentReviewRequest")
        run_id = self._normalize_optional_run_id(run_id)
        summary = self._build_summary_by_puuid(
            request,
            puuid=puuid,
            game_name=game_name,
            tag_line=tag_line,
        )
        return self._review_from_summary(
            request,
            summary=summary,
            run_id=run_id,
        )

    def _review_from_summary(
        self,
        request: RecentReviewProductRequest | ConversationRecentReviewRequest,
        *,
        summary: dict,
        run_id: str | None,
    ) -> RecentReviewApplicationResult:
        self._validate_summary(summary)
        deterministic_report = self._render_report(summary)
        runtime_request = self._compile_request(
            request,
            summary=summary,
            deterministic_report=deterministic_report,
            run_id=run_id,
        )
        runtime_result = self._run_runtime(runtime_request)
        if runtime_result.run_id != runtime_request.run_id:
            raise RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=runtime_request.run_id,
            )
        if runtime_result.runtime_status is RuntimeStatus.FAILED:
            # A typed failed Runtime receipt remains useful evidence, but it
            # can never be reconciled to task success.
            self._write_receipt(runtime_request, runtime_result)
            return self._project_result(runtime_request, runtime_result)

        application_result = self._project_result(
            runtime_request,
            runtime_result,
        )
        self._write_receipt(runtime_request, runtime_result)
        return application_result

    @staticmethod
    def _normalize_optional_run_id(run_id: str | None) -> str | None:
        if run_id is None:
            return None
        try:
            return normalize_run_id(run_id)
        except (TypeError, ValueError):
            raise RecentReviewApplicationError(
                "service_configuration_invalid"
            ) from None

    def _write_receipt(
        self,
        request: RuntimeRunRequest,
        result: RuntimeRunResult[Any],
    ) -> ApiRunReceipt:
        failure: RecentReviewApplicationError | None = None
        receipt: Any = None
        try:
            receipt = self._receipt_writer.write_result(result)
        except Exception:
            failure = RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )
        if failure is None and (
            not isinstance(receipt, ApiRunReceipt)
            or receipt.run_id != request.run_id
            or receipt.runtime_status is not result.runtime_status
            or receipt.publication_status is not result.publication_status
            or receipt.terminal_reason != result.terminal_reason
            or receipt.trace_reference != result.trace_reference
            or receipt.report_available
            != (
                result.trace_reference is not None
                and result.publication_status
                in {
                    RuntimePublicationStatus.PUBLISHED,
                    RuntimePublicationStatus.DEGRADED,
                }
            )
        ):
            failure = RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )
        if failure is not None:
            raise failure
        return receipt

    def _build_summary(self, request: RecentReviewProductRequest) -> dict:
        failure: RecentReviewApplicationError | None = None
        summary: Any = None
        try:
            summary = self._summary_builder.build(
                game_name=request.game_name,
                tag_line=request.tag_line,
                count=request.count,
                queue=request.queue,
            )
        except HTTPError as error:
            failure = _map_http_error(error)
        except Timeout:
            failure = RecentReviewApplicationError("upstream_timeout")
        except (ConnectionError, RequestException):
            failure = RecentReviewApplicationError("upstream_unavailable")
        except Exception:
            failure = RecentReviewApplicationError("upstream_unavailable")

        if failure is not None:
            raise failure

        if not isinstance(summary, dict):
            raise RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        return copy.deepcopy(summary)

    def _build_summary_by_puuid(
        self,
        request: ConversationRecentReviewRequest,
        *,
        puuid: str,
        game_name: str,
        tag_line: str,
    ) -> dict:
        failure: RecentReviewApplicationError | None = None
        summary: Any = None
        try:
            build_by_puuid = getattr(self._summary_builder, "build_by_puuid")
            if not callable(build_by_puuid):
                raise TypeError("summary builder has no trusted PUUID path")
            summary = build_by_puuid(
                puuid=puuid,
                game_name=game_name,
                tag_line=tag_line,
                count=request.count,
                queue=request.queue,
            )
        except HTTPError as error:
            failure = _map_http_error(error)
        except Timeout:
            failure = RecentReviewApplicationError("upstream_timeout")
        except (ConnectionError, RequestException):
            failure = RecentReviewApplicationError("upstream_unavailable")
        except (AttributeError, TypeError, ValueError):
            failure = RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        except Exception:
            failure = RecentReviewApplicationError("upstream_unavailable")

        if failure is not None:
            raise failure
        if not isinstance(summary, dict):
            raise RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        return copy.deepcopy(summary)

    @staticmethod
    def _validate_summary(summary: dict) -> None:
        failure: RecentReviewApplicationError | None = None
        try:
            validate_summary_document(summary)
            recent = summary.get("recent_summary")
            if not isinstance(recent, Mapping):
                raise SummaryValidationError(
                    "recent_summary must be a mapping"
                )
            games = recent.get("games_analyzed")
            if (
                isinstance(games, bool)
                or not isinstance(games, int)
                or games < 0
            ):
                raise SummaryValidationError(
                    "games_analyzed must be a non-negative integer"
                )
            included_games = sum(
                row.get("included_in_aggregate") is True
                for row in summary["matches"]
            )
            if games == 0 and included_games == 0:
                raise RecentReviewApplicationError(
                    "insufficient_match_data"
                )
            if games != included_games:
                raise SummaryValidationError(
                    "games_analyzed does not match included matches"
                )
        except RecentReviewApplicationError:
            raise
        except Exception:
            failure = RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        if failure is not None:
            raise failure

    def _render_report(self, summary: dict) -> str:
        failure: RecentReviewApplicationError | None = None
        report: Any = None
        try:
            report = self._report_renderer(copy.deepcopy(summary))
        except Exception:
            failure = RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        if failure is not None:
            raise failure
        if not isinstance(report, str) or not report.strip():
            raise RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        return report

    def _compile_request(
        self,
        request: RecentReviewProductRequest | ConversationRecentReviewRequest,
        *,
        summary: dict,
        deterministic_report: str,
        run_id: str | None,
    ) -> RuntimeRunRequest:
        failure: RecentReviewApplicationError | None = None
        compiled: Any = None
        try:
            compiled = self._compiler.compile(
                request,
                player_summary=copy.deepcopy(summary),
                deterministic_report=deterministic_report,
                run_id=run_id,
            )
        except (ProductRequestCompilationError, TypeError, ValueError):
            failure = RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        except Exception:
            failure = RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        if failure is not None:
            raise failure
        if not isinstance(compiled, RuntimeRunRequest):
            raise RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        return compiled

    def _run_runtime(
        self,
        request: RuntimeRunRequest,
    ) -> RuntimeRunResult[RecentFormReviewOutput]:
        failure: RecentReviewApplicationError | None = None
        result: Any = None
        try:
            result = self._runtime.run(request)
        except (
            PromptProgramCatalogError,
            PromptProgramContractError,
            RuntimeCompositionError,
        ):
            # Prompt/Program drift happens before a trustworthy Runtime trace
            # exists, so it is a startup/configuration failure without run_id.
            failure = RecentReviewApplicationError(
                "service_configuration_invalid"
            )
        except Exception:
            failure = RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )

        if failure is not None:
            raise failure

        if not isinstance(result, RuntimeRunResult):
            raise RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )
        return result

    @staticmethod
    def _project_result(
        request: RuntimeRunRequest,
        result: RuntimeRunResult[Any],
    ) -> RecentReviewApplicationResult:
        terminal_reason = _public_runtime_failure_reason(
            result.terminal_reason
        )
        if result.run_id != request.run_id:
            raise RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )
        if result.runtime_status is RuntimeStatus.FAILED:
            raise RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
                terminal_reason=terminal_reason,
            )
        if (
            result.publication_status is None
            or not isinstance(result.output, RecentFormReviewOutput)
            or result.trace_reference is None
            or result.output.run_id != request.run_id
            or result.output.status != result.publication_status.value
        ):
            raise RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )

        failure: RecentReviewApplicationError | None = None
        application_result: RecentReviewApplicationResult | None = None
        try:
            application_result = RecentReviewApplicationResult(
                run_id=request.run_id,
                runtime_status=result.runtime_status,
                publication_status=result.publication_status,
                terminal_reason=result.terminal_reason,
                output=result.output,
                trace_reference=result.trace_reference,
            )
        except (TypeError, ValueError):
            failure = RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )
        if failure is not None:
            raise failure
        if application_result is None:
            raise RecentReviewApplicationError(
                "review_runtime_failed",
                run_id=request.run_id,
            )
        return application_result


def _retry_after_seconds(error: HTTPError) -> int | None:
    response = error.response
    if response is None:
        return None
    raw_value = response.headers.get("Retry-After")
    if (
        not isinstance(raw_value, str)
        or not raw_value.isascii()
        or not raw_value.isdigit()
    ):
        return None
    value = int(raw_value)
    if not 1 <= value <= _MAX_RETRY_AFTER_SECONDS:
        return None
    return value


def _map_http_error(error: HTTPError) -> RecentReviewApplicationError:
    response = error.response
    status_code = response.status_code if response is not None else None
    if status_code == 404:
        return RecentReviewApplicationError("player_not_found")
    if status_code in {401, 403}:
        return RecentReviewApplicationError("riot_authentication_failed")
    if status_code == 429:
        return RecentReviewApplicationError(
            "riot_rate_limited",
            retry_after_seconds=_retry_after_seconds(error),
        )
    return RecentReviewApplicationError("upstream_unavailable")


def _public_runtime_failure_reason(value: str) -> str | None:
    return value if value in _PUBLIC_RUNTIME_FAILURE_REASONS else None


__all__ = [
    "RecentReviewApplicationError",
    "RecentReviewApplicationResult",
    "RecentReviewApplicationService",
    "RecentReviewErrorCode",
    "RecentReviewRuntime",
    "RecentReviewSummaryBuilder",
]
