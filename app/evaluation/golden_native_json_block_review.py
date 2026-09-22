"""Compact phase-specific review in JSON content, outside tool argument parsing.

The business contract is unchanged from ADR0106. This is a bounded channel
experiment; JSON mode is not a promise of correct semantics or valid schema.
"""
from dataclasses import replace

from app.evaluation import golden_native_buffered_block_review as previous
from app.evaluation import golden_native_business_policy as business
from app.evaluation import golden_native_tool_review as tool
from app.evaluation.golden_review_experiment import digest
from app.providers.errors import ProviderResponseError
from app.providers.structured import contract_for_model

native = previous.native
EXPERIMENT_ID = 'golden-native-json-block-review-v1'
LIVE_STATUS = 'offline_json_content_deadline'
LIVE_BLOCK_REASON = 'json_content_review_no_public_result_before_deadline'
STREAM_TOOL_ARGUMENTS = False


def require_live_qualification():
    if LIVE_STATUS != 'bounded_development_after_exact_ci':
        raise ValueError(LIVE_BLOCK_REASON)


def _policy(previous_raw=None):
    value = previous._policy(previous_raw)
    if value.count(tool.TOOL_DELIVERY) != 1:
        raise ValueError('json_review_delivery_policy_changed')
    return value.replace(tool.TOOL_DELIVERY, tool.TEXT_DELIVERY)


def request(inputs, *, previous_raw=None, diagnostics=None, accepted=None):
    base = previous.request(inputs, previous_raw=previous_raw, diagnostics=diagnostics, accepted=accepted)
    if accepted is not None:
        return base
    model = previous.IndependentReview if previous_raw is None else previous.previous.CompleteReview
    contract = contract_for_model(name=base.metadata['review_phase'], version='4.0.0', output_model=model)
    return native.budget_check(replace(base, tools=(), response_contract=contract,
        messages=(replace(base.messages[0], content=_policy(previous_raw)),
            replace(base.messages[1], content=native.schema_notation(contract.schema_dict()) + '\n'
                + base.messages[1].content), *base.messages[2:])))


def validate(raw, inputs, *, previous_raw=None):
    # Do not revive the historical prose-tail retry: it can change the business
    # verdict and erase disagreements. Duplicate JSON members also remain fatal.
    value, suffix = native.previous.provisional_review(raw)
    if suffix:
        if native.previous.security_terminal(value):
            raise ValueError('native_security_terminal')
        raise ProviderResponseError(provider='zhipu', code='native_review_non_json_suffix')
    payload, wire, journal = previous.validate(raw, inputs, previous_raw=previous_raw)
    journal.update(experiment=EXPERIMENT_ID, policy_sha256=digest(_policy(previous_raw)),
        raw_representation='response_content',
        previous_raw_representation='response_content' if previous_raw is not None else None,
        original_response_location='recorded_exchange_response')
    journal.pop('submission_tool', None)
    return payload, wire, journal


class NativeBusinessReviewWorkflow(business.NativeBusinessReviewWorkflow):
    make_request = staticmethod(request)
    validate_review = staticmethod(validate)
