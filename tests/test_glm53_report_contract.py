import json
import socket
from dataclasses import replace

import pytest

from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, REPORT_POLICY
from app.evaluation.glm53_guided_candidate import GuidedCandidateExecutor
from app.evaluation.coach_report import REVISER_SYSTEM_PROMPT
from app.harness.store import FileRunStore
from app.rag.coaching_query import COACHING_QUERY_GUIDANCE_V1
from scripts.probe_glm53_development_retrieval import development_plan, observe
from tests.test_provider_domain_production import OneRevisionProvider, REVISION_REPORT, ROOT


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("report contract tests must not connect")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.mark.parametrize("scenario", ["recent_review", "survival_adjustment", "economy_adjustment"])
def test_same_contract_reaches_generation_revision_and_re_evaluation(tmp_path, scenario):
    provider = OneRevisionProvider(provider_name="zhipu", model_name="glm-5.3-flash")
    result = observe(provider, root=ROOT, runs_root=tmp_path,
                     retrieval_guidance=COACHING_QUERY_GUIDANCE_V1,
                     scenario=scenario, report_contract_id=REPORT_CONTRACT_ID)
    assert result["observation"]["terminal_status"] == "published"
    assert result["observation"]["evaluation_score"] == 95
    assert result["observation"]["revision_count"] == 1
    assert result["resources"]["calls_used"] == 5
    assert result["report_contract_id"] == REPORT_CONTRACT_ID
    assert len(result["report_contract_sha256"]) == 64
    initial_policy = json.loads(provider.requests[0].messages[0].content)
    assert any(REPORT_POLICY in section["content"] for section in initial_policy["sections"]
               if section["trust"] == "internal_policy")
    revision = next(request for request in provider.requests
                    if any(message.content == REVISER_SYSTEM_PROMPT for message in request.messages))
    assert REPORT_POLICY in revision.messages[-1].content
    assert "controlled" in revision.messages[-1].content  # Actual evaluator issues, not a replacement answer.
    assert "controlled" not in json.dumps(result)
    assert result["evaluation_history"]["complete"]
    assert not result["production_admitted"] and not result["candidate_registered"]


def test_new_contract_requires_new_bound_development_identity(tmp_path):
    old = development_plan(ROOT, guided=True)
    new = development_plan(ROOT, guided=True, report_contract_id=REPORT_CONTRACT_ID)
    assert new.artifact.plan_id != old.artifact.plan_id
    assert new.artifact.plan_version == "2.0.0"
    assert new.artifact.cases[0].case_id != old.artifact.cases[0].case_id
    assert new.artifact.cases[0].run_id != old.artifact.cases[0].run_id
    assert new.artifact.prompt_context_snapshot_id != old.artifact.prompt_context_snapshot_id
    assert new.artifact.prompt_context_snapshot_sha256 != old.artifact.prompt_context_snapshot_sha256
    with pytest.raises(ValueError, match="report contract development"):
        GuidedCandidateExecutor(project_root=ROOT, input_plan=old, runs_root=tmp_path,
                                report_contract_id=REPORT_CONTRACT_ID)
    with pytest.raises(ValueError, match="drifted"):
        GuidedCandidateExecutor(project_root=ROOT, input_plan=new, runs_root=tmp_path)
    with pytest.raises(ValueError, match="requires guided"):
        development_plan(ROOT, report_contract_id=REPORT_CONTRACT_ID)
    with pytest.raises(ValueError, match="unsupported report contract"):
        development_plan(ROOT, guided=True, report_contract_id="unapproved-contract")


def test_legacy_development_plan_still_matches_its_immutable_receipt():
    receipt = json.loads((ROOT / "data/evaluation/results/development/glm53_survival_diagnostic_rq241_01.json").read_text(encoding="utf-8"))
    plan = development_plan(ROOT, guided=True, scenario="survival_adjustment")
    assert plan.execution_plan.plan_sha256 == receipt["plan_sha256"]


