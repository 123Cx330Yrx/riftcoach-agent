from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from requests import Response
from requests.exceptions import ConnectionError, HTTPError, Timeout

from app.memory.context_models import MemoryContextBinding
from app.players.models import RelationshipRole
from app.product import (
    ConversationRecentReviewRequest,
    RecentReviewProductRequest,
    RecentReviewRuntimeRequestCompiler,
)
from app.product.recent_review_service import (
    RecentReviewApplicationError,
    RecentReviewApplicationService,
)
from app.product.run_receipts import FileRunReceiptStore
from app.product.run_receipts import ApiRunReceipt
from app.runtime.models import (
    RuntimeRunResult,
    RuntimeStatus,
    RuntimeTraceReference,
)
from app.runtime.runtime import RuntimeCompositionError
from app.runtime.signals import RuntimePublicationStatus
from app.skills.catalog import SkillCatalog
from app.skills.recent_form_review import RecentFormReviewOutput


def _summary() -> dict:
    return json.loads(
        Path("examples/fixtures/player_summary_demo.json").read_text(
            encoding="utf-8"
        )
    )


class FakeSummaryBuilder:
    def __init__(self, summary: dict, events: list[str]) -> None:
        self._summary = summary
        self._events = events

    def build(
        self,
        *,
        game_name: str,
        tag_line: str,
        count: int,
        queue: int | None,
    ) -> dict:
        self._events.append("summary")
        assert (game_name, tag_line, count, queue) == (
            "DemoPlayer",
            "TEST",
            10,
            420,
        )
        return copy.deepcopy(self._summary)

    def build_by_puuid(
        self,
        *,
        puuid: str,
        game_name: str,
        tag_line: str,
        count: int,
        queue: int | None,
    ) -> dict:
        self._events.append("summary_by_puuid")
        assert (puuid, game_name, tag_line, count, queue) == (
            "trusted-puuid",
            "Renamed Player",
            "KR2",
            10,
            420,
        )
        return copy.deepcopy(self._summary)


class RecordingRenderer:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def __call__(self, summary: dict) -> str:
        self._events.append("report")
        assert summary["schema_version"] == "1.0"
        return "# deterministic report\n"


class FakeRuntime:
    def __init__(
        self,
        events: list[str],
        *,
        publication_status: RuntimePublicationStatus,
        output_status: str | None = None,
        runtime_status: RuntimeStatus = RuntimeStatus.COMPLETED,
        terminal_reason: str | None = None,
        returned_run_id: str | None = None,
    ) -> None:
        self._events = events
        self._publication_status = publication_status
        self._output_status = output_status or publication_status.value
        self._runtime_status = runtime_status
        self._terminal_reason = terminal_reason or {
            RuntimePublicationStatus.PUBLISHED: "quality_gate_passed",
            RuntimePublicationStatus.DEGRADED: "deterministic_fallback",
            RuntimePublicationStatus.REJECTED: "quality_gate_rejected",
        }[publication_status]
        self._returned_run_id = returned_run_id
        self.requests = []

    def run(self, request) -> RuntimeRunResult[RecentFormReviewOutput]:
        self._events.append("runtime")
        self.requests.append(request)
        run_id = self._returned_run_id or request.run_id
        if self._runtime_status is RuntimeStatus.FAILED:
            return RuntimeRunResult[RecentFormReviewOutput](
                run_id=run_id,
                runtime_status=RuntimeStatus.FAILED,
                publication_status=self._publication_status,
                terminal_reason=self._terminal_reason,
                output=None,
                trace_reference=None,
            )

        output = RecentFormReviewOutput(
            run_id=run_id,
            status=self._output_status,
            report=(
                None
                if self._output_status == "rejected"
                else "# reviewed report\n"
            ),
            evaluation_score=(
                91 if self._output_status == "published" else None
            ),
        )
        return RuntimeRunResult[RecentFormReviewOutput](
            run_id=run_id,
            runtime_status=RuntimeStatus.COMPLETED,
            publication_status=self._publication_status,
            terminal_reason=self._terminal_reason,
            output=output,
            trace_reference=RuntimeTraceReference(
                run_id=run_id,
                sha256="a" * 64,
            ),
        )


