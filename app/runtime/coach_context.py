"""The opt-in Coach policy, compatible with the existing Memory wrapper."""
from app.agent.context import ContextBuilderV1
from .coach_contract import COACH_CONTRACT, require_coach_contract


class CoachContextBuilder(ContextBuilderV1):
    def __init__(self, *, coach_contract=COACH_CONTRACT):
        super().__init__()
        self.coach_contract = require_coach_contract(coach_contract)

    def build(self, execution, **kwargs):
        if "policy_addendum" in kwargs:
            raise ValueError("Coach policy cannot be supplied by the caller")
        return super().build(execution, policy_addendum=self.coach_contract.context_policy, **kwargs)
