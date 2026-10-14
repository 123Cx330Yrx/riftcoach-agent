"""Adopted role candidate workflow; unchanged full-context acceptance rules."""
from app.evaluation import golden_native_partitioned_tool_review as partitioned
from app.evaluation.golden_explicit_source_projection import VERSION, OLD_ADDRESS, NEW_ADDRESS, project_request
from app.evaluation.golden_review_experiment import digest


class RoleReviewWorkflow(partitioned.NativeBusinessReviewWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        return project_request(partitioned.request(inputs, **kwargs), inputs)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = partitioned.validate(raw, inputs, previous_raw=previous_raw)
        journal = dict(journal, validator_policy_sha256=journal["policy_sha256"],
            policy_sha256=digest(partitioned._review_policy(previous_raw).replace(OLD_ADDRESS, NEW_ADDRESS)),
            source_projection=VERSION)
        return payload, wire, journal
