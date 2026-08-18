from __future__ import annotations

import json
import os
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.product.run_receipts import (
    ApiRunReceipt,
    FileRunReceiptStore,
    RunReceiptReference,
    RunReceiptIntegrityError,
)
from app.runtime.models import (
    RuntimeRunResult,
    RuntimeStatus,
    RuntimeTraceReference,
)
from app.runtime.signals import RuntimePublicationStatus
from app.skills.recent_form_review import RecentFormReviewOutput


NOW = datetime(2026, 8, 17, 8, 30, tzinfo=timezone.utc)


def _result(
    *,
    run_id: str = "receipt_demo",
    runtime_status: RuntimeStatus = RuntimeStatus.COMPLETED,
    publication_status: RuntimePublicationStatus | None = (
        RuntimePublicationStatus.PUBLISHED
    ),
    terminal_reason: str = "quality_gate_passed",
    with_trace: bool = True,
) -> RuntimeRunResult[RecentFormReviewOutput]:
    output = None
    if runtime_status is RuntimeStatus.COMPLETED:
        assert publication_status is not None
        output = RecentFormReviewOutput(
            run_id=run_id,
            status=publication_status.value,
            report=(
                None
                if publication_status is RuntimePublicationStatus.REJECTED
                else "# reviewed report\n"
            ),
            evaluation_score=(
                91
                if publication_status is RuntimePublicationStatus.PUBLISHED
                else None
            ),
        )
    return RuntimeRunResult[RecentFormReviewOutput](
        run_id=run_id,
        runtime_status=runtime_status,
        publication_status=publication_status,
        terminal_reason=terminal_reason,
        output=output,
        trace_reference=(
            RuntimeTraceReference(run_id=run_id, sha256="a" * 64)
            if with_trace
            else None
        ),
    )


@pytest.mark.parametrize(
    "publication_status, expected_report",
    (
        (RuntimePublicationStatus.PUBLISHED, True),
        (RuntimePublicationStatus.DEGRADED, True),
        (RuntimePublicationStatus.REJECTED, False),
    ),
)
def test_receipt_projects_only_body_free_runtime_terminal_fields(
    publication_status: RuntimePublicationStatus,
    expected_report: bool,
) -> None:
    receipt = ApiRunReceipt.from_runtime_result(
        _result(
            publication_status=publication_status,
            terminal_reason={
                RuntimePublicationStatus.PUBLISHED: "quality_gate_passed",
                RuntimePublicationStatus.DEGRADED: "deterministic_fallback",
                RuntimePublicationStatus.REJECTED: "quality_gate_rejected",
            }[publication_status],
        ),
        created_at_utc=NOW,
    )

    assert receipt.report_available is expected_report
    assert receipt.created_at_utc == NOW
    assert receipt.model_config["frozen"] is True
    assert receipt.model_config["extra"] == "forbid"
    assert set(receipt.model_dump()) == {
        "schema_version",
        "run_id",
        "runtime_status",
        "publication_status",
        "terminal_reason",
        "trace_reference",
        "created_at_utc",
        "report_available",
    }
    serialized = receipt.model_dump_json()
    for forbidden in (
        "reviewed report",
        "prompt",
        "tool_data",
        "exception",
        "C:\\\\",
    ):
        assert forbidden not in serialized.lower()


def test_failed_runtime_without_trace_has_a_non_report_receipt() -> None:
    receipt = ApiRunReceipt.from_runtime_result(
        _result(
            runtime_status=RuntimeStatus.FAILED,
            publication_status=None,
            terminal_reason="context_build_failed",
            with_trace=False,
        ),
        created_at_utc=NOW,
    )

    assert receipt.runtime_status is RuntimeStatus.FAILED
    assert receipt.trace_reference is None
    assert receipt.report_available is False


@pytest.mark.parametrize(
    "changes",
    (
        {"runtime_status": "completed", "trace_reference": None},
        {"publication_status": "rejected", "report_available": True},
        {"trace_reference": None, "report_available": True},
        {"created_at_utc": "2026-08-17T08:30:00"},
        {"private_report": "must not be accepted"},
    ),
)
def test_receipt_contract_rejects_inconsistent_or_extra_fields(changes) -> None:
    payload = ApiRunReceipt.from_runtime_result(
        _result(),
        created_at_utc=NOW,
    ).model_dump()
    payload.update(changes)

    with pytest.raises(ValidationError):
        ApiRunReceipt.model_validate(payload)


def test_receipt_reference_must_belong_to_the_same_run() -> None:
    payload = ApiRunReceipt.from_runtime_result(
        _result(),
        created_at_utc=NOW,
    ).model_dump()
    payload["trace_reference"]["run_id"] = "different_run"

    with pytest.raises(ValidationError, match="run_id"):
        ApiRunReceipt.model_validate(payload)


def test_file_receipt_store_round_trips_strict_json_once(tmp_path: Path) -> None:
    store = FileRunReceiptStore(tmp_path)
    receipt = store.write_result(_result(), created_at_utc=NOW)
    receipt_path = tmp_path / receipt.run_id / "api_run_receipt.json"

    assert receipt_path.is_file()
    assert receipt_path.read_bytes().endswith(b"\n")
    assert store.read_receipt(receipt.run_id) == receipt
    assert json.loads(receipt_path.read_bytes())["schema_version"] == "1.0"

    original = receipt_path.read_bytes()
    with pytest.raises(FileExistsError, match="immutable"):
        store.write_result(_result(), created_at_utc=NOW)
    assert receipt_path.read_bytes() == original


def test_file_receipt_store_returns_an_exact_body_free_receipt_reference(
    tmp_path: Path,
) -> None:
    store = FileRunReceiptStore(tmp_path)
    written = store.write_result(_result(), created_at_utc=NOW)

    receipt, reference = store.read_receipt_with_reference(written.run_id)
    payload = (tmp_path / written.run_id / "api_run_receipt.json").read_bytes()

    assert receipt == written
    assert reference == RunReceiptReference(
        run_id=written.run_id,
        sha256=sha256(payload).hexdigest(),
    )
    assert set(reference.model_dump()) == {
        "schema_version",
        "run_id",
        "relative_path",
        "sha256",
    }


def test_file_receipt_store_rejects_unsafe_run_ids(tmp_path: Path) -> None:
    store = FileRunReceiptStore(tmp_path)

    for unsafe in ("../outside", "folder\\run", "C:drive", "NUL"):
        with pytest.raises(ValueError):
            store.read_receipt(unsafe)


def test_file_receipt_store_maps_bad_json_or_schema_to_integrity_error(
    tmp_path: Path,
) -> None:
    store = FileRunReceiptStore(tmp_path)
    receipt = store.write_result(_result(), created_at_utc=NOW)
    path = tmp_path / receipt.run_id / "api_run_receipt.json"
    path.write_text('{"private": "C:\\\\secret"}\n', encoding="utf-8")

    with pytest.raises(RunReceiptIntegrityError, match="receipt"):
        store.read_receipt(receipt.run_id)


def test_failed_atomic_commit_cleans_temp_and_writes_no_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = FileRunReceiptStore(tmp_path)

    def fail_link(source, target):
        raise OSError("simulated receipt commit failure")

    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(OSError, match="simulated receipt"):
        store.write_result(_result(), created_at_utc=NOW)

    run_directory = tmp_path / "receipt_demo"
    assert not (run_directory / "api_run_receipt.json").exists()
    assert list(run_directory.glob(".api_run_receipt.*.tmp")) == []
