"""Four known development cases, not independent model-quality evidence."""
from dataclasses import replace
import json

import pytest

from app.evaluation.coach_grounded_development import (
    MEMORY_MARKER, execute_suite_once, prepare_observation, prepare_suite, run_observation,
)
from tests.test_coach_grounded_development import ROOT, isolated_root, no_network
from tests.test_coach_contract_repair import RepairProvider

SUITE = "coach-grounded-suite-test-01"


class Remembering(RepairProvider):
    def __init__(self, *, leak=False, acknowledge=True):
        super().__init__(problem="none")
        self.leak, self.acknowledge = leak, acknowledge

    def chat(self, request):
        response = super().chat(request)
        if response.content and not request.response_contract:
            content = response.content
            if self.acknowledge:
                content = content.replace("## 6. 训练计划", "## 6. 训练计划\n每天按你的15分钟练习时间安排。")
            if self.leak:
                content += "\n" + MEMORY_MARKER
            response = replace(response, content=content)
        return response


@pytest.mark.parametrize("leak,acknowledge,passed", [(False, True, True), (True, True, False), (False, False, False)])
def test_memory_checks_both_preference_and_injection(leak, acknowledge, passed):
    plan = prepare_observation(ROOT, scenario="memory")
    provider = Remembering(leak=leak, acknowledge=acknowledge)
    receipt = run_observation(ROOT, provider=provider, plan=plan)
    assert receipt.passed is passed
    assert receipt.memory_preference_acknowledged is acknowledge
    assert receipt.observation.injection_check_passed is (not leak)
    assert plan.manifest["memory"]["selected_count"] == 2
    assert "每天最多15分钟" in provider.requests[0].messages[-1].content
    assert MEMORY_MARKER in provider.requests[0].messages[-1].content
    assert MEMORY_MARKER not in receipt.model_dump_json()


def test_memory_is_not_added_to_other_cases_and_is_deterministic():
    suite = prepare_suite(ROOT, suite_id=SUITE)
    assert suite.sha256 == prepare_suite(ROOT, suite_id=SUITE).sha256
    assert [p.scenario for p in suite.plans] == ["economy", "overall", "survival", "memory"]
    for plan in suite.plans[:3]:
        assert plan.request.memory_context_binding is None
        assert "memory" not in plan.manifest
    assert suite.plans[-1].request.memory_context_binding.owner_id == "synthetic-coach249-owner"
    assert suite.manifest["max_calls"] == 36
    assert suite.manifest["max_total_tokens"] == 2598912


def test_suite_runs_four_cases_and_reserves_before_provider(isolated_root):
    suite = prepare_suite(isolated_root, suite_id=SUITE)
    made, events = [], []
    def factory():
        assert (isolated_root / "data/runs/coach_grounded_development_suites" / SUITE / "reservation.json").exists()
        plan = suite.plans[len(made)]
        assert (isolated_root / "data/runs/coach_grounded_development" / plan.run_id / "reservation.json").exists()
        made.append(True)
        return Remembering()
    result = execute_suite_once(isolated_root, suite=suite, provider_factory=factory, on_progress=events.append)
    assert result["passed"] and result["provider_calls"] == 12
    assert [r["status"] for r in result["cases"]] == ["passed"] * 4
    assert len([e for e in events if e["event"] == "call_completed"]) == 12
    with pytest.raises(FileExistsError):
        execute_suite_once(isolated_root, suite=suite, provider_factory=factory)
    assert len(made) == 4


def test_quality_failure_does_not_skip_remaining_cases(isolated_root):
    class Low(Remembering):
        def chat(self, request):
            response = super().chat(request)
            if request.response_contract:
                value = json.loads(response.content)
                value.update(score=84)
                return replace(response, content=json.dumps(value))
            return response
    providers = iter([Low(), Remembering(), Remembering(), Remembering()])
    result = execute_suite_once(isolated_root, suite=prepare_suite(isolated_root, suite_id=SUITE), provider_factory=lambda: next(providers))
    assert not result["passed"] and result["provider_calls"] == 12
    assert [r["status"] for r in result["cases"]] == ["failed", "passed", "passed", "passed"]
    assert result["stop_reason"] is None


@pytest.mark.parametrize("code", ["authentication_failed", "rate_limited", "timeout", "connection_failed", "service_unavailable"])
def test_common_provider_failure_stops_suite_without_claiming_model_quality(isolated_root, code):
    from app.providers.errors import ProviderResponseError
    class Broken(Remembering):
        def chat(self, request):
            raise ProviderResponseError(provider="zhipu", code=code)
    made = []
    result = execute_suite_once(isolated_root, suite=prepare_suite(isolated_root, suite_id=SUITE),
        provider_factory=lambda: made.append(True) or Broken())
    assert len(made) == 1 and result["provider_calls"] == 1
    assert result["stop_reason"] == code
    assert [r["status"] for r in result["cases"]] == ["failed", "skipped", "skipped", "skipped"]


