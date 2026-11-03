"""Product development plumbing with scripted responses, never quality evidence."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import socket

import pytest

from app.evaluation.coach_grounded_development import (
    DevelopmentReceipt, execute_once, prepare_observation, run_observation,
    validate_receipt, verify_development_ci,
)
from tests.test_coach_contract_repair import RepairProvider

ROOT = Path(__file__).resolve().parents[1]
RUN = "coach-grounded-dev-test-01"
SHA = "a" * 40


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("development entry tests must remain offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def isolated_root(tmp_path):
    for folder in ("examples/runtime_profiles/flash_v2", "examples/runtime_profiles/flash_v2_repair", "data/rag_docs"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    (tmp_path / "examples/fixtures").mkdir()
    for name in ("player_summary_demo.json", "deterministic_report_demo.md"):
        shutil.copyfile(ROOT / "examples/fixtures" / name, tmp_path / "examples/fixtures" / name)
    return tmp_path


def prepare(root=ROOT, scenario="economy"):
    return prepare_observation(root, scenario=scenario, run_id=RUN)


@pytest.mark.parametrize("scenario", ["overall", "survival", "economy"])
def test_product_development_runs_actual_grounded_contract_and_safe_receipt(scenario):
    plan = prepare(scenario=scenario)
    stub = RepairProvider(problem="missing_citation")
    receipt = run_observation(ROOT, provider=stub, plan=plan)
    assert receipt.passed and receipt.provider_calls == 5
    assert receipt.scope == "development_not_admission"
    assert receipt.evidence_origin == "offline_fake" and not receipt.network_used
    assert not receipt.production_admitted and not receipt.candidate_registered
    assert receipt.observation.evaluation_score == 95
    assert receipt.diagnostics.evaluation_artifact_count == 2
    assert receipt.observation.citation_check_passed
    assert [row.phase for row in receipt.calls] == ["agent", "agent", "evaluation", "revision", "evaluation"]
    assert all(r.max_tokens == 8192 and 59 < r.timeout_s <= 60 for r in stub.requests)
    assert plan.manifest["budget"]["total_tokens"] == 649728
    assert plan.dataset.role.value == "development" and not plan.dataset.calibration_excluded
    encoded = receipt.model_dump_json()
    assert validate_receipt(DevelopmentReceipt.model_validate_json(encoded), plan) == receipt
    assert not any(body in encoded for body in ("两局", "[K1]", "较多", "controlled", "示例英雄"))
    assert "minimum_evaluation_score" not in stub.requests[0].messages[-1].content
    assert "请求5局" in stub.requests[0].messages[-1].content


@pytest.mark.parametrize("problem", ["pass_with_issues", "revision_without_issues"])
def test_evaluation_correction_is_retained_in_development_diagnostics(problem):
    receipt = run_observation(ROOT, provider=RepairProvider(problem=problem), plan=prepare())
    assert receipt.passed and receipt.provider_calls == 4
    assert [d.consistency_error for d in receipt.diagnostics.evaluation_responses] == [problem, None]


@pytest.mark.parametrize("mutation", ["context", "program", "fixture", "corpus"])
def test_changed_plan_is_rejected_before_any_provider_request(isolated_root, mutation):
    plan = prepare(isolated_root)
    if mutation == "context":
        plan.manifest["context_sha256"] = "0" * 64
    else:
        file = {"program": isolated_root / "examples/runtime_profiles/flash_v2_repair/prompt_programs/recent-form-review/manifest.json",
                "fixture": isolated_root / "examples/fixtures/deterministic_report_demo.md",
                "corpus": next((isolated_root / "data/rag_docs").glob("*.md"))}[mutation]
        file.write_text(file.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    stub = RepairProvider(problem="none")
    with pytest.raises(ValueError):
        run_observation(isolated_root, provider=stub, plan=plan)
    assert not stub.requests


def test_fixed_identity_is_reserved_before_provider_and_never_overwritten(isolated_root):
    plan = prepare(isolated_root)
    made = []
    def factory():
        assert (isolated_root / "data/runs/coach_grounded_development" / RUN / "reservation.json").is_file()
        made.append(True)
        return RepairProvider(problem="none")
    result = execute_once(isolated_root, plan=plan, provider_factory=factory)
    assert result.passed
    with pytest.raises(FileExistsError):
        execute_once(isolated_root, plan=plan, provider_factory=factory)
    assert len(made) == 1


def test_interruption_retains_safe_partial_diagnostics_and_removes_bodies(isolated_root, monkeypatch, tmp_path):
    import tempfile
    from app.evaluation import coach_grounded_development as module
    temporary = []
    original = tempfile.TemporaryDirectory
    def tracked(**kwargs):
        directory = original(**kwargs)
        temporary.append(Path(directory.name))
        return directory
    monkeypatch.setattr(module.tempfile, "TemporaryDirectory", tracked)
    class Interrupted(RepairProvider):
        def chat(self, value):
            if value.response_contract:
                raise KeyboardInterrupt("secret-do-not-record")
            return super().chat(value)
    with pytest.raises(KeyboardInterrupt):
        execute_once(isolated_root, plan=prepare(isolated_root), provider_factory=lambda: Interrupted(problem="none"))
    state = isolated_root / "data/runs/coach_grounded_development" / RUN
    failure = json.loads((state / "failure.json").read_text())
    assert failure["provider_calls"] == 3 and failure["phase"] == "runtime_execution"
    assert failure["calls"][-1]["error_code"] == "interrupted"
    assert len(list(state.glob("call_*.json"))) == 3
    assert "secret-do-not-record" not in (state / "failure.json").read_text()
    assert temporary and all(not p.exists() for p in temporary)


@pytest.mark.parametrize("mutation", ["sha", "status", "missing_job", "duplicate_job", "url"])
def test_development_ci_is_exact_and_cannot_borrow_other_evidence(mutation):
    plan = prepare()
    ci = {"headSha": SHA, "status": "completed", "conclusion": "success",
          "url": "https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/248",
          "jobs": [{"name": name, "status": "completed", "conclusion": "success"}
                   for name in ("pytest", "postgres-migrations", "packaging-smoke")]}
    assert verify_development_ci(plan, implementation_sha=SHA, ci=ci).plan_sha256 == plan.sha256
    if mutation == "sha": ci["headSha"] = "b" * 40
    if mutation == "status": ci["status"] = "in_progress"
    if mutation == "missing_job": ci["jobs"].pop()
    if mutation == "duplicate_job": ci["jobs"][-1] = ci["jobs"][0]
    if mutation == "url": ci["url"] = "https://github.com/other/repo/actions/runs/248"
    with pytest.raises(ValueError):
        verify_development_ci(plan, implementation_sha=SHA, ci=ci)


@pytest.mark.parametrize("failure,calls", [
    ("contradiction", 4), ("malformed", 4), ("missing_citation", 5), ("unknown_citation", 2),
    ("low_score", 3), ("injection", 3), ("missing_source", 1), ("timeout", 3),
])
def test_failed_product_run_keeps_cause_and_never_retries_indefinitely(failure, calls):
    from app.providers.errors import ProviderResponseError
    from tests.test_provider_domain_production import REVISION_REPORT
    class Failing(RepairProvider):
        def chat(self, value):
            if failure == "timeout" and value.response_contract:
                self.requests.append(value)
                raise ProviderResponseError(provider="zhipu", code="timeout")
            response = super().chat(value)
            if failure == "missing_source" and len(self.requests) == 1:
                return self._text(REVISION_REPORT)
            if value.response_contract:
                if failure == "malformed":
                    return replace(response, content="not json", finish_reason="length")
                payload = json.loads(response.content)
                if failure == "contradiction": payload.update(verdict="needs_revision", issues=[])
                if failure == "low_score": payload.update(score=84, verdict="pass", issues=[])
                if failure == "injection":
                    payload.update(score=99, verdict="pass", issues=[{
                        "severity": "high", "category": "prompt_injection", "quote": "private",
                        "evidence": "private", "explanation": "private", "suggested_correction": "private"}])
                return replace(response, content=json.dumps(payload))
            if response.content and failure in ("missing_citation", "unknown_citation"):
                return replace(response, content=response.content.replace("[K1]", "" if failure == "missing_citation" else "[K999]"))
            return response
    stub = Failing(problem="none")
    receipt = run_observation(ROOT, provider=stub, plan=prepare())
    assert not receipt.passed and receipt.failure_codes
    assert receipt.provider_calls == calls == len(stub.requests)
    assert receipt.observation.terminal_status == "rejected"
    if failure == "timeout":
        assert receipt.diagnostics.harness_failure_code == "timeout"
        assert receipt.calls[-1].error_code == "timeout" and not receipt.calls[-1].response_received
        assert receipt.observation.evaluation_score is None
    if failure == "malformed":
        assert receipt.calls[-1].finish_reason == "length"
        assert receipt.calls[-1].content_characters == len("not json")
        assert not receipt.diagnostics.evaluation_responses[-1].schema_valid
    if failure == "low_score":
        assert receipt.observation.evaluation_score == 84


@pytest.mark.parametrize("scenario", ["overall", "survival", "economy"])
def test_nine_call_worst_path_uses_real_product_budget_and_complete_diagnostics(scenario):
    from scripts.check_glm53_report_contract_budget import _MeteredWorstPathProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    class Worst(_MeteredWorstPathProvider):
        thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
        sdk_max_retries = 0
        def chat(self, value):
            response = super().chat(value)
            return replace(response, usage=replace(response.usage, output_tokens=8192))
    receipt = run_observation(ROOT, provider=Worst(), plan=prepare(scenario=scenario))
    assert not receipt.passed and receipt.provider_calls == 9
    assert receipt.observed_output_tokens == 9 * 8192
    assert receipt.observed_input_tokens + receipt.observed_output_tokens <= 649728
    assert len(receipt.diagnostics.evaluation_responses) == 4


@pytest.mark.parametrize("mutation", ["pass", "usage", "evaluation_ordinal", "raw_error"])
def test_receipt_tampering_is_rejected(mutation):
    plan = prepare()
    receipt = run_observation(ROOT, provider=RepairProvider(problem="none"), plan=plan)
    raw = receipt.model_dump(mode="json")
    if mutation == "pass": raw["observation"]["evaluation_score"] = 1
    if mutation == "usage": raw["observed_input_tokens"] += 1
    if mutation == "evaluation_ordinal": raw["diagnostics"]["evaluation_responses"][0]["call_ordinal"] = 1
    if mutation == "raw_error": raw["calls"][0]["error_code"] = "secret injected error text"
    with pytest.raises(ValueError):
        validate_receipt(DevelopmentReceipt.model_validate(raw), plan)


def test_observer_failure_keeps_successful_calls_without_claiming_quality(isolated_root, monkeypatch):
    from app.evaluation import coach_grounded_development as module
    def fail(*args, **kwargs):
        raise ValueError("raw report must not enter failure record")
    monkeypatch.setattr(module, "observe_product_result", fail)
    with pytest.raises(ValueError):
        execute_once(isolated_root, plan=prepare(isolated_root), provider_factory=lambda: RepairProvider(problem="none"))
    state = isolated_root / "data/runs/coach_grounded_development" / RUN
    raw = (state / "failure.json").read_text()
    record = json.loads(raw)
    assert record["phase"] == "observation_projection" and record["provider_calls"] == 3
    assert len(record["evaluation_responses"]) == 1
    assert "raw report" not in raw and not (state / "receipt.json").exists()


@pytest.mark.parametrize("identity", ["../coach246_economy", "coach246_economy", "coach-grounded-dev-../escape", "CON"])
def test_development_identity_cannot_address_old_runs_or_escape(identity):
    with pytest.raises(ValueError, match="development_identity_invalid"):
        prepare_observation(ROOT, run_id=identity)


def test_cli_default_does_not_read_credentials_network_git_or_reserve(monkeypatch, isolated_root, capsys):
    from scripts import probe_coach_grounded_development as cli
    monkeypatch.setattr(cli, "ROOT", isolated_root)
    def forbidden(*args, **kwargs):
        raise AssertionError("preflight must remain read-only and offline")
    monkeypatch.setattr(cli, "command", forbidden)
    monkeypatch.setattr(cli, "high_provider", forbidden)
    monkeypatch.setattr(cli, "execute_once", forbidden)
    assert cli.main([]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["scenario"] == "economy" and value["network"] == 0
    assert value["reasoning_effort"] == "high" and value["max_output_tokens"] == 8192
    assert not (isolated_root / "data/runs").exists()


@pytest.mark.parametrize("failure", ["identity", "dirty", "ci"])
def test_cli_real_preflight_refuses_drift_before_provider_factory(monkeypatch, isolated_root, failure):
    from scripts import probe_coach_grounded_development as cli
    monkeypatch.setattr(cli, "ROOT", isolated_root)
    plan = prepare(isolated_root)
    made = []
    monkeypatch.setattr(cli, "high_provider", lambda *args: made.append(True))
    def command(*args):
        if args[:2] == ("git", "status"): return " M app/runtime/runtime.py" if failure == "dirty" else ""
        if args[:2] == ("git", "rev-parse"): return SHA
        return json.dumps({"headSha": "b" * 40})
    monkeypatch.setattr(cli, "command", command)
    assert cli.main(["--confirm-real-call", "--run-id", RUN, "--ci-run", "248", "--plan-sha256",
                     "0" * 64 if failure == "identity" else plan.sha256]) == 1
    assert not made and not (isolated_root / "data/runs").exists()


def test_live_cli_wiring_uses_actual_high_serializer_with_fake_sdk_and_closes_client(monkeypatch, isolated_root, capsys):
    # Fake CI/credentials and an in-memory SDK exercise the real CLI branch;
    # these temporary receipts are NOT real-provider evidence.
    import dotenv
    import openai
    from scripts import probe_coach_grounded_development as cli
    from tests.test_provider_domain_production import FakeDeepSeekClient, fake_deepseek_response, fake_deepseek_tool_call, REVISION_REPORT
    monkeypatch.setattr(cli, "ROOT", isolated_root)
    plan = prepare(isolated_root)
    ci = {"headSha": SHA, "status": "completed", "conclusion": "success",
          "url": "https://github.com/123Cx330Yrx/riftcoach-agent/actions/runs/248",
          "jobs": [{"name": n, "status": "completed", "conclusion": "success"}
                   for n in ("pytest", "postgres-migrations", "packaging-smoke")]}
    monkeypatch.setattr(cli, "command", lambda *args: "" if args[:2] == ("git", "status") else SHA if args[:2] == ("git", "rev-parse") else json.dumps(ci))
    def values(_path):
        assert (isolated_root / "data/runs/coach_grounded_development" / RUN / "reservation.json").exists()
        return {"LLM_PROVIDER": "zhipu", "LLM_MODEL": "glm-5.3-flash", "LLM_BASE_URL": "https://open.bigmodel.cn/api/paas/v4/", "LLM_API_KEY": "fake-test-secret"}
    monkeypatch.setattr(dotenv, "dotenv_values", values)
    responses = [fake_deepseek_response(content=None, finish_reason="tool_calls", tool_calls=(fake_deepseek_tool_call(call_id="dev-sdk", query="补刀经济"),)),
                 fake_deepseek_response(content=REVISION_REPORT, finish_reason="stop"),
                 fake_deepseek_response(content=json.dumps({"score": 95, "verdict": "pass", "issues": [], "passed_checks": [], "summary": "offline"}), finish_reason="stop")]
    for r in responses:
        r.model = "glm-5.3-flash"
        r.choices[0].message.reasoning_content = "private-reasoning"
    class Client(FakeDeepSeekClient):
        max_retries = 0
        closed = False
        def __enter__(self): return self
        def __exit__(self, *args): self.closed = True
    client = Client(responses)
    def factory(**kwargs):
        assert kwargs["max_retries"] == 0 and kwargs["timeout"] == 60
        return client
    monkeypatch.setattr(openai, "OpenAI", factory)
    assert cli.main(["--confirm-real-call", "--run-id", RUN, "--ci-run", "248", "--plan-sha256", plan.sha256]) == 0
    assert client.closed
    assert len(client.chat.completions.calls) == 3
    assert all(c["extra_body"]["reasoning_effort"] == "high" and c["max_tokens"] == 8192 and 59 < c["timeout"] <= 60 for c in client.chat.completions.calls)
    state = isolated_root / "data/runs/coach_grounded_development" / RUN
    receipt = json.loads((state / "receipt.json").read_text())
    assert len(receipt["retrieval_attempts"]) == 2
    assert receipt["retrieval_attempts"][0]["topic"] == "economy"
    assert receipt["retrieval_attempts"][0]["result"]["returned_count"] == 0
    assert receipt["retrieval_attempts"][-1]["result"]["returned_count"] > 0
    assert len(list(state.glob("retrieval_*.json"))) == 2
    persisted = "".join(p.read_text() for p in state.glob("*.json")) + capsys.readouterr().out
    assert "fake-test-secret" not in persisted and "private-reasoning" not in persisted
