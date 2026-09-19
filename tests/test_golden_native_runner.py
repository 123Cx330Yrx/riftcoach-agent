"""Synthetic runner contracts and receipts; these do not prove model quality."""
from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from app.evaluation import golden_semantic_review as candidate
from app.evaluation.golden_review_experiment import compact, digest
from app.harness.steps import EvaluationVerdict
from scripts import run_golden_native_review as runner
from tests.test_golden_integrated_review import ReplayProvider
from tests.test_golden_semantic_review import evaluation_request, opinion, request_data


@pytest.fixture
def control(tmp_path, monkeypatch):
    req = evaluation_request()
    source = tmp_path / "source.json"
    source.write_text('{"fixture":"local-only"}', encoding="utf-8")
    case = dict(id="synthetic-positive", report=req.report, report_sha256=digest(req.report),
        target=req.report, expected_report="accept", expected_categories=["fact_error"])
    manifest = dict(source_bindings=dict(source_run="source-run", base_report="base-report.md",
        files=[dict(path=source.name, sha256=hashlib.sha256(source.read_bytes()).hexdigest())]),
        user_utterance=req.user_utterance, cases=[case])
    path = tmp_path / "manifest.json"
    path.write_text(compact(manifest), encoding="utf-8")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "DATASET", path)
    loads = []

    def load(source_run, base_report):
        loads.append((source_run, base_report))
        assert source_run == tmp_path / "source-run"
        assert base_report == tmp_path / "base-report.md"
        return req.player_summary, req.deterministic_report, req.knowledge, []

    monkeypatch.setattr(runner, "load_inputs", load)
    args = SimpleNamespace(execute=False, case_index=1, run_id="native-review-synthetic",
        ci_run="synthetic-ci", env_file=tmp_path / "unused.env", output_root=tmp_path / "runs")
    return SimpleNamespace(req=req, source=source, case=case, manifest=manifest, path=path,
        loads=loads, args=args)


def forbidden(*args, **kwargs):
    pytest.fail("forbidden external or later-stage operation was reached")


def isolate_external(monkeypatch):
    import dotenv
    import app.providers.config as config
    monkeypatch.setattr(dotenv, "dotenv_values", forbidden)
    monkeypatch.setattr(config, "load_zhipu_settings", forbidden)
    monkeypatch.setattr(runner, "ReceiptedStreamProvider", forbidden)


def enable_synthetic_execution(control, monkeypatch, callback, *, tokens=13):
    """Only bypass qualification dispatch; never give the candidate live status."""
    import dotenv
    import app.providers.config as config
    events = []
    provider = ReplayProvider(callback, tokens=tokens)
    monkeypatch.setattr(candidate, "require_live_qualification", lambda: events.append("qualification"))

    def ci(run_id):
        events.append("exact-ci")
        assert run_id == control.args.ci_run
        return "a" * 40

    def secrets(path):
        events.append("secrets")
        assert path == control.args.env_file
        return {"synthetic": "not-a-credential"}

    def settings(values):
        events.append("settings")
        assert values == {"synthetic": "not-a-credential"}
        return "synthetic-settings"

    def factory(**kwargs):
        events.append("provider")
        assert kwargs["settings"] == "synthetic-settings"
        assert kwargs["directory"].is_relative_to(control.args.output_root)
        return provider

    monkeypatch.setattr(runner, "verify_public_ci", ci)
    monkeypatch.setattr(dotenv, "dotenv_values", secrets)
    monkeypatch.setattr(config, "load_zhipu_settings", settings)
    monkeypatch.setattr(runner, "ReceiptedStreamProvider", factory)
    control.args.execute = True
    return provider, events


def read_receipt(control):
    return candidate.strict_json((control.args.output_root / control.args.run_id / "receipt.json").read_text(encoding="utf-8"))


def test_execute_offline_gate_precedes_prepare_ci_credentials_and_provider(control, monkeypatch):
    control.args.execute = True
    monkeypatch.setattr(candidate, "LIVE_STATUS", "offline_only")
    monkeypatch.setattr(runner, "prepare", forbidden)
    monkeypatch.setattr(runner, "verify_public_ci", forbidden)
    isolate_external(monkeypatch)
    with pytest.raises(ValueError, match=candidate.LIVE_BLOCK_REASON):
        runner.run(control.args)
    assert not control.args.output_root.exists()