class RecordingReceiptWriter:
    def __init__(
        self,
        events: list[str],
        *,
        error: Exception | None = None,
    ) -> None:
        self._events = events
        self._error = error
        self.results = []

    def write_result(self, result, *, created_at_utc=None):
        self._events.append("receipt")
        if self._error is not None:
            raise self._error
        self.results.append(result)
        return ApiRunReceipt.from_runtime_result(result)


def _service(
    *,
    summary_builder,
    runtime,
    events: list[str],
    compiler: RecentReviewRuntimeRequestCompiler | None = None,
    renderer=None,
    receipt_writer: RecordingReceiptWriter | None = None,
) -> RecentReviewApplicationService:
    return RecentReviewApplicationService(
        summary_builder=summary_builder,
        report_renderer=renderer or RecordingRenderer(events),
        compiler=compiler
        or RecentReviewRuntimeRequestCompiler(
            SkillCatalog.from_directory("skills"),
            run_id_factory=lambda: "application_run",
        ),
        runtime=runtime,
        receipt_writer=receipt_writer or RecordingReceiptWriter(events),
    )


@pytest.mark.parametrize(
    "publication_status",
    (
        RuntimePublicationStatus.PUBLISHED,
        RuntimePublicationStatus.DEGRADED,
        RuntimePublicationStatus.REJECTED,
    ),
)
def test_service_runs_the_real_compiler_in_order_and_projects_terminal_result(
    publication_status: RuntimePublicationStatus,
) -> None:
    events: list[str] = []
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=FakeRuntime(
            events,
            publication_status=publication_status,
        ),
        events=events,
    )

    result = service.review(
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST")
    )

    assert events == ["summary", "report", "runtime", "receipt"]
    assert result.run_id == "application_run"
    assert result.runtime_status is RuntimeStatus.COMPLETED
    assert result.publication_status is publication_status
    assert result.output.status == publication_status.value
    assert result.trace_reference.run_id == result.run_id
    assert result.model_config["frozen"] is True
    assert result.model_config["extra"] == "forbid"


def test_service_threads_a_trusted_sql_run_id_through_runtime_and_receipt() -> None:
    events: list[str] = []
    writer = RecordingReceiptWriter(events)
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=FakeRuntime(
            events,
            publication_status=RuntimePublicationStatus.PUBLISHED,
        ),
        events=events,
        compiler=RecentReviewRuntimeRequestCompiler(
            SkillCatalog.from_directory("skills"),
            run_id_factory=lambda: (_ for _ in ()).throw(
                AssertionError("SQL run_id must bypass generation")
            ),
        ),
        receipt_writer=writer,
    )

    result = service.review(
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST"),
        run_id="review_sql_application",
    )

    assert result.run_id == "review_sql_application"
    assert writer.results[0].run_id == result.run_id
    assert events == ["summary", "report", "runtime", "receipt"]


def test_service_reuses_runtime_harness_after_trusted_puuid_summary() -> None:
    events: list[str] = []
    writer = RecordingReceiptWriter(events)
    runtime = FakeRuntime(
        events,
        publication_status=RuntimePublicationStatus.PUBLISHED,
    )
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=runtime,
        events=events,
        receipt_writer=writer,
    )

    result = service.review_by_puuid(
        ConversationRecentReviewRequest(),
        puuid="trusted-puuid",
        game_name="Renamed Player",
        tag_line="KR2",
        run_id="review_conversation_application",
        memory_context_binding=MemoryContextBinding(
            run_id="review_conversation_application",
            owner_id="owner-application",
            conversation_id=UUID("42000000-0000-0000-0000-000000000001"),
            relationship_id=UUID("42000000-0000-0000-0000-000000000002"),
            player_subject_id=UUID("42000000-0000-0000-0000-000000000003"),
            relationship_role=RelationshipRole.SELF,
        ),
    )

    assert result.run_id == "review_conversation_application"
    assert writer.results[0].run_id == result.run_id
    assert runtime.requests[0].memory_context_binding is not None
    assert runtime.requests[0].memory_context_binding.owner_id == "owner-application"
    assert events == ["summary_by_puuid", "report", "runtime", "receipt"]


