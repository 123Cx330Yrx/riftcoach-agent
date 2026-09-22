"""Tool submission experiment with an explicit non-blocking advisory channel.

The prior tool experiment proved that transport framing was valid but did not
stop the model from turning a context-resolvable wording suggestion into a
blocking issue. This candidate changes the result contract so that only
report-changing findings enter ``issues``; clarity suggestions are preserved in
``advisories`` and cannot trigger revision. It is development-only.
"""
from dataclasses import replace
from typing import Literal

from pydantic import Field

from app.evaluation import golden_native_business_policy as business
from app.evaluation import golden_native_issues_review as native
from app.evaluation import golden_native_tool_review as tool
from app.evaluation.golden_review_experiment import compact, digest

EXPERIMENT_ID = 'golden-native-partitioned-tool-review-v1'
LIVE_STATUS = 'bounded_development_after_exact_ci'
LIVE_BLOCK_REASON = ''


class Advisory(native.previous.Strict):
    block: int = Field(ge=1, le=64)
    source_ids: list[int] = Field(max_length=48)
    explanation: str = Field(min_length=1, max_length=700)
    suggested_correction: str = Field(min_length=1, max_length=700)


class PartitionedReview(native.NativeIssuesReview):
    advisories: list[Advisory] = Field(max_length=512)


def require_live_qualification():
    if LIVE_STATUS != 'bounded_development_after_exact_ci':
        raise ValueError(LIVE_BLOCK_REASON)


def _partition_policy(policy):
    policy = policy.replace(
        '只输出给定schema的一个JSON对象，不加前后文字。四个字段为score、verdict、issues、issue_resolutions。',
        '只调用工具提交一个完整结果，不输出其他文字。五个字段为score、verdict、issues、issue_resolutions、advisories。')
    # tool.request has already replaced the delivery sentence. Keep this
    # fallback explicit so a policy assembled through that seam cannot retain a
    # contradictory four-field declaration.
    policy = policy.replace(
        '四个字段为score、verdict、issues、issue_resolutions。',
        '五个字段为score、verdict、issues、issue_resolutions、advisories。')
    policy = policy.replace(
        'issues仅列实际问题，同段不同问题可分别列；每项须填写block、severity、category、source_ids、explanation、suggested_correction。',
        'issues仅列需要修改报告的真实问题（事实冲突、无依据外推、内部矛盾或完整上下文无法消解且影响结论的歧义）；'
        '每项须填写block、severity、category、source_ids、explanation、suggested_correction。'
        'advisories仅列完整上下文已足够确定、事实正确而只是可读性或限定表达可改善的建议；'
        '每项填写block、source_ids、explanation、suggested_correction，不得把事实错误或无法消解的歧义放入advisories。')
    policy = policy.replace(
        'pass要求无issues；needs_revision表示有可修问题；fail用于终止情况。',
        'pass要求issues为空；advisories不触发修订。needs_revision表示issues非空；fail用于终止情况。')
    return policy


def request(inputs, *, previous_raw=None, diagnostics=None, accepted=None):
    if accepted is not None:
        # Advisories remain in the audit journal but are deliberately excluded
        # from the editor's accepted-review input. Revision acts only on report
        # changing findings and cannot silently turn clarity advice into a fix.
        if isinstance(accepted, PartitionedReview):
            accepted = native.NativeIssuesReview.model_validate(
                accepted.model_dump(exclude={'advisories'}), strict=True)
        return business.request(inputs, previous_raw=previous_raw, diagnostics=diagnostics, accepted=accepted)
    base = tool.request(inputs, previous_raw=previous_raw, diagnostics=diagnostics)
    # Rebuild only the submitted tool schema and the policy's result partition.
    schema = PartitionedReview.model_json_schema()
    old_schema = base.tools[0].input_schema
    policy = _partition_policy(base.messages[0].content)
    new_header = native.schema_notation(schema) + '\n'
    # The v1 tool candidate has already removed its old schema notation before
    # sending; prepend the partitioned notation at the same seam.
    message = new_header + base.messages[1].content
    return native.budget_check(replace(base,
        tools=(replace(base.tools[0], input_schema=schema),),
        messages=(replace(base.messages[0], content=policy), replace(base.messages[1], content=message), *base.messages[2:])))


def validate(raw, inputs, *, previous_raw=None):
    value = native.strict_json(raw)
    wire = PartitionedReview.model_validate(value, strict=True)
    base = wire.model_dump(mode='json')
    advisories = base.pop('advisories')
    # Keep the established issue/resolution/source validator authoritative.
    payload, base_wire, journal = business.validate(compact(base), inputs, previous_raw=previous_raw)
    selected = []
    for number, advisory in enumerate(wire.advisories, 1):
        if advisory.block > len(inputs.source.blocks):
            raise ValueError('native_advisory_block_unknown')
        refs = native.resolve_refs(inputs, advisory.source_ids, computed_layout='statistic_series')
        selected.append(dict(advisory=number, block=advisory.block, selected_sources=refs,
                             quote=inputs.source.blocks[advisory.block - 1][1],
                             **advisory.model_dump(exclude={'block', 'source_ids'})))
    journal = dict(journal, experiment=EXPERIMENT_ID,
        validator_experiment=business.EXPERIMENT_ID,
        raw=raw, raw_sha256=digest(raw), parsed_review=wire.model_dump(mode='json'),
        advisories=selected, raw_representation='tool_arguments_projection',
        policy_sha256=digest(_partition_policy(business.INITIAL_POLICY if previous_raw is None else business.REASSESSMENT_POLICY)))
    return payload, wire, journal


class NativeBusinessReviewWorkflow(tool.NativeBusinessReviewWorkflow):
    make_request = staticmethod(request)
    validate_review = staticmethod(validate)
