"""Offline-only explicit source IDs over the unchanged native source contract.

Replace the model-facing positional key list, never response IDs or raw history.
There is no live workflow/runner registration. Reversibility proves preservation,
not that a model selects relevant evidence or that a report is correct.
"""
from copy import deepcopy
from dataclasses import replace

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_review_experiment import compact
from app.providers.models import MessageRole

VERSION = 'native-explicit-source-projection-v1'
OLD_ADDRESS = '编号对应source_index.evidence_keys；'
NEW_ADDRESS = ('编号直接查询source_index.evidence_by_id的显式键'
               '（与source_roots的source_id相同），不按数组位置计数；')
START = '[UNTRUSTED DATA]\n'
END = '\n[END UNTRUSTED DATA]'


def _unpack(request):
    if (len(request.messages) != 3
            or tuple(m.role for m in request.messages) != (
                MessageRole.SYSTEM, MessageRole.USER, MessageRole.USER)):
        raise ValueError('explicit_source_message_shape')
    content = request.messages[1].content or ''
    header, marker, body = content.partition(START)
    if not marker or not body.endswith(END):
        raise ValueError('explicit_source_data_envelope')
    data = native.strict_json(body[:-len(END)])
    if not isinstance(data, dict):
        raise ValueError('explicit_source_data_object')
    return header + marker, data


def _check_sources(request, data, inputs):
    # Bind the complete supplied data, not just the list length or key names.
    # Prior opinions/diagnostics are extra members and stay opaque and intact.
    expected = native.request_data(inputs)
    source = expected.pop('deterministic_source_facts')
    if any(key not in data or compact(data[key]) != compact(value)
           for key, value in expected.items()):
        raise ValueError('explicit_source_input_mismatch')
    if request.messages[2].content != (
            '[UNTRUSTED deterministic_source_facts]\n' + source
            + '\n[END UNTRUSTED deterministic_source_facts]'):
        raise ValueError('explicit_source_original_text_mismatch')


def _message(request, header, data, policy, metadata):
    return replace(request, metadata=metadata, messages=(
        replace(request.messages[0], content=policy),
        replace(request.messages[1], content=header + compact(data) + END),
        request.messages[2]))


def project_request(request, inputs):
    """Prepare a review/reassessment/revision request without issuing it."""
    header, data = _unpack(request)
    _check_sources(request, data, inputs)
    policy = request.messages[0].content or ''
    if (policy.count(OLD_ADDRESS) != 1 or policy.count('source_index.evidence_keys') != 1
            or 'source_index.evidence_by_id' in policy
            or 'source_projection' in request.metadata
            or 'evidence_by_id' in data['source_index']):
        raise ValueError('explicit_source_projection_conflict')
    data['source_index'] = {
        ('evidence_by_id' if key == 'evidence_keys' else key):
        ({str(n): ref for n, ref in enumerate(value, 1)} if key == 'evidence_keys' else value)
        for key, value in data['source_index'].items()}
    projected = _message(request, header, data, policy.replace(OLD_ADDRESS, NEW_ADDRESS),
                         {**request.metadata, 'source_projection': VERSION})
    if restore_request(projected, inputs) != request:
        raise ValueError('explicit_source_projection_loss')
    return native.budget_check(projected)


def restore_request(request, inputs):
    """Restore host representation; reject ID/key drift, never repair outputs."""
    header, data = _unpack(request)
    index = data.get('source_index', {})
    expected = {str(n): key for n, key in enumerate(inputs.source.evidence_keys, 1)}
    if (not isinstance(index, dict) or 'evidence_keys' in index
            or index.get('evidence_by_id') != expected):
        raise ValueError('explicit_source_id_map_mismatch')
    policy = request.messages[0].content or ''
    if (request.metadata.get('source_projection') != VERSION
            or policy.count(NEW_ADDRESS) != 1 or 'source_index.evidence_keys' in policy):
        raise ValueError('explicit_source_projection_identity')
    data = deepcopy(data)
    data['source_index'] = {
        ('evidence_keys' if key == 'evidence_by_id' else key):
        (list(inputs.source.evidence_keys) if key == 'evidence_by_id' else value)
        for key, value in index.items()}
    restored = _message(request, header, data, policy.replace(NEW_ADDRESS, OLD_ADDRESS),
                        {key: value for key, value in request.metadata.items()
                         if key != 'source_projection'})
    _check_sources(restored, data, inputs)
    return restored
