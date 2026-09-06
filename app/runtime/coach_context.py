"""The opt-in Coach policy, compatible with the existing Memory wrapper."""
from app.agent.context import ContextBuilderV1
from app.evaluation.glm53_report_contract import REPORT_CONTRACT_ID, candidate_context_policy


class CoachContextBuilder(ContextBuilderV1):
    def build(self, execution, **kwargs):
        if "policy_addendum" in kwargs:
            raise ValueError("Coach policy cannot be supplied by the caller")
        return super().build(execution, policy_addendum=candidate_context_policy(REPORT_CONTRACT_ID), **kwargs)
