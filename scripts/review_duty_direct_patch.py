"""Offline proposal: reviewers author exact patches; no paraphrasing editor.

Pure request/preview functions only. A preview is not a Host decision, provider
receipt or publishable report. No transport, credentials, run or registration.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import re
import json

from pydantic import Field

from app.evaluation.coach_report import validate_revised_report
from app.evaluation.golden_inference_coverage import report_blocks
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_native_issues_review import strict_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReview
from app.evaluation.golden_semantic_review import reject_revision_policy_echo
from app.evaluation.source_patch_editor import EditAssembly, _block_spans, _section_order, report_inputs
from app.harness.runtime import ReviewHarness
from app.harness.steps import KnowledgeCitation, KnowledgeEvidence
from scripts.report_block_keyed_editor import Replacement
from scripts import review_duty_composition as duty

VERSION = 'offline-reviewer-authored-patches-v1'
MARKER = 'reviewer_authored_patches'
PATCH_POLICY = (
    '\n本次初审同时提出可直接应用的必要修订，不再由另一个编辑模型转述修法。'
    '完整保留issues的解释、来源与suggested_correction；repairs另给逐字补丁。'
    '每组issue_ids列本次issues的一基序号，每个实际问题恰好属于一组；同段多个问题可合为一组。'
    'edits按block_N归组，N为原报告HOST_BLOCK一基段号，不是章节号；'
    '每项before为该段内唯一连续原文，after为最终替换文本，reason说明必要修改。'
    '可在一组中修正文和受直接影响的摘要；所有补丁针对同一原稿且不得重叠。'
    '只修真实问题与直接影响，完整核对来源限定，保留正确内容、身份和任务；不得把修订指令写入报告。'
    'needs_revision须覆盖全部issues；pass或fail时repairs为空。'
    '无法给出可靠修法时用fail终止，不能给needs_revision省略补丁或假称pass。'
    '补丁将原样组装并对完整新稿重新审查；补丁合法不表示通过或发布。'
)


class Repair(Strict):
    issue_ids: list[int] = Field(min_length=1, max_length=512)
    edits: dict[str, list[Replacement]] = Field(min_length=1)


class PatchReview(RoleClarityReview):
    repairs: list[Repair] = Field(max_length=512)


def review_request(inputs, name, stage='initial'):
    base = duty.review_request(inputs, name, stage)
    metadata = {**base.metadata, MARKER: VERSION}
    if stage == 'fresh':
        return duty.budget_check(replace(base, metadata=metadata))
    if not 0 < len(inputs.source.blocks) <= 64:
        raise ValueError('direct_patch_source_index')
    schema = deepcopy(base.tools[0].input_schema)
    # Share the replacement definition, as the base tool already does for its
    # issue types; repeating it per block exceeds the existing input envelope.
    schema.setdefault('$defs', {})['DirectPatchReplacement'] = Replacement.model_json_schema()
    schema['required'].append('repairs')
    schema['properties']['repairs'] = dict(type='array', maxItems=512, items=dict(
        type='object', additionalProperties=False, required=['issue_ids', 'edits'], properties={
            'issue_ids': dict(type='array', minItems=1, maxItems=512, uniqueItems=True,
                items=dict(type='integer', minimum=1, maximum=512)),
            'edits': dict(type='object', minProperties=1, additionalProperties=False, properties={
                f'block_{n}': dict(type='array', minItems=1, maxItems=512,
                    items={'$ref': '#/$defs/DirectPatchReplacement'})
                for n in range(1, len(inputs.source.blocks) + 1)})}))
    return duty.budget_check(replace(base, metadata=metadata,
        tools=(replace(base.tools[0], input_schema=schema),),
        messages=(replace(base.messages[0], content=base.messages[0].content + PATCH_POLICY),
                  *base.messages[1:])))


def validate(raw, inputs, name):
    wire = PatchReview.model_validate(strict_json(raw), strict=True)
    duty.validate(compact(wire.model_dump(mode='json', exclude={'repairs'})), inputs, name)
    if wire.verdict != 'needs_revision':
        if wire.repairs:
            raise ValueError('direct_patch_no_repairs_on_pass_or_fail')
        return wire
    ids = [i for repair in wire.repairs for i in repair.issue_ids]
    if sorted(ids) != list(range(1, len(wire.issues) + 1)):
        raise ValueError('direct_patch_issue_inventory')
    return wire


@dataclass(frozen=True)
class Proposal:
    version: str
    duty: str
    input_sha256: str
    report_sha256: str
    request_sha256: str
    raw: str


def bind(inputs, name, raw):
    validate(raw, inputs, name)
    return Proposal(VERSION, name, digest(inputs.data_json), digest(inputs.source.report),
        duty.request_sha(review_request(inputs, name)), raw)


def _patches(inputs, proposals):
    report_inputs(inputs, inputs.source.report)
    if len(proposals) != 2 or {p.duty for p in proposals} != set(duty.DUTIES):
        raise ValueError('direct_patch_pair_inventory')
    source = inputs.source
    spans = _block_spans(source)
    operations, opinions = [], {}
    for proposal in sorted(proposals, key=lambda p: duty.DUTIES.index(p.duty)):
        if proposal != bind(inputs, proposal.duty, proposal.raw):
            raise ValueError('direct_patch_binding')
        wire = validate(proposal.raw, inputs, proposal.duty)
        if wire.verdict == 'fail':
            raise ValueError('direct_patch_terminal_opinion')
        opinions[proposal.duty] = dict(raw=proposal.raw, raw_sha256=digest(proposal.raw),
            request_sha256=proposal.request_sha256)
        for group, repair in enumerate(wire.repairs, 1):
            for key, changes in repair.edits.items():
                if not re.fullmatch(r'block_[1-9][0-9]*', key):
                    raise ValueError('direct_patch_selector')
                block = int(key[6:])
                if block > len(spans) or not 1 <= len(changes) <= 512:
                    raise ValueError('direct_patch_selector')
                text = source.blocks[block - 1][1]
                for change in changes:
                    if len(operations) >= 512:
                        raise ValueError('direct_patch_operation_limit')
                    start = text.find(change.before)
                    if start < 0 or text.find(change.before, start + 1) >= 0:
                        raise ValueError('direct_patch_anchor_not_unique')
                    if change.before == change.after:
                        raise ValueError('direct_patch_noop')
                    start += spans[block - 1][0]
                    operations.append(dict(duty=proposal.duty, group=group,
                        issue_ids=repair.issue_ids, selector=key, block=block,
                        start=start, end=start + len(change.before), **change.model_dump(mode='json')))
    return operations, opinions


COORDINATION_VERSION = 'explicit-original-patch-coordination-v1'


def conflict_inventory(inputs, proposals):
    """All original operations and interval components, without choosing a fix."""
    operations, opinions = _patches(inputs, proposals)
    candidates = [dict(id=f'op_{i}', **op) for i, op in enumerate(operations, 1)]
    components, current, end = [], [], -1
    for op in sorted(candidates, key=lambda op: (op['start'], op['end'], op['id'])):
        if current and op['start'] >= end:
            if len(current) > 1:
                components.append(current)
            current, end = [], -1
        current.append(op['id'])
        end = max(end, op['end'])
    if len(current) > 1:
        components.append(current)
    return dict(version=COORDINATION_VERSION, input_sha256=digest(inputs.data_json),
        pack_sha256=digest(inputs.pack_json), original_report_sha256=digest(inputs.source.report),
        opinions=opinions, operations=candidates,
        conflicts=[dict(component=i, operation_ids=ids) for i, ids in enumerate(components, 1)])


def inventory_sha(inventory):
    # Session journals sort object keys. Hash meaning independent of disk key order,
    # while the raw Provider opinion strings remain byte-for-byte unchanged.
    return digest(json.dumps(inventory, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')))


def coordinated_operations(inventory, coordination):
    """Validate exact choice/issue accounting only; Host semantics remain required."""
    def fail():
        raise ValueError('direct_patch_coordination_invalid')
    if (not isinstance(coordination, dict)
            or set(coordination) != {'version', 'inventory_sha256', 'resolutions'}
            or coordination['version'] != COORDINATION_VERSION
            or coordination['inventory_sha256'] != inventory_sha(inventory)
            or not isinstance(coordination['resolutions'], list)
            or len(coordination['resolutions']) != len(inventory['conflicts'])
            or not inventory['conflicts']):
        fail()
    candidates = {op['id']: op for op in inventory['operations']}
    conflicted = {i for c in inventory['conflicts'] for i in c['operation_ids']}
    chosen = set(candidates) - conflicted
    for component, resolution in zip(inventory['conflicts'], coordination['resolutions']):
        if (not isinstance(resolution, dict)
                or set(resolution) != {'component', 'selected_operation_ids', 'issue_coverage'}
                or type(resolution['component']) is not int
                or resolution['component'] != component['component']):
            fail()
        ids, coverage = resolution['selected_operation_ids'], resolution['issue_coverage']
        if (not isinstance(ids, list) or not ids or any(type(i) is not str for i in ids)
                or len(set(ids)) != len(ids) or not set(ids) <= set(component['operation_ids'])
                or not isinstance(coverage, list)):
            fail()
        expected = {(candidates[i]['duty'], issue)
            for i in component['operation_ids'] for issue in candidates[i]['issue_ids']}
        covered, referenced = [], set()
        for row in coverage:
            if (not isinstance(row, dict)
                    or set(row) != {'duty', 'issue_id', 'selected_operation_ids', 'reason'}
                    or type(row['duty']) is not str or type(row['issue_id']) is not int
                    or not isinstance(row['reason'], str) or not row['reason'].strip()):
                fail()
            refs = row['selected_operation_ids']
            if (not isinstance(refs, list) or not refs or any(type(i) is not str for i in refs)
                    or len(set(refs)) != len(refs) or not set(refs) <= set(ids)):
                fail()
            covered.append((row['duty'], row['issue_id']))
            referenced.update(refs)
        if len(covered) != len(expected) or set(covered) != expected or referenced != set(ids):
            fail()
        chosen.update(ids)
    selected = [op for op in inventory['operations'] if op['id'] in chosen]
    ordered = sorted(selected, key=lambda op: op['start'])
    if any(a['end'] > b['start'] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('direct_patch_coordination_still_overlaps')
    return selected


def preview(inputs, proposals, *, coordination=None):
    """Unapproved deterministic preview; never manufacture an editor exchange."""
    operations, opinions = _patches(inputs, proposals)
    source = inputs.source
    extra = {}
    applied = operations
    if coordination is not None:
        inventory = conflict_inventory(inputs, proposals)
        selected = coordinated_operations(inventory, coordination)
        applied = [{k: v for k, v in op.items() if k != 'id'} for op in selected]
        extra = dict(coordination=deepcopy(coordination), conflict_inventory=inventory,
            selected_operations=selected, coordination_semantics_verified=False)
    ordered = sorted(applied, key=lambda op: op['start'])
    if any(a['end'] > b['start'] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('direct_patch_overlap_requires_new_joint_design')
    report = source.report
    for op in reversed(ordered):
        report = report[:op['start']] + op['after'] + report[op['end']:]
    validate_revised_report(report, source.report)
    _section_order(report)
    report_blocks(report)
    for name in duty.DUTIES:
        reject_revision_policy_echo(report, source.report, review_request(inputs, name))
    knowledge = strict_json(inputs.data_json)['knowledge']
    ReviewHarness._validate_report_citations(report, KnowledgeEvidence(
        context=knowledge['context'], citations=tuple(KnowledgeCitation(**{
            k: v for k, v in row.items() if k != 'retrievals'}) for row in knowledge['citations'])))
    revised = report_inputs(inputs, report)
    return EditAssembly(report, dict(version=VERSION, opinions=opinions, operations=operations, **extra,
        input_sha256=digest(inputs.data_json), original_report_sha256=digest(source.report),
        assembled_report_sha256=digest(report), preview_only=True,
        semantic_approval=False, production_admitted=False, native_acceptance_verified=False,
        semantic_compatibility_verified=False, full_final_review_required=True,
        fresh_request_sha256={name: duty.request_sha(review_request(revised, name, 'fresh'))
            for name in duty.DUTIES}))
