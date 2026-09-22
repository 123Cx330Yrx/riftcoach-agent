"""Phase-specific review submission using buffered tool arguments (ADR0106).

Independent reviews have no prior findings to resolve. Reassessment retains
the full mandatory mapping contract. Historical requests remain reproducible.
"""
from dataclasses import replace
from typing import Literal

from pydantic import Field

from app.evaluation import golden_native_block_tool_review as previous
from app.evaluation.golden_review_experiment import compact, digest

native = previous.native
EXPERIMENT_ID = 'golden-native-buffered-block-review-v1'
LIVE_STATUS = 'bounded_development_after_exact_ci'
LIVE_BLOCK_REASON = ''
STREAM_TOOL_ARGUMENTS = False


class IndependentReview(native.previous.UntitledSchema, native.previous.Strict):
    reviews: list[previous.BlockReview] = Field(min_length=1, max_length=64)
    score: int = Field(ge=0, le=100)
    verdict: Literal['pass', 'needs_revision', 'fail']


def require_live_qualification():
    if LIVE_STATUS != 'bounded_development_after_exact_ci':
        raise ValueError(LIVE_BLOCK_REASON)


def _policy(previous_raw=None):
    policy = previous._policy(previous_raw)
    if previous_raw is not None:
        return policy
    replacements = {
        '四个顶层字段为reviews、score、verdict、issue_resolutions。':
            '三个顶层字段为reviews、score、verdict。',
        '\n这是独立审查，未提供上一轮评估，issue_resolutions必须为空数组。':
            '\n这是独立审查，未提供上一轮评估。',
        '\nissue_resolutions的final_issue按reviews顺序及段内issues顺序连续从1编号；advisories不参与问题编号。': '',
    }
    for old, new in replacements.items():
        if policy.count(old) != 1:
            raise ValueError('buffered_review_policy_changed')
        policy = policy.replace(old, new)
    return policy


def _internal(wire):
    if isinstance(wire, IndependentReview):
        # A declared adapter between two contracts, not repair of a missing
        # model field. Strict wire validation has already rejected extra fields.
        return previous.CompleteReview.model_validate(
            dict(wire.model_dump(mode='json'), issue_resolutions=[]), strict=True)
    return wire


def request(inputs, *, previous_raw=None, diagnostics=None, accepted=None):
    if accepted is not None:
        return previous.request(inputs, previous_raw=previous_raw,
            diagnostics=diagnostics, accepted=_internal(accepted))
    base = previous.request(inputs, previous_raw=previous_raw, diagnostics=diagnostics)
    header = native.schema_notation(base.tools[0].input_schema) + '\n'
    if not base.messages[1].content.startswith(header):
        raise ValueError('buffered_review_schema_header_changed')
    schema = (IndependentReview if previous_raw is None else previous.CompleteReview).model_json_schema()
    return native.budget_check(replace(base,
        tools=(replace(base.tools[0], input_schema=schema),),
        messages=(replace(base.messages[0], content=_policy(previous_raw)),
            replace(base.messages[1], content=base.messages[1].content[len(header):]),
            *base.messages[2:])))


def validate(raw, inputs, *, previous_raw=None):
    schema = IndependentReview if previous_raw is None else previous.CompleteReview
    wire = schema.model_validate(native.strict_json(raw), strict=True)
    internal = _internal(wire)
    payload, _, journal = previous.validate(compact(internal.model_dump(mode='json')),
        inputs, previous_raw=previous_raw)
    journal.update(experiment=EXPERIMENT_ID, raw=raw, raw_sha256=digest(raw),
        parsed_review=wire.model_dump(mode='json'), policy_sha256=digest(_policy(previous_raw)),
        submission_phase='independent' if previous_raw is None else 'reassessment',
        validator_projection={'issue_resolutions': [], 'reason': 'no_previous_review_in_independent_contract'}
            if previous_raw is None else None)
    return payload, wire, journal


class NativeBusinessReviewWorkflow(previous.NativeBusinessReviewWorkflow):
    make_request = staticmethod(request)
    validate_review = staticmethod(validate)
