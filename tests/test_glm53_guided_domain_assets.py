import json
from pathlib import Path

import pytest

from app.evaluation.glm53_guided_domain_assets import admit_guided_domain_assets


ROOT = Path(__file__).resolve().parents[1]


def test_guided_v4_asset_bundle_admits_without_provider_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("asset admission must not perform provider I/O")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    bundle = admit_guided_domain_assets(project_root=ROOT)
    assert bundle.dataset.case_count == 4
    assert bundle.budget.case_max_calls == 9
    assert bundle.budget.external_provider_calls == 0
    assert bundle.protocol.retrieval_guidance_id == "coaching-query-guidance-v1"


def test_guided_v4_budget_is_bound_to_plan_and_context():
    bundle = admit_guided_domain_assets(project_root=ROOT)
    assert bundle.budget.input_plan_sha256 == bundle.input_plan.execution_plan.plan_sha256
    assert bundle.budget.snapshot_sha256 == bundle.context_snapshot_sha256
    assert tuple(row["case_id"] for row in bundle.budget.cases) == tuple(
        row.case_id for row in bundle.input_plan.artifact.cases
    )


def test_guided_v4_protocol_rejects_historical_identity(tmp_path):
    source = ROOT / "data/evaluation/glm53_flash_guided_domain_protocol_v4.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["protocol_id"] = "glm53-flash-retrieval-hardened-domain-observation-v3"
    target = tmp_path / source.name
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        from app.evaluation.glm53_guided_domain_assets import GuidedDomainProtocol

        GuidedDomainProtocol.model_validate_json(target.read_bytes())
