import json
from pathlib import Path
import socket

import pytest

from scripts.probe_glm53_development_retrieval import (
    DEVELOPMENT_SCENARIOS, QueryObserver, development_plan, main, observe,
)
from app.evaluation.glm53_flash_candidate_profile import GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor, _evaluation_observation
from tests.test_coaching_retrieval_development_chain import ScriptedCoach
from tests.test_provider_domain_production import ROOT
from tests.test_provider_domain_production import OneRevisionProvider, REVISION_REPORT
from app.evaluation.coach_report import REVISER_SYSTEM_PROMPT
from app.providers.models import ChatMessage, ChatRequest, MessageRole
from app.rag.coaching_query import COACHING_QUERY_GUIDANCE_V1
from app.skills.review_executor import SkillReviewExecutionError
from app.harness.store import FileRunStore
from app.providers.errors import ProviderResponseError, ProviderTimeoutError
from app.evaluation.glm53_guided_candidate import (
    GUIDED_DOMAIN_CASES, GuidedCandidateExecutor, validate_guided_domain_case_set,
)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline probe tests must not connect")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_observer_retains_safe_diagnostics_but_does_not_rewrite_model_query():
    provider = ScriptedCoach(query="private-query-5831")
    observer = QueryObserver(provider)
    response = observer.chat(ChatRequest(messages=(ChatMessage(MessageRole.USER, "development"),)))
    assert response.tool_calls[0].arguments["query"] == "private-query-5831"
    assert observer.queries[0]["topic"] == "unmapped"
    assert "private-query-5831" not in json.dumps(observer.queries)


def test_development_observation_uses_real_chain_and_no_heldout(tmp_path):
    report = observe(ScriptedCoach(), root=ROOT, runs_root=tmp_path)
    assert report["evidence_origin"] == "offline_fake"
    assert not report["network_used"]
    assert report["resources"]["calls_used"] == 3
    assert report["observation"]["terminal_status"] == "published"
    assert report["observation"]["evidence_source_ids"]
    assert report["queries"][0]["topic"] == "review"
    assert report["production_admitted"] is False
    assert report["retrieval_guidance_id"] is None
    assert report["retrieval_guidance_sha256"] is None
    assert development_plan(ROOT).artifact.dataset_id == "demo-development-not-heldout"
    for forbidden in ('"content"', '"reasoning"', '"api_key"', '"user_utterance"', '"arguments"'):
        assert forbidden not in json.dumps(report)


@pytest.mark.parametrize("failure", ["timeout", "invalid_chat_response", "invalid_tool_output", "invalid_structured_output"])
def test_evaluation_failure_survives_tool_adapter_manifest_and_development_receipt(tmp_path, failure):
    class FailingEvaluator(ScriptedCoach):
        def chat(self, request):
            if request.response_contract is not None:
                self.requests.append(request)
                if failure == "timeout":
                    raise ProviderTimeoutError(provider="zhipu", code=failure)
                if failure == "invalid_chat_response":
                    raise ProviderResponseError(provider="zhipu", code=failure)
                if failure == "invalid_tool_output":
                    # A valid tool-only response is not a valid evaluator text response.
                    return ScriptedCoach().chat(ChatRequest(messages=(ChatMessage(MessageRole.USER, "development"),)))
                return self._text("private_invalid_json")
            return super().chat(request)

    provider = FailingEvaluator()
    report = observe(provider, root=ROOT, runs_root=tmp_path, retrieval_guidance=COACHING_QUERY_GUIDANCE_V1)
    observation = report["observation"]
    assert observation["terminal_status"] == "rejected"
    assert observation["terminal_reason"] == "evaluation_failed"
    assert observation["safe_provider_error_code"] == failure
    assert observation["evaluation_score"] is None
    assert report["resources"]["calls_used"] == (4 if failure == "invalid_structured_output" else 3)
    assert "private_invalid_json" not in json.dumps(report)
    run_id = development_plan(ROOT, guided=True).artifact.cases[0].run_id
    manifest = FileRunStore(tmp_path, run_id).read_manifest()
    assert manifest.failure_code == failure
    assert not any(row["kind"] == "final_report" for row in manifest.artifacts)


