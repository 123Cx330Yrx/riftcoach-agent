"""Full-source independent editing preparation and bounded runner regression."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.providers.models import ChatResponse, TokenUsage
from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE as PROFILE
from scripts import run_independent_edit_pair as runner
from scripts.check_source_bound_report import original_request
from scripts.native_contract_options import body
from scripts.run_review_model_comparison import observe
from tests.test_review_model_comparison import decision, fake_provider
from tests.test_native_editor_product_budget import offline


def response(text):
    return ChatResponse(content=text, provider="zhipu", model="glm-5.3-flash",
        finish_reason="stop", usage=TokenUsage(10, 10))


def provider_for(responses):
    provider = fake_provider(responses)
    provider.model_name = PROFILE.model
    provider.thinking_profile_id = PROFILE.profile_id
    provider.transport_id = CAPACITY_TRANSPORT_ID
    return provider


def test_preparation_preserves_reports_all_sources_without_old_opinions_or_assembly(monkeypatch):
    original_read = Path.read_text
    def read(path, *args, **kwargs):
        assert "data/runs/" not in path.as_posix() and path.name != ".env"
        return original_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    variants, plan = runner.prepare()
    req, saved, _ = original_request()
    assert [v[1].source.report for v in variants] == [req.report, saved["host_reference"]["report"]]
    for (_, inputs, prepared), cell in zip(variants, plan["cells"], strict=True):
        old = runner.RoleReviewWorkflow.make_request(inputs)
        data = body(prepared)
        assert data.pop("original_report_markdown") == inputs.source.report
        assert data == body(old) and prepared.messages[2] == old.messages[2]
        assert not prepared.tools and prepared.response_contract is None
        assert not {"accepted_review", "previous_review", "original_review"} & body(prepared).keys()
        assert "riftcoach:knowledge-sources" not in prepared.messages[1].content
        assert cell["expected_host_only"] not in compact(body(prepared))
        assert hashlib.sha256(validate_request(prepared, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest() == cell["request_sha256"]
        assert prepared.max_tokens == 32768 and prepared.timeout_s == 300
    assert plan["proposed_diagnostic_budget"]["max_calls"] == 2
    assert plan["proposed_diagnostic_budget"]["max_seconds_total"] == 600
    assert plan["provider_requests"] == 0 and not plan["production_admitted"]
    saved_plan = json.loads((runner.ROOT / "data/evaluation/results/golden_independent_edit_preparation_v1.json").read_text(encoding="utf-8"))
    assert saved_plan == dict(preparation_plan=plan, preparation_plan_sha256=digest(compact(plan)))


def test_host_rejection_stops_after_unchanged_wrong_report_not_format_success(tmp_path):
    variants, plan = runner.prepare()
    provider = provider_for([response(variants[0][1].source.report)])
    result = observe(provider, tmp_path, variants, plan, adjudicate=decision(False),
        reviewer_profile=PROFILE, transport_id=CAPACITY_TRANSPORT_ID, inspect_response=runner.inspect_edit)
    assert result["error_code"] == "model_comparison_semantic_failure"
    assert result["reserved_calls"] == 1 and result["unknown_usage_calls"] == 0
    assert result["cases"][0]["valid"] and not result["cases"][0]["edit_changed"]
    journal = json.loads((tmp_path / variants[0][0] / "journal.json").read_text(encoding="utf-8"))
    assert journal["raw"] == variants[0][1].source.report and not journal["semantic_approval"]
    assert not (tmp_path / variants[1][0]).exists()


def test_scripted_edit_then_keep_records_actual_outputs_under_same_batch(tmp_path):
    variants, plan = runner.prepare()
    reference = variants[1][1].source.report
    provider = provider_for([response(reference), response(reference)])
    result = observe(provider, tmp_path, variants, plan, adjudicate=decision(True),
        reviewer_profile=PROFILE, transport_id=CAPACITY_TRANSPORT_ID, inspect_response=runner.inspect_edit)
    assert result["pair_accepted"] and result["reserved_calls"] == 2
    assert [row["edit_changed"] for row in result["cases"]] == [True, False]
    assert result["input_tokens"] == result["output_tokens"] == 20
    assert not result["production_admitted"]


def test_editor_cannot_introduce_unknown_citation_and_raw_response_survives(tmp_path):
    variants, plan = runner.prepare()
    bad = variants[0][1].source.report + "\n[K999]"
    provider = provider_for([response(bad)])
    result = observe(provider, tmp_path, variants, plan, adjudicate=lambda *_: pytest.fail("invalid output reached host"),
        reviewer_profile=PROFILE, transport_id=CAPACITY_TRANSPORT_ID, inspect_response=runner.inspect_edit)
    assert result["error_code"] == "unknown_report_citation"
    assert result["reserved_calls"] == 1 and result["unknown_usage_calls"] == 0
    saved = json.loads((tmp_path / variants[0][0] / "response.json").read_text(encoding="utf-8"))
    assert saved["content"] == bad


def test_old_authorization_cannot_start_new_plan_or_touch_ci_or_credentials(monkeypatch):
    import scripts.run_golden_inference_development as ci
    monkeypatch.setattr(ci, "verify_public_ci", lambda *_: pytest.fail("unauthorized plan reached CI"))
    with pytest.raises(ValueError, match="independent_edit_specific_plan_approval_required"):
        runner.run(SimpleNamespace(execute=True, approval_plan_sha="8a4b189416a7fede2c7690f9a7dde1c993504d00294739135e4bfb7d48a8dde2",
            env_file=Path("missing.env"), ci_run="old"))


def test_existing_batch_cannot_restart_even_with_matching_plan_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "RUN_DIRECTORY", tmp_path)
    _, plan = runner.prepare()
    with pytest.raises(ValueError, match="independent_edit_batch_exists"):
        runner.run(SimpleNamespace(execute=True, approval_plan_sha=digest(compact(plan)), env_file=None, ci_run="old"))


def test_failed_execution_is_nonzero_but_preview_and_success_can_exit_normally(monkeypatch):
    monkeypatch.setattr(runner, "run", lambda _: {"pair_accepted": False})
    with pytest.raises(SystemExit) as stopped:
        runner.main(["--execute"])
    assert stopped.value.code == 2
    runner.main([])
    monkeypatch.setattr(runner, "run", lambda _: {"pair_accepted": True})
    runner.main(["--execute"])
