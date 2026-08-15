from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adjudicate_deepseek_resource_calibration import adjudicate
from tests.test_provider_resource_calibration import REAL_RESULT


def test_adjudication_cli_writes_once_without_provider_io(tmp_path: Path) -> None:
    result = (
        tmp_path
        / "data/evaluation/results/provider_capabilities/calibration.json"
    )
    output = (
        tmp_path
        / "data/evaluation/results/provider_capabilities/adjudication.json"
    )
    result.parent.mkdir(parents=True)
    result.write_bytes(REAL_RESULT.read_bytes())

    record = adjudicate(
        result_path=result,
        output_path=output,
        repository_root=tmp_path,
    )

    assert record.status == "incomplete"
    assert record.external_provider_calls == 0
    assert record.billable_cost is None
    assert output.is_file()
    with pytest.raises(FileExistsError, match="immutable"):
        adjudicate(
            result_path=result,
            output_path=output,
            repository_root=tmp_path,
        )


def test_adjudication_cli_rejects_paths_outside_result_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="inside provider results"):
        adjudicate(
            result_path=REAL_RESULT,
            output_path=tmp_path / "outside.json",
            repository_root=tmp_path,
        )