def test_guidance_is_an_explicit_candidate_context_addendum(tmp_path):
    with pytest.raises(ValueError, match="requires retrieval hardening"):
        ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=development_plan(ROOT),
            runs_root=tmp_path,
            request_policy=GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY,
            quality_hardening=True,
            retrieval_guidance=COACHING_QUERY_GUIDANCE_V1,
        )
    provider = ScriptedCoach()
    report = observe(
        provider, root=ROOT, runs_root=tmp_path,
        retrieval_guidance=COACHING_QUERY_GUIDANCE_V1,
    )
    assert report["observation"]["terminal_status"] == "published"
    assert report["retrieval_guidance_id"] == "coaching-query-guidance-v1"
    assert report["retrieval_guidance_sha256"]
    system_text = "\n".join(message.content for message in provider.requests[0].messages if message.role.value == "system")
    assert COACHING_QUERY_GUIDANCE_V1 in system_text


@pytest.mark.parametrize("failure", ["report_missing_headings", "report_too_short", "unknown_report_citation"])
def test_revision_failure_keeps_prior_evaluation_without_claiming_final_score(tmp_path, failure):
    class InvalidRevision(OneRevisionProvider):
        def chat(self, request):
            if any(message.content == REVISER_SYSTEM_PROMPT for message in request.messages):
                self.requests.append(request)
                report = REVISION_REPORT
                if failure == "report_missing_headings":
                    report = report.replace("## 6. 训练计划", "## private_heading")
                elif failure == "unknown_report_citation":
                    report = report.replace("[K1]", "[K999999]")
                return self._text(report)
            response = super().chat(request)
            if failure == "report_too_short" and any(message.role.value == "tool" for message in request.messages):
                return self._text(REVISION_REPORT + "\nprivate_original_details" * 50)
            return response

    provider = InvalidRevision(provider_name="zhipu", model_name="glm-5.3-flash")
    report = observe(provider, root=ROOT, runs_root=tmp_path, retrieval_guidance=COACHING_QUERY_GUIDANCE_V1)
    result = report["observation"]
    assert result["terminal_status"] == "rejected"
    assert result["terminal_reason"] == "revision_failed"
    assert result["safe_provider_error_code"] == failure
    assert result["revision_count"] == 1
    assert result["evaluation_score"] is None
    assert result["evaluation_validated"] is False
    history = report["evaluation_history"]
    assert history["complete"] is False
    assert [row["score"] for row in history["attempts"]] == [70]
    assert history["attempts"][0]["issue_category_counts"] == [{"name": "fact_error", "count": 1}]
    assert report["resources"]["calls_used"] == 4
    assert not any(secret in json.dumps(report) for secret in ("private_heading", "private_original_details", "K999999", "controlled"))
    manifest = FileRunStore(tmp_path, development_plan(ROOT, guided=True).artifact.cases[0].run_id).read_manifest()
    assert manifest.failure_code == failure
    assert not any(row["kind"] == "final_report" for row in manifest.artifacts)


def test_unknown_revision_exception_does_not_leak_code_or_text(tmp_path, monkeypatch):
    def fail(*_args, **_kwargs):
        error = ValueError("private revision text")
        error.code = "report_missing_headings"
        raise error
    monkeypatch.setattr("app.harness.adapters.ChatCoachReviser.revise", fail)
    provider = OneRevisionProvider(provider_name="zhipu", model_name="glm-5.3-flash")
    report = observe(provider, root=ROOT, runs_root=tmp_path, retrieval_guidance=COACHING_QUERY_GUIDANCE_V1)
    assert report["observation"]["terminal_reason"] == "revision_failed"
    assert report["observation"]["safe_provider_error_code"] is None
    assert report["evaluation_history"]["attempts"][0]["score"] == 70
    assert "private revision text" not in json.dumps(report)


@pytest.mark.parametrize("second_evaluation_fails", [False, True])
def test_development_history_separates_prior_from_final_evaluation(tmp_path, second_evaluation_fails):
    class EvaluatedRevision(OneRevisionProvider):
        def chat(self, request):
            if second_evaluation_fails and request.response_contract is not None and self.evaluation_attempts == 1:
                self.requests.append(request)
                raise ProviderTimeoutError(provider="zhipu", code="timeout")
            return super().chat(request)
    report = observe(EvaluatedRevision(provider_name="zhipu", model_name="glm-5.3-flash"),
                     root=ROOT, runs_root=tmp_path, retrieval_guidance=COACHING_QUERY_GUIDANCE_V1)
    history = report["evaluation_history"]
    assert history["complete"] is not second_evaluation_fails
    assert [row["score"] for row in history["attempts"]] == ([70] if second_evaluation_fails else [70, 95])
    assert report["observation"]["evaluation_score"] == (None if second_evaluation_fails else 95)
    assert report["observation"]["terminal_status"] == ("rejected" if second_evaluation_fails else "published")
    assert report["resources"]["calls_used"] == 5