class MismatchedReceiptWriter:
    def write_result(self, result, *, created_at_utc=None):
        return ApiRunReceipt(
            run_id="different_receipt_run",
            runtime_status=result.runtime_status,
            publication_status=result.publication_status,
            terminal_reason=result.terminal_reason,
            trace_reference=RuntimeTraceReference(
                run_id="different_receipt_run",
                sha256=result.trace_reference.sha256,
            ),
            created_at_utc=datetime.now(timezone.utc),
            report_available=True,
        )


def test_service_rejects_a_receipt_writer_identity_mismatch() -> None:
    events: list[str] = []
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=FakeRuntime(
            events,
            publication_status=RuntimePublicationStatus.PUBLISHED,
        ),
        events=events,
        receipt_writer=MismatchedReceiptWriter(),
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "review_runtime_failed"
    assert caught.value.run_id == "application_run"


class RaisingSummaryBuilder:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def build(self, **kwargs):
        raise self._error


class UnexpectedRuntime:
    def run(self, request):
        raise AssertionError("runtime must not be called")


def _http_error(status_code: int, *, retry_after: str | None = None) -> HTTPError:
    response = Response()
    response.status_code = status_code
    response.url = "https://asia.api.riotgames.com/private?api_key=secret-key"
    if retry_after is not None:
        response.headers["Retry-After"] = retry_after
    return HTTPError(
        "private upstream body C:\\Users\\secret\\.env",
        response=response,
    )


