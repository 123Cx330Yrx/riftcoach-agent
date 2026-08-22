"""No-I/O admission and immutable output lifecycle for the 8B holdout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import IO

from app.evaluation.stage8_adoption import (
    evaluate_adoption_gate,
    load_adoption_gate,
)

from .models import ExperimentRecord, ExperimentSplit, HoldoutAdmission
from .runner import (
    ExperimentViolation,
    build_experiment_id,
    build_holdout_admission_id,
    validate_experiment_record,
)


_MAX_RESULT_BYTES = 2 * 1024 * 1024
_GATE = Path("data/evaluation/stage8/advanced_adoption_gate_v1.json")
_CASES = Path("data/evaluation/stage8/advanced_adoption_cases_v1.json")


def load_experiment_record(path: str | Path) -> ExperimentRecord:
    result_path = Path(path)
    try:
        raw = result_path.read_bytes()
    except OSError as exc:
        raise ExperimentViolation("experiment_result_unreadable") from exc
    if not raw or len(raw) > _MAX_RESULT_BYTES:
        raise ExperimentViolation("experiment_result_unreadable")
    try:
        decoded = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
        normalized = json.dumps(
            decoded,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        return validate_experiment_record(
            ExperimentRecord.model_validate_json(normalized, strict=True)
        )
    except ExperimentViolation:
        raise
    except (ValueError, TypeError) as exc:
        raise ExperimentViolation("experiment_result_invalid") from exc


def write_experiment_record_exclusive(
    path: str | Path,
    record: ExperimentRecord,
) -> None:
    if not isinstance(record, ExperimentRecord):
        raise TypeError("record must be an ExperimentRecord")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(record.model_dump_json(indent=2))
        stream.write("\n")


def prepare_holdout_admission(
    *,
    repository_root: str | Path,
    development_result_path: str | Path,
    code_sha: str,
    public_ci_sha: str,
    confirm_public_ci_success: bool,
    confirm_holdout: bool,
) -> HoldoutAdmission:
    if public_ci_sha != code_sha:
        raise ExperimentViolation("public_ci_identity_mismatch")
    if not confirm_public_ci_success:
        raise ExperimentViolation("public_ci_confirmation_required")
    if not confirm_holdout:
        raise ExperimentViolation("holdout_confirmation_required")
    development = load_experiment_record(development_result_path)
    if (
        development.split is not ExperimentSplit.DEVELOPMENT
        or development.code_sha != code_sha
        or development.verdict != "eligible_for_holdout"
        or development.external_io_calls != 0
        or development.holdout_executions != 0
    ):
        raise ExperimentViolation("development_admission_invalid")

    root = Path(repository_root).resolve()
    loaded = load_adoption_gate(root / _GATE, root / _CASES)
    decision = evaluate_adoption_gate(loaded)
    if (
        development.gate_digest != decision.gate_digest
        or development.case_set_sha256 != loaded.case_set_file_sha256
    ):
        raise ExperimentViolation("development_identity_drift")
    admission_id = build_holdout_admission_id(
        development_experiment_id=development.experiment_id,
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        gate_digest=decision.gate_digest,
        case_set_sha256=loaded.case_set_file_sha256,
    )
    holdout_experiment_id = build_experiment_id(
        split=ExperimentSplit.HOLDOUT,
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        gate_digest=decision.gate_digest,
        case_set_sha256=loaded.case_set_file_sha256,
    )
    return HoldoutAdmission(
        admission_id=admission_id,
        holdout_experiment_id=holdout_experiment_id,
        development_experiment_id=development.experiment_id,
        code_sha=code_sha,
        public_ci_sha=public_ci_sha,
        gate_digest=decision.gate_digest,
        case_set_sha256=loaded.case_set_file_sha256,
    )


class ImmutableExperimentOutput:
    """Exclusive reservation; abandon leaves a sentinel and consumes the path."""

    def __init__(self, path: Path, experiment_id: str, stream: IO[str]) -> None:
        self.path = path
        self.experiment_id = experiment_id
        self._stream = stream
        self._committed = False

    @classmethod
    def reserve(
        cls,
        path: str | Path,
        *,
        experiment_id: str,
    ) -> "ImmutableExperimentOutput":
        if not _is_sha256(experiment_id):
            raise ValueError("experiment_id must be a SHA-256 digest")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        stream = output.open("x", encoding="utf-8", newline="\n")
        return cls(output, experiment_id, stream)

    def commit(self, record: ExperimentRecord) -> None:
        if self._committed or self._stream.closed:
            raise RuntimeError("experiment output is already finalized")
        if not isinstance(record, ExperimentRecord):
            raise TypeError("record must be an ExperimentRecord")
        if record.experiment_id != self.experiment_id:
            raise ValueError("record does not match the reserved experiment")
        self._stream.write(record.model_dump_json(indent=2))
        self._stream.write("\n")
        self._stream.flush()
        self._stream.close()
        self._committed = True

    def abandon(self) -> None:
        if not self._stream.closed:
            self._stream.close()


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise ExperimentViolation("experiment_result_invalid")
        output[key] = value
    return output


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


__all__ = [
    "ImmutableExperimentOutput",
    "load_experiment_record",
    "prepare_holdout_admission",
    "write_experiment_record_exclusive",
]