@pytest.mark.parametrize("tamper", ["content", "path", "producer", "run_id", "duplicate"])
def test_partial_development_history_rejects_corrupt_artifacts(tmp_path, monkeypatch, tamper):
    def fail(*_args, **_kwargs):
        raise ValueError("private revision error")
    monkeypatch.setattr("app.harness.adapters.ChatCoachReviser.revise", fail)
    observe(OneRevisionProvider(provider_name="zhipu", model_name="glm-5.3-flash"),
            root=ROOT, runs_root=tmp_path, retrieval_guidance=COACHING_QUERY_GUIDANCE_V1)
    run_id = development_plan(ROOT, guided=True).artifact.cases[0].run_id
    store = FileRunStore(tmp_path, run_id)
    manifest = store.read_manifest()
    # The original formal observation contract remains complete-only.
    assert not _evaluation_observation(manifest, store)[0].attempts
    record = next(row for row in manifest.artifacts if row["kind"] == "evaluation_result")
    if tamper == "content":
        (tmp_path / run_id / record["path"]).write_text("private corrupt artifact", encoding="utf-8")
    elif tamper == "duplicate":
        manifest.artifacts.append(dict(record))
    else:
        record[tamper] = "private_invalid_identity"
    history, payload = _evaluation_observation(manifest, store, allow_incomplete_history=True)
    assert history.attempts == ()
    assert payload is None


def test_guided_executor_rebinds_exact_candidate_policy_and_context(tmp_path):
    plan = development_plan(ROOT, guided=True)
    executor = GuidedCandidateExecutor(
        project_root=ROOT, input_plan=plan, runs_root=tmp_path,
    )
    assert executor.guidance_id == "coaching-query-guidance-v1"
    assert len(executor.guidance_sha256) == 64
    assert executor.input_plan.artifact.request_policy_id == GLM53_FLASH_LOW_CANDIDATE_REQUEST_POLICY.policy_id


def test_guided_case_identity_rejects_all_historical_names():
    for old in ("rq227", "rq230", "rq235", "rq237"):
        mutated = list(GUIDED_DOMAIN_CASES)
        mutated[0] = mutated[0].model_copy(update={"case_id": f"guided_domain_{old}"})
        with pytest.raises(ValueError, match="canonical|historical"):
            validate_guided_domain_case_set(tuple(mutated))


@pytest.mark.parametrize("scenario", tuple(DEVELOPMENT_SCENARIOS))
def test_guided_candidate_entry_supports_representative_coaching_scenarios(tmp_path, scenario):
    report = observe(
        ScriptedCoach(), root=ROOT, runs_root=tmp_path / scenario,
        retrieval_guidance=COACHING_QUERY_GUIDANCE_V1, scenario=scenario,
    )
    assert report["observation"]["terminal_status"] == "published"
    assert report["observation"]["evidence_source_ids"]
    assert report["plan_sha256"]


def test_fresh_guided_domain_case_set_is_canonical_and_rejects_reused_identity():
    validate_guided_domain_case_set()
    assert len(GUIDED_DOMAIN_CASES) == 4
    with pytest.raises(ValueError, match="canonical"):
        validate_guided_domain_case_set(GUIDED_DOMAIN_CASES[1:] + GUIDED_DOMAIN_CASES[:1])


def test_terminal_projection_failure_retains_safe_diagnostics(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise SkillReviewExecutionError("private model response must not leak")
    monkeypatch.setattr(ProductionDomainCaseExecutor, "execute", broken)
    report = observe(ScriptedCoach(), root=ROOT, runs_root=tmp_path)
    assert report["execution_error"] == "terminal_output_validation_failed"
    assert report["observation"] is None
    assert report["resources"]["calls_used"] == 0
    assert "private model response" not in json.dumps(report)


def test_real_flag_required_before_environment_and_output(tmp_path):
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(SystemExit):
        main(["--implementation-sha", "a" * 40, "--env-file", str(tmp_path / "absent.env"),
              "--output", str(output)])
    assert not output.exists()


def test_persisted_development_observation_has_no_invented_query_or_admission():
    path = ROOT / "data/evaluation/results/development/glm53_autonomous_retrieval_dev_01.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["scope"] == "development_not_admission"
    assert report["resources"]["calls_used"] == 2
    assert len(report["queries"]) == 2
    assert report["observation"]["evidence_source_ids"] == []
    assert report["observation"]["terminal_reason"] == "evidence_required"
    assert not report["production_admitted"]
    for query in report["queries"]:
        assert set(query) == {"shape", "topic", "recognized_topics", "character_count", "term_count", "filter_names"}
    assert report["probe_sha256"]
