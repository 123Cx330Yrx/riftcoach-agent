from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import pytest

from app.runtime.models import (
    RuntimeArtifactReference,
    RuntimeIdentitySnapshot,
    RuntimePolicySnapshot,
    RuntimePublicationStatus,
)
from app.runtime.recorder import RuntimeRecorder
from app.runtime.signals import (
    ContextBuiltSignal,
    ExecutionValidatedSignal,
    PublicationDecidedSignal,
    RunCompletedSignal,
    RunStartedSignal,
)
from app.runtime.store import RuntimeTraceIntegrityError, RuntimeTraceStore


SHA_A = "a" * 64
SHA_B = "b" * 64


def trace():
    recorder = RuntimeRecorder(run_id="runtime_store_demo")
    recorder.emit(
        RunStartedSignal(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            runtime_policy_version="1.0.0",
        )
    )
    recorder.emit(
        ExecutionValidatedSignal(
            input_artifact_sha256s=(SHA_A, SHA_B),
        )
    )
    recorder.emit(
        ContextBuiltSignal(
            context_contract_version="1.0.0",
            estimated_context_units=8000,
        )
    )
    recorder.emit(
        PublicationDecidedSignal(
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
            artifact_sha256s=(SHA_A,),
        )
    )
    recorder.emit(
        RunCompletedSignal(
            publication_status=RuntimePublicationStatus.PUBLISHED,
            terminal_reason="quality_gate_passed",
        )
    )
    return recorder.build_trace(
        identity=RuntimeIdentitySnapshot(
            skill_name="recent-form-review",
            skill_version="0.2.0",
            context_contract_version="1.0.0",
            prompt_profile_id="recent-form-coach",
            prompt_profile_version="1.0.0",
            provider_id="offline-fake",
            provider_model="fake-v1",
            harness_version="1.0.0",
        ),
        policy=RuntimePolicySnapshot(
            policy_version="1.0.0",
            event_budget=256,
            max_iterations=4,
            max_tool_calls=3,
            timeout_s=30,
            max_context_tokens=16000,
            publish_score_threshold=85,
            max_revisions=1,
            allow_deterministic_fallback=True,
        ),
        artifacts=(
            RuntimeArtifactReference(
                kind="final_report",
                schema_version="1.0",
                relative_path="output/final_report.md",
                sha256=SHA_A,
                producer="review_harness",
            ),
        ),
    )


def test_store_writes_trace_before_harness_directory_exists_and_round_trips():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = RuntimeTraceStore(root, "runtime_store_demo")
        assert not store.run_directory.exists()

        expected = trace()
        reference = store.write_trace(expected)
        loaded = store.read_trace(reference)

        assert loaded == expected
        assert store.trace_path.is_file()
        assert reference.relative_path == "runtime_trace.json"
        assert reference.sha256 == hashlib.sha256(
            store.trace_path.read_bytes()
        ).hexdigest()


def test_store_serializes_strict_json_with_a_trailing_newline():
    with tempfile.TemporaryDirectory() as directory:
        store = RuntimeTraceStore(directory, "runtime_store_demo")
        store.write_trace(trace())

        payload = store.trace_path.read_bytes()

        assert payload.endswith(b"\n")
        assert json.loads(payload)["trace_schema_version"] == "1.0"


def test_store_rejects_duplicate_write_without_changing_original():
    with tempfile.TemporaryDirectory() as directory:
        store = RuntimeTraceStore(directory, "runtime_store_demo")
        store.write_trace(trace())
        original = store.trace_path.read_bytes()

        with pytest.raises(FileExistsError, match="immutable"):
            store.write_trace(trace())

        assert store.trace_path.read_bytes() == original


def test_store_rejects_trace_for_another_run():
    with tempfile.TemporaryDirectory() as directory:
        store = RuntimeTraceStore(directory, "another_run")

        with pytest.raises(ValueError, match="run_id"):
            store.write_trace(trace())


def test_store_rejects_unsafe_run_ids():
    with tempfile.TemporaryDirectory() as directory:
        for run_id in ("../outside", "folder\\run", "NUL", "run."):
            with pytest.raises(ValueError):
                RuntimeTraceStore(directory, run_id)


def test_read_detects_tampered_trace_bytes():
    with tempfile.TemporaryDirectory() as directory:
        store = RuntimeTraceStore(directory, "runtime_store_demo")
        reference = store.write_trace(trace())
        store.trace_path.write_text('{"tampered": true}\n', encoding="utf-8")

        with pytest.raises(RuntimeTraceIntegrityError, match="digest"):
            store.read_trace(reference)


def test_failed_atomic_replace_cleans_temp_and_leaves_no_trace(monkeypatch):
    with tempfile.TemporaryDirectory() as directory:
        store = RuntimeTraceStore(directory, "runtime_store_demo")

        def fail_replace(source, target):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(os, "replace", fail_replace)
        with pytest.raises(OSError, match="simulated"):
            store.write_trace(trace())

        assert not store.trace_path.exists()
        assert list(store.run_directory.glob(".runtime_trace.*.tmp")) == []
