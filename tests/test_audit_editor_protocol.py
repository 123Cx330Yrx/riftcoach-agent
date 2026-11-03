"""Public failed/successful calls distinguish encoding from output compliance."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from app.evaluation.review_bound_editor import Changes
from app.providers.errors import ProviderCapabilityError
from app.providers.models import ToolChoiceMode
from scripts import audit_editor_protocol as audit


def current():
    name, _, paths = audit.EXPORTS[-1]
    files = json.loads((audit.RESULTS/name).read_bytes())['public_json_contents']
    return files[paths[0]], files['claim-scope-6/revision/response.json']


def test_public_audit_never_reads_private_runs_or_uses_network(monkeypatch):
    original = Path.read_bytes

    def public_only(path):
        assert 'runs' not in path.parts
        return original(path)

    def forbidden(*args, **kwargs):
        raise AssertionError('network not permitted in offline audit')

    monkeypatch.setattr(Path, 'read_bytes', public_only)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    value = audit.audit()
    assert len(value['rows']) == 11  # Stage/transport copies count only once.
    assert sum(r['schema_valid'] for r in value['rows']) == 8
    assert value['provider_calls'] == 0
    assert not value['qualification_evaluated']
    assert all(r['sdk_parameters_preserved'] and not r['server_strict_requested'] for r in value['rows'])


def test_missing_block_reproduces_actual_schema_and_strict_validator():
    request, response = current()
    before = deepcopy((request, response))
    row = audit.assess(request, response)
    assert row['errors'] == [dict(path=['edits', 0], validator='required', missing_fields=['block'])]
    with pytest.raises(ValidationError) as caught:
        Changes.model_validate(response['tool_calls'][0]['arguments'], strict=True)
    assert caught.value.errors(include_input=False)[0]['loc'] == ('edits', 0, 'block')
    assert (request, response) == before


def test_sdk_nested_schema_and_json_ipc_roundtrip_preserve_required():
    data, _ = current()
    request = audit.REQUEST.validate_json(json.dumps(data, ensure_ascii=False))
    encoded = audit.sdk_projection(request)
    assert encoded['tools'][0]['function']['parameters'] == data['tools'][0]['input_schema']
    assert encoded['extra_body']['tool_stream'] is True
    assert encoded['stream_options'] == dict(include_usage=True)
    assert audit.REQUEST.validate_json(audit.REQUEST.dump_json(request)) == request


def test_required_tool_choice_remains_an_explicit_capability_failure():
    data, _ = current()
    request = audit.REQUEST.validate_json(json.dumps(data))
    with pytest.raises(ProviderCapabilityError) as caught:
        audit.sdk_projection(replace(request, tool_choice=ToolChoiceMode.REQUIRED))
    assert caught.value.missing_capabilities == ('required_tool_choice',)


def test_mixed_output_is_not_counted_as_a_schema_success():
    data, response = current()
    response = deepcopy(response)
    response['content'] = 'extraneous output'
    with pytest.raises(ValueError, match='editor_audit_response_channel'):
        audit.assess(data, response)


def test_changed_public_export_cannot_reuse_old_evidence_digest(tmp_path):
    filename, sha, paths = audit.EXPORTS[-1]
    (tmp_path/filename).write_bytes((audit.RESULTS/filename).read_bytes()+b' ')
    with pytest.raises(ValueError, match='editor_audit_export_changed'):
        audit.audit(tmp_path, ((filename, sha, paths),))


def test_anchor_only_address_cannot_disambiguate_repeated_blocks_or_overlaps():
    assert audit.anchor_occurrences([dict(text='重复句'), dict(text='重复句')], '重复句') == 2
    assert audit.anchor_occurrences([dict(text='aaaa')], 'aaa') == 2
    assert audit.anchor_occurrences([dict(text='原文')], '缺失') == 0
    with pytest.raises(ValueError, match='editor_audit_empty_anchor'):
        audit.anchor_occurrences([dict(text='原文')], '')
