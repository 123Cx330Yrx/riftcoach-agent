"""Create a no-I/O adjudication for immutable DeepSeek calibration evidence."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.evaluation.provider_resource_calibration import (
    RealResourceCalibrationResult,
    build_resource_calibration_adjudication,
)


_DEFAULT_RESULT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_resource_calibration_v1.json"
)
_DEFAULT_OUTPUT = Path(
    "data/evaluation/results/provider_capabilities/"
    "deepseek_v4_pro_resource_calibration_v1_adjudication.json"
)


def adjudicate(
    *,
    result_path: Path,
    output_path: Path,
    repository_root: Path = PROJECT_ROOT,
):
    root = repository_root.resolve()
    result = _inside_result_root(root, result_path)
    output = _inside_result_root(root, output_path)
    if result == output:
        raise ValueError("result and adjudication paths must differ")
    if not result.is_file():
        raise FileNotFoundError("immutable calibration result does not exist")
    if output.exists():
        raise FileExistsError("calibration adjudication is immutable")

    raw = result.read_bytes()
    parsed = RealResourceCalibrationResult.model_validate_json(raw)
    record = build_resource_calibration_adjudication(
        result=parsed,
        calibration_result_sha256=hashlib.sha256(raw).hexdigest(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(record.model_dump_json(indent=2))
        stream.write("\n")
    return record


def _inside_result_root(root: Path, value: Path) -> Path:
    allowed = (
        root / "data/evaluation/results/provider_capabilities"
    ).resolve()
    path = value if value.is_absolute() else root / value
    resolved = path.resolve()
    if not resolved.is_relative_to(allowed) or resolved.suffix.lower() != ".json":
        raise ValueError("path must be a JSON file inside provider results")
    return resolved


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Adjudicate immutable DeepSeek resource calibration evidence."
    )
    parser.add_argument("--result", type=Path, default=_DEFAULT_RESULT)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    values = _parse_args(argv)
    record = adjudicate(
        result_path=values.result,
        output_path=values.output,
    )
    print(
        f"status={record.status} "
        f"external_calls={record.external_provider_calls_in_result} "
        f"normalized_responses={record.normalized_responses} "
        f"usage_complete={str(record.usage_complete).lower()} "
        "external_provider_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
