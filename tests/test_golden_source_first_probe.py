"""A diagnostic is exactly one new receipted call, never a replayed full run."""
from types import SimpleNamespace

import pytest

from app.evaluation import golden_provisional_reassessment as provisional
from app.evaluation import golden_source_first_review as candidate
from app.evaluation.golden_review_experiment import compact
from scripts import run_golden_source_first_probe as probe
from tests.test_golden_comparison_reassessment import inputs_for, assessment
from tests.test_golden_integrated_review import ReplayProvider


def prepared():
    inputs = inputs_for()
    first, final = assessment(inputs)
    state = provisional.prepare(compact(first), inputs)
    return state, candidate.build_request(state), final


@pytest.mark.parametrize("malformed", [False, True])
def test_one_new_call_preserves_response_usage_even_if_final_validation_fails(tmp_path, malformed):
    state, request, final = prepared()
    if malformed:
        final["audits"][1]["claims"][0]["comparisons"][0]["operand_refs"].pop()
    provider = ReplayProvider(lambda *_: compact(final))
    result = probe.observe(provider, tmp_path, state, request)
    assert len(provider.requests) == 1 and result["reserved_calls"] == 1
    assert result["completed_calls"] == 1 and result["unknown_usage_calls"] == 0
    assert result["input_tokens"] + result["output_tokens"] == 20
    assert result["valid"] is not malformed
    assert not result["full_workflow"] and not result["manual_semantic_acceptance"]
    assert (tmp_path / "response.json").exists() and (tmp_path / "request.json").exists()


def test_interruption_accounts_for_unknown_usage_without_retry(tmp_path):
    state, request, _ = prepared()
    provider = ReplayProvider(lambda *_: (_ for _ in ()).throw(RuntimeError("interrupted")))
    result = probe.observe(provider, tmp_path, state, request)
    assert len(provider.requests) == 1
    assert not result["valid"] and result["unknown_usage_calls"] == 1
    assert result["completed_calls"] == 0


def test_preview_and_failed_ci_do_not_open_credentials_or_provider(monkeypatch, tmp_path):
    import dotenv
    state, request, _ = prepared()
    monkeypatch.setattr(probe, "prepare", lambda _: (state, request, {"max_new_calls": 1}))
    monkeypatch.setattr(dotenv, "dotenv_values", lambda *_: pytest.fail("read credentials"))
    monkeypatch.setattr(probe, "ReceiptedStreamProvider", lambda **_: pytest.fail("opened Provider"))
    monkeypatch.setattr(probe, "verify_public_ci", lambda _: (_ for _ in ()).throw(ValueError("ci_missing")))
    args = SimpleNamespace(execute=False, output_root=tmp_path, run_id="source-first-probe-scripted", ci_run="test")
    assert probe.run(args) == {"max_new_calls": 1}
    args.execute = True
    with pytest.raises(ValueError, match="ci_missing"): probe.run(args)
    assert not (tmp_path / args.run_id).exists()
