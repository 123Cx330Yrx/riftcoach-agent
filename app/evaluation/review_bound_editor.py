"""Unregistered revision protocol; review provenance is not edit support.

No provider construction, publication authority, or old-response conversion.
The existing full-context initial/revision/fresh state machine is preserved.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib

from pydantic import Field

from app.evaluation.coarse_revision_editor import CoarseRevisionWorkflow, Current, TEXT_OUTPUT
from app.evaluation.coach_report import validate_revised_report
from app.evaluation.golden_coarse_source_projection import resolve_refs, source_catalog
from app.evaluation.golden_inference_coverage import MAX_REPORT_CHARS, report_blocks
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_native_issues_review import budget_check, strict_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_semantic_review import reject_revision_policy_echo
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.source_patch_editor import EditAssembly, _block_spans, _section_order, report_inputs
from app.harness.runtime import ReviewHarness
from app.harness.steps import KnowledgeCitation, KnowledgeEvidence
from app.providers.models import ToolSpec, ToolChoiceMode

VERSION = 'review-bound-text-edits-offline-v1'
TOOL = 'submit_review_edits'
OUTPUT = (
    '只调用submit_review_edits提交必要替换，不输出完整报告或其他文字。'
    '每项包含block、before、after、reason：before须为block内唯一连续原文，'
    'after为替换文本，reason解释必要修改；所有操作针对原稿，不得重叠。'
    '程序保留完整审查意见及其来源上下文；这不证明任何修改有据。'
    'source_ids用于解释输入审查意见引用，不属于编辑输出字段。'
    '核对完整真实来源，只修实际问题及直接影响内容，保留正确分析与身份目标。'
    '无需改动可提交空edits；空操作不代表问题已解决，完整成稿仍须重新审查。'
)


class TextChange(Strict):
    block: int = Field(ge=1, le=64)
    before: str = Field(min_length=1, max_length=MAX_REPORT_CHARS)
    after: str = Field(max_length=MAX_REPORT_CHARS)
    reason: str = Field(min_length=1, max_length=700)


class Changes(Strict):
    edits: list[TextChange] = Field(max_length=512)


def review_context(inputs, accepted):
    report_inputs(inputs, inputs.source.report)
    # Validate fields, but do not invent a previous reassessment for a wire that
    # the workflow has already validated against its actual previous response.
    wire = type(accepted).model_validate(accepted.model_dump(mode='json'), strict=True)
    if wire.verdict not in ('needs_revision', 'pass'):
        raise ValueError('review_bound_verdict')
    sources = []
    for ordinal, issue in enumerate(wire.issues, 1):
        if issue.block > len(inputs.source.blocks):
            raise ValueError('review_bound_issue_block')
        sources.append(dict(review_issue=ordinal, block=issue.block,
                            selected_sources=resolve_refs(inputs, issue.source_ids)))
    for resolution in wire.issue_resolutions:
        resolve_refs(inputs, resolution.source_ids)
    projection = wire.model_dump(mode='json')
    return dict(origin='host_bound_review_source_context', accepted_review=projection,
                accepted_review_sha256=digest(compact(projection)),
                input_sha256=digest(inputs.data_json),
                catalog_sha256=source_catalog(inputs)['catalog_sha256'],
                review_sources=sources, proves_edit_support=False,
                editor_selected_sources=False)


def edit_request(inputs, accepted):
    review_context(inputs, accepted)
    base = Current.make_request(inputs, accepted=accepted)
    if base.messages[0].content.count(TEXT_OUTPUT) != 1:
        raise ValueError('review_bound_output_contract_changed')
    schema = deepcopy(Changes.model_json_schema())
    schema['properties']['edits']['items'] = schema.pop('$defs')['TextChange']
    return budget_check(replace(base,
        messages=(replace(base.messages[0], content=base.messages[0].content.replace(TEXT_OUTPUT, OUTPUT)),
                  *base.messages[1:]),
        tools=(ToolSpec(TOOL, '提交必要替换；不声明来源核验通过或发布。', schema),),
        tool_choice=ToolChoiceMode.AUTO, response_contract=None))


def inspect_exchange(prepared, exchange, inputs, accepted):
    if prepared != edit_request(inputs, accepted):
        raise ValueError('review_bound_input_changed')
    issued, response = exchange.issued_request, exchange.response
    # Compare every request field, allowing only the real shared-budget marker
    # and a tightened timeout; no changed prompt, model parameter or tool schema.
    metadata = dict(issued.metadata)
    marker = metadata.pop('coach_budget_contract', None)
    if (marker not in (None, 'coach-bounded-review-v2')
            or not 0 < issued.timeout_s <= prepared.timeout_s
            or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared
            or hashlib.sha256(validate_request(issued, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
            != exchange.receipt_request_sha256):
        raise ValueError('review_bound_exchange_identity')
    if ((response.provider, response.model) != ('zhipu', 'glm-5.3-flash')
            or response.finish_reason != 'tool_calls' or (response.content or '').strip()
            or len(response.tool_calls) != 1 or response.tool_calls[0].name != TOOL):
        raise ValueError('review_bound_tool_channel')
    raw = compact(dict(response.tool_calls[0].arguments))
    wire = Changes.model_validate(strict_json(raw), strict=True)
    context = review_context(inputs, accepted)
    source = inputs.source
    spans = _block_spans(source)
    operations = []
    for number, change in enumerate(wire.edits, 1):
        if change.block > len(spans):
            raise ValueError('review_bound_block_unknown')
        block = source.blocks[change.block - 1][1]
        pos = block.find(change.before)
        if pos < 0 or block.find(change.before, pos + 1) >= 0:
            raise ValueError('review_bound_anchor_not_unique')
        if change.before == change.after:
            raise ValueError('review_bound_noop')
        start = spans[change.block - 1][0] + pos
        operations.append(dict(ordinal=number, start=start, end=start + len(change.before),
                               **change.model_dump(mode='json')))
    ordered = sorted(operations, key=lambda op: op['start'])
    if any(a['end'] > b['start'] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('review_bound_overlap')
    report = source.report
    for op in reversed(ordered):
        report = report[:op['start']] + op['after'] + report[op['end']:]
    validate_revised_report(report, source.report)
    _section_order(report)
    report_blocks(report)
    reject_revision_policy_echo(report, source.report, prepared)
    knowledge = strict_json(inputs.data_json)['knowledge']
    ReviewHarness._validate_report_citations(report, KnowledgeEvidence(
        context=knowledge['context'], citations=tuple(KnowledgeCitation(**{
            k: v for k, v in c.items() if k != 'retrievals'}) for c in knowledge['citations'])))
    final = Current.make_request(report_inputs(inputs, report))
    return EditAssembly(report, dict(version=VERSION, raw=raw, raw_sha256=digest(raw),
        review_source_context=context, operations=operations,
        original_report=source.report, original_report_sha256=digest(source.report),
        assembled_report=report, assembled_report_sha256=digest(report),
        semantic_approval=False, production_admitted=False, full_final_review_required=True,
        final_review_request_sha256=hashlib.sha256(validate_request(
            final, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest()))


class ReviewBoundRevisionWorkflow(CoarseRevisionWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        if kwargs.get('accepted') is not None:
            if set(kwargs) != {'accepted'}:
                raise ValueError('review_bound_mode_conflict')
            return edit_request(inputs, kwargs['accepted'])
        return Current.make_request(inputs, **kwargs)

    def _call(self, prepared, phase):
        if phase != 'native_business_revision':
            return super()._call(prepared, phase)
        self.last_edit_journal = None
        if self.stopped or self.calls >= 5 or self._accepted is None:
            raise ValueError('integrated_call_budget_exhausted')
        inputs = self._accepted[0]
        _, accepted, _ = self.validate_review(self._accepted_raw, inputs,
                                             previous_raw=self._accepted_previous)
        if prepared != edit_request(inputs, accepted):
            raise ValueError('review_bound_input_changed')
        budget_check(prepared)
        self.calls += 1
        try:
            exchange = self.send(prepared)
            self.record(phase, exchange)
            assembly = inspect_exchange(prepared, exchange, inputs, accepted)
            self.last_edit_journal = assembly.journal
            return assembly.report
        except BaseException:
            self.stopped = True
            raise