def test_preview_is_local_and_control_labels_never_enter_model_input(control, monkeypatch):
    monkeypatch.setattr(candidate, "require_live_qualification", forbidden)
    monkeypatch.setattr(runner, "verify_public_ci", forbidden)
    isolate_external(monkeypatch)
    original = candidate.request
    requests = []

    def capture(*args, **kwargs):
        request = original(*args, **kwargs)
        requests.append(request)
        return request

    monkeypatch.setattr(candidate, "request", capture)
    plan = runner.run(control.args)
    assert len(control.loads) == len(requests) == 1
    assert plan["selected_cases"] == [control.case["id"]]
    assert plan["manifest_sha256"] == hashlib.sha256(control.path.read_bytes()).hexdigest()
    assert plan["report_sha256"] == control.case["report_sha256"]
    assert plan["labels_sent_to_model"] is plan["production_admitted"] is plan["semantic_approval"] is False
    data = request_data(requests[0])

    def keys(value):
        if isinstance(value, dict):
            yield from value
            for child in value.values():
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert not {"expected_report", "expected_categories", "target", "target_labels"}.intersection(keys(data))
    assert control.case["id"] not in compact(data)
    assert control.req.report in compact(data)
    assert not control.args.output_root.exists()


def test_issue_only_entry_uses_its_own_qualification_and_schema(control, monkeypatch):
    from app.evaluation import golden_native_issues_review as active
    isolate_external(monkeypatch)
    preview = runner.run(control.args, candidate_module=active)
    assert preview['experiment_id'] == active.EXPERIMENT_ID
    control.args.execute = True
    monkeypatch.setattr(active, 'LIVE_STATUS', 'offline_qualification')
    monkeypatch.setattr(runner, 'prepare', forbidden)
    with pytest.raises(ValueError, match=active.LIVE_BLOCK_REASON):
        runner.run(control.args, candidate_module=active)


def test_issue_only_execution_reuses_exact_ci_and_receipt_orchestration(control, monkeypatch):
    from app.evaluation import golden_native_issues_review as active
    from tests.test_golden_native_issues_review import opinion as issue_opinion
    inputs = active.build_inputs(control.req)
    provider, events = enable_synthetic_execution(control, monkeypatch, lambda *_: compact(issue_opinion(inputs)))
    monkeypatch.setattr(active, 'require_live_qualification', lambda: events.append('issue-only-qualification'))
    outcome = runner.run(control.args, candidate_module=active)
    assert outcome['automatic_path_pass'] and len(provider.requests) == 1
    assert provider.requests[0].response_contract.version == '3.0.0'
    assert events[:2] == ['issue-only-qualification', 'exact-ci']
    assert read_receipt(control)['experiment_id'] == active.EXPERIMENT_ID


