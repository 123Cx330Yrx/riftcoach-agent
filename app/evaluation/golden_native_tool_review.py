"""Development-only native review submitted through the existing tool channel.

This is a result submission, not an executable product tool. Keep the historical
text workflows and product fingerprints unchanged while testing this boundary.
"""
from dataclasses import replace
import hashlib

from app.evaluation import golden_native_business_policy as business
from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.providers.models import ToolChoiceMode, ToolSpec

EXPERIMENT_ID = 'golden-native-tool-review-v1'
LIVE_STATUS = 'offline_scope_false_positive'
LIVE_BLOCK_REASON = 'tool_review_scope_false_positive_requires_redesign'
SUBMIT_TOOL = 'submit_report_review'
TEXT_DELIVERY = '只输出给定schema的一个JSON对象，不加前后文字。'
TOOL_DELIVERY = (
    '审查完成后只调用一次submit_report_review，用工具参数提交完整审查结果。'
    '不输出正文、前言或后记，也不调用其他工具。')


def require_live_qualification():
    if LIVE_STATUS != 'bounded_development_after_exact_ci':
        raise ValueError(LIVE_BLOCK_REASON)


def request(inputs, *, previous_raw=None, diagnostics=None, accepted=None):
    base = business.request(inputs, previous_raw=previous_raw,
                            diagnostics=diagnostics, accepted=accepted)
    if accepted is not None:
        return base  # Editing still returns the complete Markdown report.
    schema = base.response_contract.schema_dict()
    header = native.schema_notation(schema) + '\n'
    if not base.messages[1].content.startswith(header):
        raise ValueError('native_tool_schema_header_mismatch')
    policy = base.messages[0].content
    if policy.count(TEXT_DELIVERY) != 1:
        raise ValueError('native_tool_delivery_policy_mismatch')
    return native.budget_check(replace(base, response_contract=None,
        tools=(ToolSpec(SUBMIT_TOOL, '提交完整报告的审查结果；不执行外部操作。', schema),),
        tool_choice=ToolChoiceMode.AUTO,
        messages=(replace(base.messages[0], content=policy.replace(TEXT_DELIVERY, TOOL_DELIVERY)),
                  replace(base.messages[1], content=base.messages[1].content[len(header):]),
                  *base.messages[2:])))


def validate(raw, inputs, *, previous_raw=None):
    payload, wire, journal = business.validate(raw, inputs, previous_raw=previous_raw)
    policy = business.INITIAL_POLICY if previous_raw is None else business.REASSESSMENT_POLICY
    journal = dict(journal, experiment=EXPERIMENT_ID,
        policy_sha256=native.digest(policy.replace(TEXT_DELIVERY, TOOL_DELIVERY)),
        raw_representation='tool_arguments_projection',
        previous_raw_representation='tool_arguments_projection' if previous_raw is not None else None,
        original_response_location='recorded_exchange_response', submission_tool=SUBMIT_TOOL)
    return payload, wire, journal


def tool_result(prepared, exchange):
    # Same issued-input/receipt checks as validate_exchange. Kept local for this
    # experiment rather than changing a shared historical/product fingerprint.
    issued = exchange.issued_request
    if (issued.messages != prepared.messages or issued.response_contract != prepared.response_contract
            or issued.tools != prepared.tools or issued.tool_choice != prepared.tool_choice):
        raise ValueError('integrated_issued_input_mismatch')
    sha = hashlib.sha256(validate_request(issued, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
    if sha != exchange.receipt_request_sha256:
        raise ValueError('integrated_receipt_mismatch')
    response = exchange.response
    if (response.finish_reason != 'tool_calls' or (response.content or '').strip()
            or len(response.tool_calls) != 1 or response.tool_calls[0].name != SUBMIT_TOOL):
        raise ValueError('native_review_tool_channel_invalid')
    # The recorder retains the actual typed response. This serialization is only
    # the existing domain validator's input, never claimed as original content.
    return native.compact(dict(response.tool_calls[0].arguments))


class NativeBusinessReviewWorkflow(native.NativeBusinessReviewWorkflow):
    make_request = staticmethod(request)
    validate_review = staticmethod(validate)

    def _call(self, prepared, phase):
        if not prepared.tools:
            return super()._call(prepared, phase)
        if self.stopped or self.calls >= 5:
            raise ValueError('integrated_call_budget_exhausted')
        native.budget_check(prepared)
        self.calls += 1
        try:
            exchange = self.send(prepared)
            self.record(phase, exchange)
            return tool_result(prepared, exchange)
        except BaseException:
            self.stopped = True
            raise