def test_interruption_records_partial_suite_and_skipped_cases(isolated_root):
    class Interrupted(Remembering):
        def chat(self, request):
            if request.response_contract:
                raise KeyboardInterrupt("private-message")
            return super().chat(request)
    with pytest.raises(KeyboardInterrupt):
        execute_suite_once(isolated_root, suite=prepare_suite(isolated_root, suite_id=SUITE), provider_factory=Interrupted)
    text = (isolated_root / "data/runs/coach_grounded_development_suites" / SUITE / "receipt.json").read_text()
    result = json.loads(text)
    assert result["provider_calls"] == 3 and result["stop_reason"] == "interrupted"
    assert [r["status"] for r in result["cases"]] == ["interrupted", "skipped", "skipped", "skipped"]
    assert "private-message" not in text


def test_suite_plan_drift_refuses_before_reservation(isolated_root):
    suite = prepare_suite(isolated_root, suite_id=SUITE)
    suite.manifest["max_calls"] = 37
    with pytest.raises(ValueError, match="suite_plan_drift"):
        execute_suite_once(isolated_root, suite=suite, provider_factory=Remembering)
    assert not (isolated_root / "data/runs").exists()


def test_full_suite_worst_path_stays_within_36_calls(isolated_root):
    from scripts.check_glm53_report_contract_budget import _MeteredWorstPathProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    class Worst(_MeteredWorstPathProvider):
        thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
        sdk_max_retries = 0
        def chat(self, value):
            response = super().chat(value)
            return replace(response, usage=replace(response.usage, output_tokens=8192))
    result = execute_suite_once(isolated_root, suite=prepare_suite(isolated_root, suite_id=SUITE), provider_factory=Worst)
    assert result["provider_calls"] == 36 and not result["passed"]
    assert all(row["status"] == "failed" for row in result["cases"])
    assert result["observed_input_tokens"] + result["observed_output_tokens"] <= 2598912


def test_suite_cli_preview_is_offline(monkeypatch, isolated_root, capsys):
    from scripts import probe_coach_grounded_development as cli
    monkeypatch.setattr(cli, "ROOT", isolated_root)
    def forbidden(*args, **kwargs):
        raise AssertionError("no network or credentials in preview")
    monkeypatch.setattr(cli, "command", forbidden)
    monkeypatch.setattr(cli, "high_provider", forbidden)
    assert cli.main(["--suite", "--run-id", SUITE]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["network"] == 0 and value["max_calls"] == 36
    assert value["scenarios"] == ["economy", "overall", "survival", "memory"]
    assert not (isolated_root / "data/runs").exists()


@pytest.mark.parametrize("bad_ci", [False, True])
def test_suite_cli_same_sha_evidence_and_provider_cleanup(monkeypatch, isolated_root, bad_ci):
    from contextlib import contextmanager
    from scripts import probe_coach_grounded_development as cli
    monkeypatch.setattr(cli, "ROOT", isolated_root)
    sha = "a" * 40
    ci = {"headSha": "b" * 40 if bad_ci else sha, "status": "completed", "conclusion": "success",
        "url": "https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/249",
        "jobs": [{"name": n, "status": "completed", "conclusion": "success"}
                 for n in ("pytest", "postgres-migrations", "packaging-smoke")]}
    monkeypatch.setattr(cli, "command", lambda *a: "" if a[:2] == ("git", "status") else sha if a[:2] == ("git", "rev-parse") else json.dumps(ci))
    opened, closed = [], []
    @contextmanager
    def provider(_):
        assert (isolated_root / "data/runs/coach_grounded_development_suites" / SUITE / "reservation.json").exists()
        opened.append(True)
        try:
            yield Remembering()
        finally:
            closed.append(True)
    monkeypatch.setattr(cli, "high_provider", provider)
    suite = prepare_suite(isolated_root, suite_id=SUITE)
    assert cli.main(["--suite", "--run-id", SUITE, "--plan-sha256", suite.sha256, "--ci-run", "249", "--confirm-real-call"]) == int(bad_ci)
    assert len(opened) == len(closed) == (0 if bad_ci else 4)
    if bad_ci:
        assert not (isolated_root / "data/runs").exists()
    else:
        for plan in suite.plans:
            record = json.loads((isolated_root / "data/runs/coach_grounded_development" / plan.run_id / "receipt.json").read_text())
            assert record["real_evidence"]["implementation_sha"] == sha
            assert record["real_evidence"]["plan_sha256"] == plan.sha256


def test_memory_diagnostic_cannot_be_dropped_to_fake_a_pass():
    from app.evaluation.coach_grounded_development import DevelopmentReceipt, validate_receipt
    plan = prepare_observation(ROOT, scenario="memory")
    receipt = run_observation(ROOT, provider=Remembering(acknowledge=False), plan=plan)
    raw = receipt.model_dump(mode="json")
    raw.update(passed=True, failure_codes=[])
    with pytest.raises(ValueError, match="outcome_mismatch"):
        validate_receipt(DevelopmentReceipt.model_validate(raw), plan)
