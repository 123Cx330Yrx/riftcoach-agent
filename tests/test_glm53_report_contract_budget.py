import json
import socket

import pytest
from pydantic import ValidationError

from scripts.check_glm53_report_contract_budget import (
    ROOT, REPORT_PATH, ReportContractBudgetProof, build_report_contract_budget_proof, canonical_proof_bytes,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("budget proof must not connect")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_new_contract_full_path_uses_real_budget_and_rebuilds_frozen_evidence():
    proof = build_report_contract_budget_proof()
    assert canonical_proof_bytes(proof) == (ROOT / REPORT_PATH).read_bytes()
    assert len(proof.cases) == 3
    for row in proof.cases:
        assert row.calls_used == len(row.envelope.requests) == 9
        assert row.settled_total_tokens > 9 * 4096
        assert row.envelope.reserved_total_tokens <= proof.case_token_limit
        assert row.envelope.reserved_total_tokens > row.settled_total_tokens
        assert row.request_timeouts_s == (45.0,) * 9
        assert row.output_limits == (4096,) * 9
    assert len({row.plan_sha256 for row in proof.cases}) == 3
    assert len({row.snapshot_sha256 for row in proof.cases}) == 3


def test_new_proof_is_body_free_and_cannot_claim_real_or_formal_evidence():
    raw = (ROOT / REPORT_PATH).read_bytes()
    proof = ReportContractBudgetProof.model_validate_json(raw)
    assert proof.external_provider_calls == 0 and not proof.network_used
    for forbidden in ("bounded synthetic", "RiftCoach 教练式复盘报告", '"messages"', '"content"',
                      "早期死亡", "两局合成样本", "api_key", "reasoning_content"):
        assert forbidden not in raw.decode()


def test_proof_cannot_silently_measure_the_old_entry(monkeypatch):
    from scripts import check_glm53_report_contract_budget as module
    original = module.observe

    def legacy(*args, **kwargs):
        return original(*args, **{**kwargs, "report_contract_id": None})

    monkeypatch.setattr(module, "observe", legacy)
    with pytest.raises(ValueError, match="contract identity mismatch"):
        module.build_report_contract_budget_proof()


def test_existing_budget_wall_is_not_bypassed(monkeypatch, tmp_path):
    from scripts import probe_glm53_development_retrieval as probe
    from scripts.check_glm53_report_contract_budget import _MeteredWorstPathProvider
    from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID
    from app.rag.coaching_query import COACHING_QUERY_GUIDANCE_V1
    original = probe.BoundedRevisionBudgetedProvider

    def small_budget(**kwargs):
        return original(**{**kwargs, "case_max_tokens": 1000, "domain_max_tokens": 1000})

    monkeypatch.setattr(probe, "BoundedRevisionBudgetedProvider", small_budget)
    provider = _MeteredWorstPathProvider()
    result = probe.observe(provider, root=ROOT, runs_root=tmp_path,
                           retrieval_guidance=COACHING_QUERY_GUIDANCE_V1, report_contract_id=REPORT_CONTRACT_ID)
    assert result["resources"]["stop_code"] == "token_budget_exhausted"
    assert result["resources"]["calls_used"] == 0
    assert not provider.requests


@pytest.mark.parametrize("change", ["margin", "settlement", "timeout", "identity", "contract", "duplicate", "body", "digest"])
def test_tampered_budget_proof_is_rejected(change):
    payload = json.loads((ROOT / REPORT_PATH).read_bytes())
    row = payload["cases"][0]
    if change == "margin":
        row["token_margin"] += 1
    elif change == "settlement":
        row["settled_input_tokens"] = 1
    elif change == "timeout":
        row["request_timeouts_s"][0] = 90
    elif change == "identity":
        row["envelope"]["case_id"] = "old-case"
    elif change == "contract":
        payload["report_contract_sha256"] = "0" * 64
    elif change == "duplicate":
        payload["cases"][1] = row
    elif change == "body":
        row["body"] = "private report"
    else:
        payload["report_sha256"] = "0" * 64
    if change != "digest":
        from scripts.check_glm53_report_contract_budget import _digest
        payload["report_sha256"] = _digest({key: value for key, value in payload.items() if key != "report_sha256"})
    with pytest.raises(ValidationError):
        ReportContractBudgetProof.model_validate(payload)
