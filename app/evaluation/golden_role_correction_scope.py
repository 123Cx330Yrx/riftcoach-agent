"""Versioned review responsibility on the existing coarse-source workflow.

All actionable fields and sources remain available. The editor receives the
complete accepted review; initial, fresh and bounded reassessment share one rule.
"""
from dataclasses import replace

from app.evaluation.golden_coarse_source_projection import project_request
from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_role_coarse import RoleCoarseReviewWorkflow

CONTRACT_ID = "golden-role-correction-scope-workflow-v1"
RULE = (
    "审查输出也必须遵守上述事实、范围与来源规则。suggested_correction只修复explanation已确认的实际问题及有来源支持的直接影响；"
    "不得另行扩展到未确认有问题的指标、对象、比较组或量词。修法里的说明和示例都逐项核对，不让正确示例掩盖错误的总指令；"
    "不能确认的替换断言不要当作确定修法。"
)


def review_policy(previous_raw=None):
    """One policy producer for runtime requests and manifest fingerprints."""
    from app.evaluation.golden_role_clarity import review_policy as base_policy
    from app.evaluation.golden_coarse_source_projection import ROW_ADDRESS, OLD_ROOT_POLICY, ROOT_POLICY
    from app.evaluation.golden_explicit_source_projection import NEW_ADDRESS
    return (base_policy(previous_raw).replace(NEW_ADDRESS, ROW_ADDRESS)
            .replace(OLD_ROOT_POLICY, ROOT_POLICY) + "\n" + RULE)


class RoleCorrectionScopeReviewWorkflow(RoleCoarseReviewWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        request = project_request(inputs, **kwargs)
        if kwargs.get("accepted") is not None:
            return request
        return budget_check(replace(request, messages=(
            replace(request.messages[0], content=review_policy(kwargs.get("previous_raw"))),
            *request.messages[1:])))

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = RoleCoarseReviewWorkflow.validate_review(
            raw, inputs, previous_raw=previous_raw)
        return payload, wire, dict(journal, experiment=CONTRACT_ID,
            validator_experiment=CONTRACT_ID,
            policy_sha256=digest(review_policy(previous_raw)))
