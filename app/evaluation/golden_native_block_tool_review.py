"""Compact paragraph review experiment; structural coverage is not semantic proof.

Reuse partitioned findings, sources, tool transport, revision and shared budget.
Every paragraph receives one result, with empty arrays for a clear paragraph.
No repeated text, positive explanations, navigation labels or extra model calls.
"""
from dataclasses import replace
from typing import Literal

from pydantic import Field

from app.evaluation import golden_native_partitioned_tool_review as previous
from app.evaluation.golden_review_experiment import compact, digest

native = previous.native
EXPERIMENT_ID = 'golden-native-block-tool-review-v1'
LIVE_STATUS = 'bounded_development_after_exact_ci'
LIVE_BLOCK_REASON = ''


class Advisory(native.previous.Strict):
    source_ids: list[int] = Field(max_length=48)
    explanation: str = Field(min_length=1, max_length=700)
    suggested_correction: str = Field(min_length=1, max_length=700)


class BlockReview(native.previous.Strict):
    block: int = Field(ge=1, le=64)
    issues: list[native.previous.Problem] = Field(max_length=512)
    advisories: list[Advisory] = Field(max_length=512)


class CompleteReview(native.previous.UntitledSchema, native.previous.Strict):
    reviews: list[BlockReview] = Field(min_length=1, max_length=64)
    score: int = Field(ge=0, le=100)
    verdict: Literal['pass', 'needs_revision', 'fail']
    issue_resolutions: list[native.IssueResolution] = Field(max_length=512)


def require_live_qualification():
    if LIVE_STATUS != 'bounded_development_after_exact_ci':
        raise ValueError(LIVE_BLOCK_REASON)


def _policy(previous_raw=None):
    policy = previous._review_policy(previous_raw)
    replacements = {
        '五个字段为score、verdict、issues、issue_resolutions、advisories。':
            '四个顶层字段为reviews、score、verdict、issue_resolutions。'
            'reviews按原报告顺序恰好覆盖source_index.blocks全部段，每段一项block、issues、advisories。'
            '逐段核对该段所有子句及它们与全文、来源的关系，再提交该段结果；复合句不能只检查开头。'
            '无问题和建议的段两数组为空；不复述正确段正文、数字或解释，不输出其他覆盖摘要。',
        '每项须填写block、severity、category、source_ids、explanation、suggested_correction。':
            '每项须填写severity、category、source_ids、explanation、suggested_correction；段号由所属review给出。',
        '每项填写block、source_ids、explanation、suggested_correction，':
            '每项填写source_ids、explanation、suggested_correction，',
        'pass要求issues为空；': 'pass要求每段issues都为空；',
        'needs_revision表示issues非空；': 'needs_revision表示至少一段issues非空；',
    }
    for old, new in replacements.items():
        if policy.count(old) != 1:
            raise ValueError('block_review_policy_changed')
        policy = policy.replace(old, new)
    return policy + '\nissue_resolutions的final_issue按reviews顺序及段内issues顺序连续从1编号；advisories不参与问题编号。'


def _flatten(wire):
    return dict(score=wire.score, verdict=wire.verdict,
        issues=[dict(block=row.block, **issue.model_dump(mode='json'))
                for row in wire.reviews for issue in row.issues],
        advisories=[dict(block=row.block, **item.model_dump(mode='json'))
                    for row in wire.reviews for item in row.advisories],
        issue_resolutions=[r.model_dump(mode='json') for r in wire.issue_resolutions])


def request(inputs, *, previous_raw=None, diagnostics=None, accepted=None):
    if accepted is not None:
        if previous_raw is not None:
            raise ValueError('native_request_mode_conflict')
        mapped = previous.PartitionedReview.model_validate(_flatten(accepted), strict=True)
        return previous.request(inputs, accepted=mapped)
    base = previous.request(inputs, previous_raw=previous_raw, diagnostics=diagnostics)
    old_header = native.schema_notation(base.tools[0].input_schema) + '\n'
    if not base.messages[1].content.startswith(old_header):
        raise ValueError('block_review_schema_header_changed')
    schema = CompleteReview.model_json_schema()
    return native.budget_check(replace(base,
        tools=(replace(base.tools[0], input_schema=schema),),
        messages=(replace(base.messages[0], content=_policy(previous_raw)),
            replace(base.messages[1], content=native.schema_notation(schema) + '\n'
                + base.messages[1].content[len(old_header):]), *base.messages[2:])))


def validate(raw, inputs, *, previous_raw=None):
    wire = CompleteReview.model_validate(native.strict_json(raw), strict=True)
    if [r.block for r in wire.reviews] != list(range(1, len(inputs.source.blocks) + 1)):
        raise ValueError('block_review_inventory_invalid')
    # Existing validator checks sources, issue resolutions, score/verdict and
    # publication blockers. Mapping never invents or suppresses a finding.
    payload, _, journal = previous.validate(compact(_flatten(wire)), inputs, previous_raw=previous_raw)
    journal.update(experiment=EXPERIMENT_ID, raw=raw, raw_sha256=digest(raw),
        parsed_review=wire.model_dump(mode='json'), policy_sha256=digest(_policy(previous_raw)),
        structural_block_inventory_complete=True, semantic_coverage_proven=False)
    return payload, wire, journal


class NativeBusinessReviewWorkflow(previous.NativeBusinessReviewWorkflow):
    make_request = staticmethod(request)
    validate_review = staticmethod(validate)
