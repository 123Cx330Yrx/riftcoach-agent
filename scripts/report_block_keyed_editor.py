"""Prospective offline editor: explicit block keys, no inferred selectors.

One tool call retains multi-block edits without the transport's eight-call
limit. No old response conversion, provider construction or admission.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import re

from pydantic import Field

from app.evaluation import review_bound_editor as baseline
from app.evaluation.coach_report import validate_revised_report
from app.evaluation.golden_inference_coverage import MAX_REPORT_CHARS, report_blocks
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_native_issues_review import budget_check, strict_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_semantic_review import reject_revision_policy_echo
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.source_patch_editor import EditAssembly, _block_spans, _section_order, report_inputs
from app.harness.runtime import ReviewHarness
from app.harness.steps import KnowledgeCitation, KnowledgeEvidence
from app.providers.models import ToolSpec
from scripts.report_document_workflow import DocumentReviewWorkflow, request_sha

VERSION = 'offline-block-keyed-editor-v1'
TOOL = 'submit_block_edits'
OUTPUT = (
    '只调用submit_block_edits提交一次必要修改，不输出完整报告或其他文字。'
    'edits是按原稿段号归组的对象：键block_N仅指source_index.blocks中的第N段；'
    '每个键的值是该段修改数组，每项包含before、after、reason。'
    'before须为该段内唯一连续原文，after为替换文本，reason解释必要修改。'
    '同段多项归在同一键下，跨段分别归组；所有操作针对原稿，不得重叠。'
    '只使用工具schema给出的段落键，不另填block、source_ids或issue_id。'
    '核对完整真实来源和完整接受意见，只修实际问题及直接影响内容，保留正确分析与身份目标。'
    '无需改动提交edits={}；空操作不代表问题已解决，完整成稿仍须重新审查。'
)


class Replacement(Strict):
    before: str = Field(min_length=1, max_length=MAX_REPORT_CHARS)
    after: str = Field(max_length=MAX_REPORT_CHARS)
    reason: str = Field(min_length=1, max_length=700)


class BlockChanges(Strict):
    edits: dict[str, list[Replacement]]


def edit_request(inputs, accepted):
    base = baseline.edit_request(inputs, accepted)
    blocks = inputs.source.blocks
    if not 0 < len(blocks) <= 64:
        raise ValueError('block_keyed_source_index')
    schema = dict(type='object', additionalProperties=False, required=['edits'], properties={
        'edits': dict(type='object', additionalProperties=False, properties={
            f'block_{n}': dict(type='array', minItems=1, maxItems=512,
                items=deepcopy(Replacement.model_json_schema())) for n in range(1, len(blocks) + 1)})})
    if base.messages[0].content.count(baseline.OUTPUT) != 1:
        raise ValueError('block_keyed_policy_contract')
    return budget_check(replace(base, tools=(ToolSpec(TOOL,
        '按显式原稿段落键提交必要替换；不判断通过或发布。', schema),), messages=(
            replace(base.messages[0], content=base.messages[0].content.replace(baseline.OUTPUT, OUTPUT)),
            *base.messages[1:])))


def inspect_exchange(prepared, exchange, inputs, accepted):
    if prepared != edit_request(inputs, accepted):
        raise ValueError('block_keyed_input_changed')
    issued, response = exchange.issued_request, exchange.response
    metadata = dict(issued.metadata)
    marker = metadata.pop('coach_budget_contract', None)
    if (marker not in (None, 'coach-bounded-review-v2')
            or not 0 < issued.timeout_s <= prepared.timeout_s
            or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared
            or hashlib.sha256(validate_request(issued, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
            != exchange.receipt_request_sha256):
        raise ValueError('block_keyed_exchange_identity')
    if ((response.provider, response.model) != ('zhipu', 'glm-5.3-flash')
            or response.finish_reason != 'tool_calls' or (response.content or '').strip()
            or len(response.tool_calls) != 1 or response.tool_calls[0].name != TOOL):
        raise ValueError('block_keyed_tool_channel')
    raw = compact(dict(response.tool_calls[0].arguments))
    wire = BlockChanges.model_validate(strict_json(raw), strict=True)
    context = baseline.review_context(inputs, accepted)
    source = inputs.source
    spans = _block_spans(source)
    operations = []
    for selector, replacements in wire.edits.items():
        if not re.fullmatch(r'block_[1-9][0-9]*', selector):
            raise ValueError('block_keyed_selector')
        block_id = int(selector[6:])
        if block_id > len(spans) or not 1 <= len(replacements) <= 512:
            raise ValueError('block_keyed_selector')
        block = source.blocks[block_id - 1][1]
        for change in replacements:
            if len(operations) >= 512:
                raise ValueError('block_keyed_operation_limit')
            pos = block.find(change.before)
            if pos < 0 or block.find(change.before, pos + 1) >= 0:
                raise ValueError('block_keyed_anchor_not_unique')
            if change.before == change.after:
                raise ValueError('block_keyed_noop')
            start = spans[block_id - 1][0] + pos
            operations.append(dict(ordinal=len(operations) + 1, selector=selector,
                block=block_id, start=start, end=start + len(change.before),
                **change.model_dump(mode='json')))
    ordered = sorted(operations, key=lambda op: op['start'])
    if any(a['end'] > b['start'] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('block_keyed_overlap')
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
    final = DocumentReviewWorkflow.make_request(report_inputs(inputs, report))
    return EditAssembly(report, dict(version=VERSION, raw=raw, raw_sha256=digest(raw),
        review_source_context=context, operations=operations,
        original_report=source.report, original_report_sha256=digest(source.report),
        assembled_report=report, assembled_report_sha256=digest(report),
        semantic_approval=False, production_admitted=False, full_final_review_required=True,
        final_review_request_sha256=request_sha(final)))


class BlockKeyedDocumentWorkflow(DocumentReviewWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        if kwargs.get('accepted') is not None:
            if set(kwargs) != {'accepted'}:
                raise ValueError('block_keyed_mode_conflict')
            return edit_request(inputs, kwargs['accepted'])
        return DocumentReviewWorkflow.make_request(inputs, **kwargs)

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
            raise ValueError('block_keyed_input_changed')
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
