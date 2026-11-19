"""Role review: actionable findings plus nonblocking paragraph markers.

Markers preserve a place for optional clarity observations without asking the
reviewer to generate another factual report. They do not prove correctness or
weaken the source/issue contract. Historical note workflows remain unchanged.
"""
from dataclasses import replace

from pydantic import Field

from app.evaluation import golden_native_partitioned_tool_review as partitioned
from app.evaluation.golden_explicit_source_projection import VERSION
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_notes import RoleNoteReview, NEW_NOTE, review_policy as note_policy
from app.evaluation.golden_role_tool_delivery import DELIVERY_ID, RoleToolDeliveryReviewWorkflow

CONTRACT_ID = 'golden-role-review-clarity-markers-v1'
CLARITY_ID = 'role-review-clarity-markers-v1'
MARKER_POLICY = (
    '每项仅填写block，标记该段存在可选的可读性改善；每段最多一个标记，不生成解释、'
    '新数字、引用或替换正文。此标记不用于确认事实正确，也不能替代完整审查；'
    '真实事实错误、无依据外推、内部矛盾或完整上下文无法消解且影响结论的歧义必须进入issues，'
    '不能藏入advisories；不要把仅可选的措辞改善升级为issues。')


class ClarityMarker(partitioned.native.previous.Strict):
    block: int = Field(ge=1, le=64)


class RoleClarityReview(RoleNoteReview):
    advisories: list[ClarityMarker] = Field(max_length=64)


def review_policy(previous_raw=None):
    policy = note_policy(previous_raw)
    if policy.count(NEW_NOTE) != 1:
        raise ValueError('role_clarity_policy_contract_changed')
    return policy.replace(NEW_NOTE, MARKER_POLICY)


class RoleClarityReviewWorkflow(RoleToolDeliveryReviewWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        request = RoleToolDeliveryReviewWorkflow.make_request(inputs, **kwargs)
        if kwargs.get('accepted') is not None:
            return request  # Existing editor receives only actionable issues.
        return partitioned.native.budget_check(replace(request,
            tools=(replace(request.tools[0], input_schema=RoleClarityReview.model_json_schema()),),
            messages=(replace(request.messages[0], content=review_policy(kwargs.get('previous_raw'))),
                      *request.messages[1:]),
            metadata={**request.metadata, 'review_output': CLARITY_ID}))

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        value = partitioned.native.strict_json(raw)
        wire = RoleClarityReview.model_validate(value, strict=True)
        payload, _, base_journal = partitioned.business.validate(
            compact(wire.model_dump(mode='json', exclude={'advisories'})), inputs,
            previous_raw=previous_raw)
        markers, seen = [], set()
        for marker in wire.advisories:
            if marker.block > len(inputs.source.blocks):
                raise ValueError('native_advisory_block_unknown')
            if marker.block in seen:
                raise ValueError('native_advisory_block_duplicate')
            seen.add(marker.block)
            markers.append(dict(block=marker.block, quote=inputs.source.blocks[marker.block-1][1]))
        return payload, wire, dict(base_journal,
            experiment=CONTRACT_ID, validator_experiment=partitioned.business.EXPERIMENT_ID,
            validator_policy_sha256=base_journal['policy_sha256'],
            policy_sha256=digest(review_policy(previous_raw)), source_projection=VERSION,
            request_delivery=DELIVERY_ID,
            review_output=CLARITY_ID, raw=raw, raw_sha256=digest(raw),
            parsed_review=wire.model_dump(mode='json'), advisories=markers,
            raw_representation='tool_arguments_projection')
