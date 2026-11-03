"""Real RQ-249 failure shape: four tool calls before any retrieval execution."""
from dataclasses import replace

import pytest

from app.evaluation.coach_grounded_development import prepare_observation, prepare_suite, execute_suite_once, run_observation
from tests.test_coach_grounded_suite import Remembering
from tests.test_coach_grounded_development import ROOT, no_network, isolated_root


class FourSearches(Remembering):
    def chat(self, request):
        response = super().chat(request)
        if response.tool_calls:
            original = response.tool_calls[0]
            return replace(response, tool_calls=tuple(replace(original, id=f"batch-{i}",
                arguments={"query": query, "top_k": 2})
                for i, query in enumerate(("补刀经济", "早期死亡", "近期复盘", "训练计划"))))
        return response


def test_original_three_tool_cap_reproduces_real_failure_without_rewriting_it():
    receipt = run_observation(ROOT, provider=FourSearches(), plan=prepare_observation(ROOT))
    assert not receipt.passed and receipt.provider_calls == 1
    assert receipt.observation.agent_stop_reason == "max_tool_calls"
    assert receipt.calls[0].tool_call_count == 4 and not receipt.retrieval_attempts


@pytest.mark.parametrize("scenario", ["economy", "overall", "survival", "memory"])
def test_versioned_budget_accepts_four_local_searches_through_actual_runtime(scenario):
    plan = prepare_observation(ROOT, scenario=scenario, tool_batch=True)
    receipt = run_observation(ROOT, provider=FourSearches(), plan=plan)
    assert plan.request.policy.max_tool_calls == 8
    assert plan.request.policy.coach_contract.version == "1.2.0"
    assert receipt.passed and receipt.provider_calls == 3
    assert receipt.calls[0].tool_call_count == 4
    assert receipt.observation.successful_tool_names == ("knowledge.search",)
    assert len(receipt.observation.evidence_source_ids) >= 1
    assert receipt.observation.citation_check_passed


@pytest.mark.parametrize("count,passed", [(8, True), (9, False)])
def test_eight_tools_are_bounded_and_ninth_is_rejected_before_execution(count, passed):
    class Batch(FourSearches):
        def chat(self, request):
            response = super().chat(request)
            if response.tool_calls:
                return replace(response, tool_calls=tuple(replace(response.tool_calls[i % 4], id=f"bounded-{i}",
                    arguments={**response.tool_calls[i % 4].arguments, "top_k": i // 4 + 1}) for i in range(count)))
            return response
    receipt = run_observation(ROOT, provider=Batch(), plan=prepare_observation(ROOT, tool_batch=True))
    assert receipt.passed is passed
    if not passed:
        assert receipt.provider_calls == 1 and not receipt.retrieval_attempts
        assert receipt.observation.agent_stop_reason == "max_tool_calls"


def test_old_contracts_and_runtime_assets_keep_their_frozen_identity():
    from app.runtime.coach_contract import COACH_CONTRACT, GROUNDED_COACH_CONTRACT, BATCH_COACH_CONTRACT
    assert GROUNDED_COACH_CONTRACT.snapshot().sha256 == "48bf65c41a30d60a0d97f9b10a9fd2c03a1f9841150b71ef30b2fb819c831161"
    assert COACH_CONTRACT.snapshot().sha256 == "968c8dc8e2d745ed82bb4cdc1486bde0388d6782603bd833abdba067701e35d1"
    assert prepare_observation(ROOT).request.policy.max_tool_calls == 3
    assert BATCH_COACH_CONTRACT.descriptor()["total_tokens"] == 649728
    assert BATCH_COACH_CONTRACT.descriptor()["max_calls"] == 9


def test_versioned_suite_does_not_reuse_old_plan_and_runs_all_four(isolated_root):
    import shutil
    shutil.copytree(ROOT / "examples/runtime_profiles/flash_v2_batch", isolated_root / "examples/runtime_profiles/flash_v2_batch")
    old = prepare_suite(isolated_root, suite_id="coach-grounded-suite-batch-test")
    new = prepare_suite(isolated_root, suite_id=old.suite_id, tool_batch=True)
    assert old.sha256 != new.sha256
    result = execute_suite_once(isolated_root, suite=new, provider_factory=FourSearches)
    assert result["passed"] and result["provider_calls"] == 12
    assert all(r["status"] == "passed" for r in result["cases"])


@pytest.mark.parametrize("scenario", ["economy", "overall", "survival", "memory"])
def test_versioned_contract_retains_nine_call_resource_ceiling(scenario):
    from scripts.check_glm53_report_contract_budget import _MeteredWorstPathProvider
    from app.providers.zhipu_profiles import ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE
    class Worst(_MeteredWorstPathProvider):
        thinking_profile_id = ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE.profile_id
        sdk_max_retries = 0
        def chat(self, request):
            response = super().chat(request)
            return replace(response, usage=replace(response.usage, output_tokens=8192))
    receipt = run_observation(ROOT, provider=Worst(), plan=prepare_observation(ROOT, scenario=scenario, tool_batch=True))
    assert receipt.provider_calls == 9 and not receipt.passed
    assert receipt.observed_input_tokens + receipt.observed_output_tokens <= 649728
