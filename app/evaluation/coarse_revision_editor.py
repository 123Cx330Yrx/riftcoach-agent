"""Unregistered necessary-edit adapter over the current full-context reviewer.

Changes one existing revision slot, not review criteria or pass/fail control flow.
Exact text replacement preserves untouched bytes; it does not prove semantics.
No provider construction, product registration, retry or publication authority.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib

from app.evaluation.golden_coarse_source_projection import resolve_refs, source_catalog
from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_role_boundary_examples import RoleBoundaryExamplesReviewWorkflow as Current
from app.evaluation.golden_semantic_review import reject_revision_policy_echo
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.source_patch_editor import EditSet, SUBMIT_TOOL, apply_edits
from app.providers.models import ToolSpec, ToolChoiceMode

VERSION = 'coarse-source-explicit-revision-v1'
TEXT_OUTPUT = '只输出完整Markdown报告，不输出审查JSON或修改说明。'
EDIT_OUTPUT = (
    '只调用submit_source_edits提交必要替换，不输出完整报告或其他文字。'
    '每项用block定位原段；before须为该段内唯一连续原文，after为替换文本；'
    '所有操作同时针对原稿，不允许重叠。source_ids仅选source_roots编号，'
    'reason说明真实来源支持的必要修改；无必要改动则edits为空。'
)


def edit_request(inputs, accepted):
    base = Current.make_request(inputs, accepted=accepted)
    policy = base.messages[0].content
    if policy.count(TEXT_OUTPUT) != 1:
        raise ValueError('coarse_edit_output_contract_changed')
    schema = deepcopy(EditSet.model_json_schema())
    references = schema['$defs']['TextEdit']['properties']['source_ids']
    references['items']['enum'] = [r['source_id'] for r in source_catalog(inputs)['roots']]
    references['uniqueItems'] = True
    return budget_check(replace(base,
        messages=(replace(base.messages[0], content=policy.replace(TEXT_OUTPUT, EDIT_OUTPUT)),
                  *base.messages[1:]),
        tools=(ToolSpec(SUBMIT_TOOL, '提交必要文本替换；不发布。', schema),),
        tool_choice=ToolChoiceMode.AUTO, response_contract=None))


def inspect_edit_exchange(prepared, exchange, inputs, accepted):
    """Validate the real tool response, then bind the assembled full report."""
    if prepared != edit_request(inputs, accepted):
        raise ValueError('coarse_edit_input_changed')
    issued, response = exchange.issued_request, exchange.response
    if (issued.messages != prepared.messages or issued.tools != prepared.tools
            or issued.tool_choice != prepared.tool_choice
            or issued.response_contract != prepared.response_contract
            or issued.max_tokens != prepared.max_tokens
            or issued.timeout_s > prepared.timeout_s
            or issued.temperature != prepared.temperature or issued.top_p != prepared.top_p
            or any(issued.metadata.get(k) != v for k, v in prepared.metadata.items())
            or hashlib.sha256(validate_request(issued, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
            != exchange.receipt_request_sha256):
        raise ValueError('coarse_edit_exchange_identity')
    if (response.provider, response.model) != ('zhipu', 'glm-5.3-flash'):
        raise ValueError('coarse_edit_response_identity')
    if (response.finish_reason != 'tool_calls' or (response.content or '').strip()
            or len(response.tool_calls) != 1 or response.tool_calls[0].name != SUBMIT_TOOL):
        raise ValueError('coarse_edit_tool_channel')
    raw = compact(dict(response.tool_calls[0].arguments))
    assembly = apply_edits(raw, inputs, resolve_sources=resolve_refs,
        make_final_request=Current.make_request, policy=prepared.messages[0].content,
        version=VERSION)
    reject_revision_policy_echo(assembly.report, inputs.source.report, prepared)
    return assembly


class CoarseRevisionWorkflow(Current):
    """Reuse all initial/revise/fresh ordering, source binding and failure rules."""
    last_edit_journal = None

    def evaluate(self, request):
        try:
            return super().evaluate(request)
        except BaseException:
            self.stopped = True
            raise

    def revise(self, request):
        try:
            return super().revise(request)
        except BaseException:
            self.stopped = True
            raise

    @staticmethod
    def make_request(inputs, **kwargs):
        if kwargs.get('accepted') is not None:
            if set(kwargs) != {'accepted'}:
                raise ValueError('coarse_edit_mode_conflict')
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
            raise ValueError('coarse_edit_input_changed')
        budget_check(prepared)
        self.calls += 1
        try:
            exchange = self.send(prepared)
            self.record(phase, exchange)  # Retain the actual response before parsing or rejection.
            assembly = inspect_edit_exchange(prepared, exchange, inputs, accepted)
            self.last_edit_journal = assembly.journal
            return assembly.report
        except BaseException:
            self.stopped = True
            raise