@pytest.mark.parametrize(
    "error, expected_code, expected_retry",
    (
        (_http_error(404), "player_not_found", None),
        (_http_error(401), "riot_authentication_failed", None),
        (_http_error(403), "riot_authentication_failed", None),
        (_http_error(429, retry_after="17"), "riot_rate_limited", 17),
        (_http_error(500), "upstream_unavailable", None),
        (Timeout("secret-key https://private"), "upstream_timeout", None),
        (
            ConnectionError("C:\\private\\cache secret-key"),
            "upstream_unavailable",
            None,
        ),
    ),
)
def test_upstream_failures_map_to_body_free_safe_errors(
    error: Exception,
    expected_code: str,
    expected_retry: int | None,
) -> None:
    events: list[str] = []
    service = _service(
        summary_builder=RaisingSummaryBuilder(error),
        runtime=UnexpectedRuntime(),
        events=events,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    public = caught.value.to_public_dict()
    assert public["code"] == expected_code
    assert public["retry_after_seconds"] == expected_retry
    assert public["run_id"] is None
    assert public["terminal_reason"] is None
    assert caught.value.__context__ is None
    serialized = json.dumps(public, ensure_ascii=False)
    for secret in ("secret-key", "riotgames.com", "C:\\", ".env"):
        assert secret not in serialized
        assert secret not in str(caught.value)


def test_rate_limit_retry_after_is_bounded_and_never_echoed_raw() -> None:
    events: list[str] = []
    service = _service(
        summary_builder=RaisingSummaryBuilder(
            _http_error(429, retry_after="999999 private")
        ),
        runtime=UnexpectedRuntime(),
        events=events,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.retry_after_seconds is None
    assert "private" not in str(caught.value.to_public_dict())


def test_invalid_summary_is_configuration_failure_before_report_or_runtime() -> None:
    events: list[str] = []
    service = _service(
        summary_builder=FakeSummaryBuilder({"schema_version": "9.9"}, events),
        runtime=UnexpectedRuntime(),
        events=events,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "service_configuration_invalid"
    assert events == ["summary"]


def test_malformed_match_row_cannot_escape_as_a_raw_python_error() -> None:
    events: list[str] = []
    summary = _summary()
    summary["matches"] = [["C:\\private\\secret-key"]]
    service = _service(
        summary_builder=FakeSummaryBuilder(summary, events),
        runtime=UnexpectedRuntime(),
        events=events,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "service_configuration_invalid"
    assert "private" not in str(caught.value)
    assert events == ["summary"]


def test_zero_analyzable_matches_stops_before_run_id_generation() -> None:
    events: list[str] = []
    summary = _summary()
    summary["recent_summary"]["games_analyzed"] = 0
    summary["matches"] = []
    compiler = RecentReviewRuntimeRequestCompiler(
        SkillCatalog.from_directory("skills"),
        run_id_factory=lambda: (_ for _ in ()).throw(
            AssertionError("run_id must not be generated")
        ),
    )
    service = _service(
        summary_builder=FakeSummaryBuilder(summary, events),
        runtime=UnexpectedRuntime(),
        events=events,
        compiler=compiler,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "insufficient_match_data"
    assert caught.value.run_id is None
    assert events == ["summary"]


def test_renderer_and_compiler_drift_fail_closed_before_runtime(
    tmp_path: Path,
) -> None:
    events: list[str] = []

    def bad_renderer(summary: dict) -> str:
        events.append("report")
        raise KeyError("C:\\private\\prompt secret-key")

    renderer_service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=UnexpectedRuntime(),
        events=events,
        renderer=bad_renderer,
    )
    with pytest.raises(RecentReviewApplicationError) as renderer_error:
        renderer_service.review(
            RecentReviewProductRequest(riot_id="DemoPlayer#TEST")
        )
    assert renderer_error.value.code == "service_configuration_invalid"
    assert "private" not in str(renderer_error.value)

    events.clear()
    compiler_service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=UnexpectedRuntime(),
        events=events,
        compiler=RecentReviewRuntimeRequestCompiler(
            SkillCatalog.from_directory(tmp_path),
        ),
    )
    with pytest.raises(RecentReviewApplicationError) as compiler_error:
        compiler_service.review(
            RecentReviewProductRequest(riot_id="DemoPlayer#TEST")
        )
    assert compiler_error.value.code == "service_configuration_invalid"
    assert events == ["summary", "report"]


class RaisingRuntime:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def run(self, request):
        raise self._error


def test_prompt_program_drift_is_configuration_failure_without_raw_details() -> None:
    events: list[str] = []
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=RaisingRuntime(
            RuntimeCompositionError(
                "C:\\private\\prompt manifest secret-key drifted"
            )
        ),
        events=events,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "service_configuration_invalid"
    assert caught.value.run_id is None
    assert "private" not in str(caught.value)


@pytest.mark.parametrize(
    "runtime",
    (
        FakeRuntime(
            [],
            publication_status=RuntimePublicationStatus.DEGRADED,
            runtime_status=RuntimeStatus.FAILED,
            terminal_reason="harness_execution_failed",
        ),
        RaisingRuntime(RuntimeError("secret-key C:\\private\\runtime")),
    ),
)
def test_runtime_failure_becomes_safe_review_error_with_trusted_run_id(
    runtime,
) -> None:
    events: list[str] = []
    if isinstance(runtime, FakeRuntime):
        runtime._events = events
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=runtime,
        events=events,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "review_runtime_failed"
    assert caught.value.run_id == "application_run"
    assert caught.value.__context__ is None
    assert "secret-key" not in str(caught.value)


def test_typed_failed_runtime_is_receipted_before_safe_error() -> None:
    events: list[str] = []
    writer = RecordingReceiptWriter(events)
    runtime = FakeRuntime(
        events,
        publication_status=RuntimePublicationStatus.DEGRADED,
        runtime_status=RuntimeStatus.FAILED,
        terminal_reason="harness_execution_failed",
    )
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=runtime,
        events=events,
        receipt_writer=writer,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "review_runtime_failed"
    assert events == ["summary", "report", "runtime", "receipt"]
    assert len(writer.results) == 1
    assert writer.results[0].runtime_status is RuntimeStatus.FAILED


def test_application_service_can_write_the_real_file_receipt_store(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    receipt_store = FileRunReceiptStore(tmp_path)
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=FakeRuntime(
            events,
            publication_status=RuntimePublicationStatus.PUBLISHED,
        ),
        events=events,
        receipt_writer=receipt_store,
    )

    result = service.review(
        RecentReviewProductRequest(riot_id="DemoPlayer#TEST")
    )

    receipt = receipt_store.read_receipt(result.run_id)
    assert receipt.run_id == result.run_id
    assert receipt.runtime_status is RuntimeStatus.COMPLETED
    assert receipt.publication_status is RuntimePublicationStatus.PUBLISHED
    assert receipt.trace_reference == result.trace_reference
    assert receipt.report_available is True


def test_untyped_runtime_exception_does_not_invent_a_receipt() -> None:
    events: list[str] = []
    writer = RecordingReceiptWriter(events)
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=RaisingRuntime(RuntimeError("secret-key C:\\private")),
        events=events,
        receipt_writer=writer,
    )

    with pytest.raises(RecentReviewApplicationError):
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert events == ["summary", "report"]
    assert writer.results == []


def test_receipt_failure_is_body_free_and_blocks_success_projection() -> None:
    events: list[str] = []
    writer = RecordingReceiptWriter(
        events,
        error=OSError("C:\\private\\receipt secret-key"),
    )
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=FakeRuntime(
            events,
            publication_status=RuntimePublicationStatus.PUBLISHED,
        ),
        events=events,
        receipt_writer=writer,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert events == ["summary", "report", "runtime", "receipt"]
    assert caught.value.code == "review_runtime_failed"
    assert caught.value.run_id == "application_run"
    assert caught.value.__context__ is None
    assert "private" not in str(caught.value)


def test_runtime_terminal_mismatch_and_untrusted_reason_are_not_projected() -> None:
    events: list[str] = []
    writer = RecordingReceiptWriter(events)
    mismatch = FakeRuntime(
        events,
        publication_status=RuntimePublicationStatus.PUBLISHED,
        output_status="degraded",
    )
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=mismatch,
        events=events,
        receipt_writer=writer,
    )
    with pytest.raises(RecentReviewApplicationError) as mismatch_error:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))
    assert mismatch_error.value.code == "review_runtime_failed"
    assert mismatch_error.value.terminal_reason is None
    assert writer.results == []
    assert events == ["summary", "report", "runtime"]

    events.clear()
    unknown = FakeRuntime(
        events,
        publication_status=RuntimePublicationStatus.DEGRADED,
        runtime_status=RuntimeStatus.FAILED,
        terminal_reason="new_internal_failure",
    )
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=unknown,
        events=events,
        receipt_writer=RecordingReceiptWriter(events),
    )
    with pytest.raises(RecentReviewApplicationError) as unknown_error:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))
    assert unknown_error.value.terminal_reason is None


def test_runtime_result_cannot_switch_the_server_generated_run_id() -> None:
    events: list[str] = []
    writer = RecordingReceiptWriter(events)
    service = _service(
        summary_builder=FakeSummaryBuilder(_summary(), events),
        runtime=FakeRuntime(
            events,
            publication_status=RuntimePublicationStatus.PUBLISHED,
            returned_run_id="different_run",
        ),
        events=events,
        receipt_writer=writer,
    )

    with pytest.raises(RecentReviewApplicationError) as caught:
        service.review(RecentReviewProductRequest(riot_id="DemoPlayer#TEST"))

    assert caught.value.code == "review_runtime_failed"
    assert caught.value.run_id == "application_run"
    assert writer.results == []
    assert events == ["summary", "report", "runtime"]
