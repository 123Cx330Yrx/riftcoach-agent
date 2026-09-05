from __future__ import annotations

from pathlib import Path

from app.evaluation.glm53_retrieval_hardened_domain_v3_gate import (
    RetrievalV3DomainGateOptions,
    RetrievalV3PreflightStatus,
    run_retrieval_cli,
)


ROOT = Path(__file__).resolve().parents[1]


def test_retrieval_gate_stops_before_provider_until_public_ci() -> None:
    result = run_retrieval_cli(
        RetrievalV3DomainGateOptions(confirm_real_call=False, preflight_only=True),
        repository_root=ROOT,
        environment_loader=lambda _root: (_ for _ in ()).throw(AssertionError()),
        provider_factory=lambda _settings: (_ for _ in ()).throw(AssertionError()),
    )
    assert isinstance(result, RetrievalV3PreflightStatus)
    assert result.status == "pending_public_ci"
    assert result.external_provider_calls == 0
    assert result.held_out_executed is False