def test_direct_executor_cannot_bypass_report_contract_admission(tmp_path):
    from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
    from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
    plan = development_plan(ROOT, guided=True, report_contract_id=REPORT_CONTRACT_ID)
    with pytest.raises(ValueError, match="explicit report contract"):
        ProductionDomainCaseExecutor(project_root=ROOT, input_plan=plan, runs_root=tmp_path)
    with pytest.raises(ValueError, match="exact guided candidate policy"):
        ProductionDomainCaseExecutor(project_root=ROOT, input_plan=plan, runs_root=tmp_path,
                                     report_contract_id=REPORT_CONTRACT_ID)
    old = development_plan(ROOT, guided=True)
    with pytest.raises(ValueError, match="report contract development"):
        ProductionDomainCaseExecutor(project_root=ROOT, input_plan=old, runs_root=tmp_path,
                                     request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
                                     quality_hardening=True, retrieval_hardening=True,
                                     retrieval_guidance=COACHING_QUERY_GUIDANCE_V1, max_revisions=1,
                                     report_contract_id=REPORT_CONTRACT_ID)


def test_contract_drift_is_rejected_before_provider_io(tmp_path, monkeypatch):
    plan = development_plan(ROOT, guided=True, report_contract_id=REPORT_CONTRACT_ID)
    executor = GuidedCandidateExecutor(project_root=ROOT, input_plan=plan, runs_root=tmp_path,
                                       report_contract_id=REPORT_CONTRACT_ID)
    monkeypatch.setattr("app.evaluation.glm53_report_contract.REPORT_POLICY", REPORT_POLICY + "\ndrift")
    provider = OneRevisionProvider(provider_name="zhipu", model_name="glm-5.3-flash")
    with pytest.raises(ValueError, match="drifted"):
        executor.execute(case_id=plan.artifact.cases[0].case_id, provider=provider)
    assert not provider.requests


def test_report_contract_cannot_relabel_a_consumed_fixture(tmp_path):
    plan = development_plan(ROOT, guided=True, report_contract_id=REPORT_CONTRACT_ID)
    tampered = replace(plan, player_summary_path=ROOT / "examples/fixtures/player_summary_glm53_flash_guided_v4.json")
    with pytest.raises(ValueError, match="anonymous demo fixtures"):
        GuidedCandidateExecutor(project_root=ROOT, input_plan=tampered, runs_root=tmp_path,
                                report_contract_id=REPORT_CONTRACT_ID)


def test_cli_rejects_report_contract_without_guidance_before_credentials(tmp_path):
    from scripts.probe_glm53_development_retrieval import main
    with pytest.raises(SystemExit) as failure:
        main(["--confirm-real-call", "--implementation-sha", "0" * 40,
              "--env-file", str(tmp_path / "does-not-exist.env"),
              "--output", str(tmp_path / "unused.json"), "--report-contract"])
    assert failure.value.code == 2
    assert not (tmp_path / "unused.json").exists()


@pytest.mark.parametrize("failure", ["initial_heading", "revision_heading", "revision_short", "revision_citation"])
def test_alignment_does_not_relax_structure_length_or_citation_gates(tmp_path, failure):
    class InvalidReport(OneRevisionProvider):
        def chat(self, request):
            is_revision = any(message.content == REVISER_SYSTEM_PROMPT for message in request.messages)
            if is_revision:
                self.requests.append(request)
                content = REVISION_REPORT
                if failure == "revision_heading":
                    content = content.replace("## 6. 训练计划", "## Other")
                if failure == "revision_citation":
                    content = content.replace("[K1]", "[K999]")
                return self._text(content)
            response = super().chat(request)
            if any(message.role.value == "tool" for message in request.messages):
                if failure == "initial_heading":
                    return self._text(REVISION_REPORT.replace("## 6. 训练计划", "## Other"))
                if failure == "revision_short":
                    return self._text(REVISION_REPORT + "\nprivate detail" * 100)
            return response

    provider = InvalidReport(provider_name="zhipu", model_name="glm-5.3-flash")
    result = observe(provider, root=ROOT, runs_root=tmp_path,
                     retrieval_guidance=COACHING_QUERY_GUIDANCE_V1, report_contract_id=REPORT_CONTRACT_ID)
    observation = result["observation"]
    assert observation["terminal_status"] == "rejected"
    assert observation["evaluation_score"] is None
    expected = "report_missing_headings"
    if failure == "revision_short":
        expected = "report_too_short"
    if failure == "revision_citation":
        expected = "unknown_report_citation"
    assert observation["safe_provider_error_code"] == expected
    assert result["resources"]["calls_used"] == (2 if failure == "initial_heading" else 4)
    plan = development_plan(ROOT, guided=True, report_contract_id=REPORT_CONTRACT_ID)
    manifest = FileRunStore(tmp_path, plan.artifact.cases[0].run_id).read_manifest()
    assert not any(row["kind"] == "final_report" for row in manifest.artifacts)
