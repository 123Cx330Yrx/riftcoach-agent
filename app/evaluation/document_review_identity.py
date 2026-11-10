"""Document role/protocol identity; full source binding belongs to the workflow.

Lossless tables do not preserve original object insertion order. Do not invent
an original data_json/catalog hash by reserializing them. Issued/prepared bytes,
sources and catalogue are bound by the workflow and strict receipt replay.
"""
from dataclasses import replace
import re

from app.evaluation.golden_explicit_source_projection import _unpack, END
from app.evaluation.golden_inference_coverage import report_blocks
from app.evaluation.golden_review_experiment import SourceIndex, compact
from app.evaluation.golden_role_boundary_examples import review_policy
from app.evaluation.golden_coarse_source_projection import VERSION as PROJECTION
from app.providers.models import MessageRole, ToolChoiceMode
from scripts import report_document_view as view

VERSION = 'document-review-request-identity-v1'
START = '[UNTRUSTED REPORT DOCUMENT]\n'
STOP = '\n[END UNTRUSTED REPORT DOCUMENT]'


def baseline(request):
    """Verify presentation/protocol, normalize only for role classification."""
    if (request.metadata.get('report_presentation') != view.VERSION
            or len(request.messages) != 4
            or tuple(m.role for m in request.messages) != (
                MessageRole.SYSTEM, MessageRole.USER, MessageRole.USER, MessageRole.USER)):
        raise ValueError('document_identity_message_shape')
    text = request.messages[1].content or ''
    if not text.startswith(START) or not text.endswith(STOP):
        raise ValueError('document_identity_envelope')
    marked = text[len(START):-len(STOP)]
    first = re.search(r'\n\[HOST_BLOCK:([0-9a-f]{16}_*):1\]\n', marked)
    if first is None:
        raise ValueError('document_identity_marker')
    marker = re.compile(r'\n\[HOST_BLOCK:' + re.escape(first[1]) + r':([1-9][0-9]*)\]\n')
    report = marker.sub('', marked)
    blocks = tuple((b['block_id'], b['text']) for b in report_blocks(report))
    source = SourceIndex(report, blocks, (), '')
    if view.mark_document(source)[0] != marked:
        raise ValueError('document_identity_marker_binding')
    phase = request.metadata.get('review_phase')
    if phase not in ('native_business_review', 'native_business_reassessment'):
        raise ValueError('document_identity_phase')
    policy = review_policy(None if phase == 'native_business_review' else '{}')
    if (policy.count(view.ADDRESS) != 1
            or request.messages[0].content != policy.replace(view.ADDRESS, view.DOCUMENT_ADDRESS)):
        raise ValueError('document_identity_policy')
    clean = dict(request.metadata)
    clean.pop('report_presentation')
    marker_value = clean.pop('coach_budget_contract', None)
    if marker_value not in (None, 'coach-bounded-review-v2'):
        raise ValueError('document_identity_budget_marker')
    if (set(clean) != {'harness_step', 'review_phase', 'source_projection', 'source_catalog_sha256', 'review_delivery', 'review_output'}
            or request.max_tokens != 32768 or not 0 < request.timeout_s <= 300
            or request.temperature != 1.0 or request.top_p != .95
            or request.response_contract is not None
            or clean.get('review_delivery') != 'role-review-tool-schema-only-v1'
            or clean.get('review_output') != 'role-review-clarity-markers-v1'
            or request.tool_choice is not ToolChoiceMode.AUTO
            or len(request.tools) != 1 or request.tools[0].name != 'submit_report_review'):
        raise ValueError('document_identity_request_contract')
    projected = replace(request, metadata=clean, messages=(
        replace(request.messages[0], content=policy), request.messages[2], request.messages[3]))
    header, data = _unpack(projected)
    if 'blocks' in data['source_index']:
        raise ValueError('document_identity_duplicate_report')
    data['source_index']['blocks'] = source.prompt_sources()['blocks']
    return replace(projected, messages=(projected.messages[0],
        replace(projected.messages[1], content=header + compact(data) + END), projected.messages[2]))


def role_for_request(request):
    from app.runtime.reviewer_roles import role_for_request as old
    if request.metadata.get('report_presentation') is not None:
        return old(baseline(request), source_projection=PROJECTION)
    role = old(request, source_projection=PROJECTION)
    if role == 'review':
        raise ValueError('document_identity_structured_review_rejected')
    return role


def request_identity(request):
    from app.runtime.reviewer_roles import profile_for_role
    return 'zhipu', profile_for_role(role_for_request(request)).model
