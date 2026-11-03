"""Time600 workflow on unchanged full-source business validators and editor."""
import hashlib

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_review_experiment import compact
from scripts.report_contrast_review import ContrastDocumentWorkflow
from scripts import report_block_keyed_editor as editor


def request_sha(request):
    return hashlib.sha256(timing.request_bytes(request)).hexdigest()


def edit_request(inputs, accepted):
    return timing.prepare_request(editor.edit_request(inputs, accepted))


def tool_result(prepared, exchange):
    # DocumentReviewWorkflow already checks every prepared/issued field.
    if request_sha(exchange.issued_request) != exchange.receipt_request_sha256:
        raise ValueError("integrated_receipt_mismatch")
    response = exchange.response
    if (response.finish_reason != "tool_calls" or (response.content or "").strip()
            or len(response.tool_calls) != 1 or response.tool_calls[0].name != "submit_report_review"):
        raise ValueError("native_review_tool_channel_invalid")
    return compact(dict(response.tool_calls[0].arguments))


class TimedDocumentWorkflow(ContrastDocumentWorkflow):
    request_sha = staticmethod(request_sha)
    check_request = staticmethod(timing.request_bytes)
    tool_result = staticmethod(tool_result)
    edit_request = staticmethod(edit_request)

    @staticmethod
    def make_request(inputs, **kwargs):
        return timing.prepare_request(ContrastDocumentWorkflow.make_request(inputs, **kwargs))

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = ContrastDocumentWorkflow.validate_review(raw, inputs, previous_raw=previous_raw)
        return payload, wire, dict(journal, request_timing_identity=timing.TIMED_IDENTITY)

    @staticmethod
    def inspect_exchange(prepared, exchange, inputs, accepted):
        return editor.inspect_exchange(prepared, exchange, inputs, accepted,
            make_edit=edit_request, receipt_sha=request_sha, make_final=TimedDocumentWorkflow.make_request)
