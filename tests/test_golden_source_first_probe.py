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


def test_preview_and_retired_entry_do_not_open_credentials_or_provider(monkeypatch, tmp_path):
    import dotenv
    state, request, _ = prepared()
    monkeypatch.setattr(probe, "prepare", lambda _: (state, request, {"max_new_calls": 0}))
    monkeypatch.setattr(dotenv, "dotenv_values", lambda *_: pytest.fail("read credentials"))
    args = SimpleNamespace(execute=False, output_root=tmp_path, run_id="source-first-probe-scripted", ci_run="test")
    assert probe.run(args) == {"max_new_calls": 0}
    args.execute = True
    monkeypatch.setattr(probe, "prepare", lambda _: pytest.fail("retired entry read baseline"))
    with pytest.raises(ValueError, match="offline_only_after_failed_diagnostic"): probe.run(args)
    assert not (tmp_path / args.run_id).exists()


def test_full_audit_does_not_stop_at_first_schema_error_or_repair_response():
    from scripts.audit_golden_source_first_result import inspect_response
    state, _, final = prepared()
    first = final["audits"][1]["claims"][0]
    duplicate = dict(first)
    first.pop("comparisons")
    duplicate["comparisons"] = [dict(duplicate["comparisons"][0], operand_refs=[999])]
    final["audits"][1]["claims"].append(duplicate)
    raw = compact(final)
    result = inspect_response(state, raw)
    assert compact(final) == raw
    assert any(e["code"] == "missing" for e in result["schema_errors"])
    assert any(e["code"] == "comparison_operand_set_mismatch"
               for row in result["claims"] for e in row["errors"])
    assert not result["response_repaired"] and not result["semantic_approval"]