@pytest.mark.parametrize("change,code", [
    ("source", "native_control_source_changed"),
    ("report_hash", "native_control_report_changed"),
    ("target_missing", "native_control_report_changed"),
    ("target_repeated", "native_control_report_changed"),
    ("duplicate_identity", "native_control_duplicate_identity"),
    ("label", "native_control_label_invalid"),
    ("case_index", "native_control_case_index_invalid"),
])
def test_prepare_rejects_changed_or_ambiguous_frozen_control(control, change, code):
    index = 1
    if change == "source":
        control.source.write_text("changed", encoding="utf-8")
    elif change == "report_hash":
        control.case["report_sha256"] = "0" * 64
    elif change == "target_missing":
        control.case["target"] = "未出现的句子"
    elif change == "target_repeated":
        control.case["report"] *= 2
        control.case["report_sha256"] = digest(control.case["report"])
    elif change == "duplicate_identity":
        control.manifest["cases"].append(deepcopy(control.case))
    elif change == "label":
        control.case["expected_report"] = "arbitrary"
    elif change == "case_index":
        index = 2
    control.path.write_text(compact(control.manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=code):
        runner.prepare(index)
    if change == "source":
        assert control.loads == []


def test_ci_failure_stops_before_secret_provider_and_output_creation(control, monkeypatch):
    control.args.execute = True
    monkeypatch.setattr(candidate, "require_live_qualification", lambda: None)
    isolate_external(monkeypatch)

    def failed_ci(run_id):
        assert run_id == control.args.ci_run
        raise ValueError("exact_sha_ci_not_qualified")

    monkeypatch.setattr(runner, "verify_public_ci", failed_ci)
    with pytest.raises(ValueError, match="exact_sha_ci_not_qualified"):
        runner.run(control.args)
    assert not control.args.output_root.exists()


@pytest.mark.parametrize("run_id", ["../escape", "native-review-../../escape", "native-review-x/child", "native-review-C:\\escape"])
def test_run_id_cannot_escape_output_directory(control, monkeypatch, run_id):
    control.args.execute, control.args.run_id = True, run_id
    monkeypatch.setattr(candidate, "require_live_qualification", lambda: None)
    monkeypatch.setattr(runner, "verify_public_ci", forbidden)
    isolate_external(monkeypatch)
    with pytest.raises(ValueError, match="native_run_id_invalid"):
        runner.run(control.args)
    assert not control.args.output_root.exists()


def test_success_uses_injected_native_scorer_and_preserves_real_exchange_accounting(control, monkeypatch):
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(control.req)
    raw = compact(opinion(inputs))
    provider, events = enable_synthetic_execution(control, monkeypatch, lambda *_: raw)
    score = runner.score_case

    def native_score(case, result):
        events.append("native-score")
        # This native result has no legacy claim/audits payload requirement.
        return score(case, result)

    monkeypatch.setattr(runner, "score_case", native_score)
    outcome = runner.run(control.args)
    assert events == ["qualification", "exact-ci", "secrets", "settings", "provider", "native-score"]
    assert len(provider.requests) == 1
    assert outcome["matched"] and outcome["automatic_path_pass"]
    assert not outcome["manual_semantic_acceptance"] and not outcome["semantic_approval"]
    receipt = read_receipt(control)
    assert receipt["head_sha"] == "a" * 40 and receipt["ci_run"] == control.args.ci_run
    assert receipt["reserved_calls"] == receipt["completed_calls"] == 1
    assert receipt["input_tokens"] == receipt["output_tokens"] == 13
    assert receipt["unknown_usage_calls"] == 0 and receipt["cases"] == [outcome]
    case_dir = control.args.output_root / control.args.run_id / control.case["id"]
    assert candidate.strict_json((case_dir / "response-001.json").read_text(encoding="utf-8"))["content"] == raw
    assert candidate.strict_json((case_dir / "initial-correction-journal.json").read_text(encoding="utf-8"))["raw"] == raw


@pytest.mark.parametrize("interrupt", [False, True])
def test_failed_or_interrupted_second_exchange_keeps_completed_and_unknown_usage(control, monkeypatch, interrupt):
    inputs = candidate.NativeBusinessReviewWorkflow.build_inputs(control.req)
    invalid = opinion(inputs)
    invalid["reviews"] = []

    def callback(_, call):
        if call == 1:
            return compact(invalid)
        raise KeyboardInterrupt() if interrupt else RuntimeError("synthetic transport failure")

    provider, _ = enable_synthetic_execution(control, monkeypatch, callback, tokens=17)
    if interrupt:
        with pytest.raises(KeyboardInterrupt):
            runner.run(control.args)
    else:
        outcome = runner.run(control.args)
        assert not outcome["valid"] and not outcome["matched"]
        assert outcome["interrupted"] and outcome["stop_reason"] == "protocol_or_execution_failure"
    assert len(provider.requests) == 2
    receipt = read_receipt(control)
    assert receipt["reserved_calls"] == 2 and receipt["completed_calls"] == 1
    assert receipt["unknown_usage_calls"] == 1
    assert receipt["input_tokens"] == receipt["output_tokens"] == 17
    assert not receipt["manual_semantic_acceptance"]
    assert receipt["cases"] == ([] if interrupt else [outcome])
    result_path = control.args.output_root / control.args.run_id / control.case["id"] / "result.json"
    saved = candidate.strict_json(result_path.read_text(encoding="utf-8"))
    assert saved["completed_calls"] == 1 and saved["unknown_usage_calls"] == 1


def test_score_location_category_and_threshold_are_only_structural_signals(control):
    case = deepcopy(control.case)
    result = SimpleNamespace(verdict=EvaluationVerdict.PASS, score=84, issues=[])
    assert not runner.score_case(case, result)["matched"]
    result.score = 85
    accepted = runner.score_case(case, result)
    assert accepted["matched"] and not accepted["semantic_approval"]
    case["expected_report"] = "reject"
    result.verdict = EvaluationVerdict.NEEDS_REVISION
    result.issues = [dict(quote="unrelated paragraph", category="fact_error")]
    assert not runner.score_case(case, result)["matched"]
    result.issues = [dict(quote=case["target"], category="other")]
    located = runner.score_case(case, result)
    assert located["matched"] and located["target_location_flagged"]
    assert not located["suggested_category_matched"] and not located["semantic_approval"]
    result.issues[0]["category"] = "fact_error"
    matched = runner.score_case(case, result)
    assert matched["matched"] and matched["suggested_category_matched"]
    assert not matched["semantic_approval"]
