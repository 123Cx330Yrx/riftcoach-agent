from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.provider_capability_result_contracts import (
    GLM53FlashResponseDiagnostic,
    LegacyTransportGenerationSplitReport,
    LegacyTransportGenerationSplitReportCorrected,
)


RESULT_ROOT = Path("data/evaluation/results/provider_capabilities")


@pytest.mark.parametrize(
    ("name", "model"),
    (
        (
            "zhipu_glm53_flash_response_completion_diagnostic_v1.json",
            GLM53FlashResponseDiagnostic,
        ),
        (
            "zhipu_glm53_flash_transport_generation_split_diagnostic_rq188_v1.json",
            LegacyTransportGenerationSplitReport,
        ),
        (
            "zhipu_glm53_flash_transport_generation_split_diagnostic_rq188_corrected_v1.json",
            LegacyTransportGenerationSplitReportCorrected,
        ),
    ),
)
def test_immutable_historical_results_match_their_bound_contract(name, model) -> None:
    model.model_validate_json((RESULT_ROOT / name).read_text(encoding="utf-8"))


def test_historical_contracts_reject_identity_drift() -> None:
    path = RESULT_ROOT / "zhipu_glm53_flash_response_completion_diagnostic_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["diagnostic_code_sha"] = "0" * 40

    with pytest.raises(ValidationError):
        GLM53FlashResponseDiagnostic.model_validate(payload)


def test_historical_contracts_reject_body_or_unknown_fields() -> None:
    path = RESULT_ROOT / "zhipu_glm53_flash_transport_generation_split_diagnostic_rq188_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["observations"][0]["response_body"] = "must not be retained"

    with pytest.raises(ValidationError):
        LegacyTransportGenerationSplitReport.model_validate(payload)
