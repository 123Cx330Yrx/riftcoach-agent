"""Prospective identity/package/IPC boundaries; synthetic evidence only."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from app.evaluation import golden_stream_bridge as legacy
from app.providers.models import ChatResponse, TokenUsage
from scripts import document_semantic_request as identity
from scripts import prepare_document_semantic_comparison as preparation
from scripts import document_semantic_host_task as host_task


@pytest.fixture(scope='module')
def rows():
    return preparation.controls()[1]


def test_complete_fixed_requests_and_default_admission_closed(rows):
    assert len(rows) == 15
    for row, material, request in rows:
        restored = identity.baseline(request)
        assert json.loads(legacy.validate_request(restored,
            transport_id=legacy.TIMED_REVIEW_TRANSPORT_ID)) == material['original_request']
        assert row['request_sha256'] == identity.request_sha(request)
        assert request.messages[1:] == restored.messages[1:]
        # Expected labels, historical findings and Host interpretation remain
        # outside the actual request; the only new marker names a variant.
        assert set(request.metadata[identity.MARKER]) == {'version', 'variant'}
        with pytest.raises(ValueError):
            legacy.validate_request(request, transport_id=legacy.TIMED_REVIEW_TRANSPORT_ID)


@pytest.mark.parametrize('fault', ['business', 'suffix', 'marker', 'timeout', 'tool'])
def test_corrupted_policy_schema_or_identity_is_rejected(rows, fault):
    request = rows[1][2]
    if fault == 'business':
        request = replace(request, messages=(replace(request.messages[0],
            content='Changed business rule\n' + request.messages[0].content), *request.messages[1:]))
    elif fault == 'suffix':
        request = replace(request, messages=(replace(request.messages[0],
            content=request.messages[0].content + '\nextra'), *request.messages[1:]))
    elif fault == 'marker':
        request = replace(request, metadata={**request.metadata, identity.MARKER: {
            'version': identity.VERSION, 'variant': 'short_examples', 'expected': 'pass'}})
    elif fault == 'timeout':
        request = replace(request, timeout_s=601)
    else:
        request = replace(request, tools=())
    with pytest.raises(ValueError):
        identity.request_bytes(request)


def test_new_process_receipt_binds_actual_variant_and_keeps_shared_module_unchanged(rows, tmp_path):
    request = rows[1][2]
    original = (legacy.TRANSPORTS, legacy.TIMED_REVIEW_TRANSPORT_ID, legacy.validate_request,
                legacy.run_child)
    bridge = identity.isolated_bridge()
    captured = {}
    # Intercept the process boundary only; never instantiate an SDK or use a key.
    from unittest.mock import patch
    # isolated_bridge captures its owned original run_child; replace the actual
    # subprocess boundary instead of bypassing its command rewrite.
    class Child:
        returncode = 0
        stdin = stdout = None
        def poll(self):
            return self.returncode
        def wait(self, timeout=None):
            return self.returncode
        def communicate(self, input=None, timeout=None):
            captured['raw'] = input
            return (legacy.RESPONSE.dump_json(ChatResponse(provider='zhipu', model='glm-5.3',
                content='synthetic', finish_reason='stop', usage=TokenUsage(input_tokens=1, output_tokens=1))), b'')
    def popen(command, **kwargs):
        captured['command'] = command
        return Child()
    with patch.dict(bridge.os.environ, {}, clear=True), patch.object(bridge.subprocess, 'Popen', popen):
        provider = bridge.GoldenProcessStreamProvider(settings=SimpleNamespace(
            model='glm-5.3', api_key='synthetic-only', base_url='https://open.bigmodel.cn/api/paas/v4'),
            directory=tmp_path, transport_id=identity.TRANSPORT)
        provider.chat(request)
    assert captured['raw'] == identity.request_bytes(request)
    assert captured['raw'] != legacy.validate_request(identity.baseline(request),
        transport_id=legacy.TIMED_REVIEW_TRANSPORT_ID)
    assert captured['command'][captured['command'].index('-m') + 1] == 'scripts.document_semantic_request'
    reservation = json.loads((tmp_path / 'stream-001/reservation.json').read_bytes())
    assert reservation['request_sha256'] == identity.request_sha(request)
    assert reservation['transport_id'] == identity.TRANSPORT
    assert original == (legacy.TRANSPORTS, legacy.TIMED_REVIEW_TRANSPORT_ID, legacy.validate_request,
                        legacy.run_child)


def test_package_rejects_changed_source_and_orphan_and_is_create_only(tmp_path):
    package = tmp_path / 'package'
    value = preparation.package(package, root_thread_id='synthetic-root',
                                independent_thread_id='synthetic-independent')
    assert preparation.verify_package(package)['requests'] == 15
    assert value['preparation_plan']['budget']['role_calls'] == {'glm-5.3': 15, 'glm-5.3-flash': 0}
    assert not value['preparation_plan']['execution_ready']
    with pytest.raises(FileExistsError):
        preparation.package(package, root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')
    path = package / value['files'][0]['material_path']
    original = path.read_bytes()
    path.write_bytes(original + b' ')
    with pytest.raises(ValueError, match='material_changed'):
        preparation.verify_package(package)
    path.write_bytes(original)
    (package / 'orphan.json').write_text('{}')
    with pytest.raises(ValueError, match='inventory_changed'):
        preparation.verify_package(package)


def test_native_task_uses_actual_policy_full_material_and_checkpoint_without_certification(rows, tmp_path):
    from app.evaluation.golden_review_experiment import digest
    from scripts.host_review_task_checkpoint import publish, read, check_answer
    plan, _ = preparation.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-independent')
    row, material, request = rows[4]  # Correct historical scope:3 final.
    from app.evaluation import document_review_qualification as qualification
    source = next(s for c, s in qualification.frozen_cases()[0] if c['key'] == row['source_key'])
    inputs = host_task.TimedDocumentWorkflow.build_inputs(replace(source, report=material['report']))
    from app.providers.models import ToolCall
    response = ChatResponse(provider='zhipu', model='glm-5.3', content=None,
        finish_reason='tool_calls', usage=TokenUsage(input_tokens=1, output_tokens=1),
        tool_calls=(ToolCall(id='synthetic-only', name='submit_report_review', arguments=dict(
            score=96, verdict='pass', issues=[], issue_resolutions=[], advisories=[])),))
    _, stage = host_task.stage_for(row, inputs, request, response)
    bound = dict(plan_sha256=preparation.sha(preparation.options.canonical(plan)), key=row['key'],
        stage=row['stage'], response_sha256='1'*64, report_sha256=digest(stage['report']),
        request_sha256=identity.request_sha(request))
    raw = identity.request_bytes(request)
    (tmp_path/'material.json').write_bytes(preparation.options.canonical(material))
    task = host_task.task(plan, row, stage, bound, tmp_path, raw, tmp_path/'material.json')
    instructions = json.loads(task)['instructions']
    assert 'All four must be true' in instructions and str((tmp_path/'material.json').resolve()) in instructions
    reference = instructions.split('BEGIN VERIFIED BUSINESS-POLICY REFERENCE\n', 1)[1].split(
        '\nEND VERIFIED BUSINESS-POLICY REFERENCE', 1)[0]
    assert json.loads(reference)['policies'][0]['policy_text'] == request.messages[0].content
    task_path = tmp_path/'task.json'
    task_path.write_text(task, encoding='utf-8')
    checkpoint = tmp_path/'checkpoint.json'
    sha = publish(checkpoint, task_path, 'synthetic-independent')
    assert read(checkpoint, sha)[1] == json.loads(task)
    # Routing check is not a review schema or author attestation; no native
    # event/receipt is invented by this synthetic construction.
    answer = json.dumps(dict(binding=bound, review=dict(binding=bound))).encode()
    assert check_answer(checkpoint, sha, answer) == answer
    with pytest.raises(ValueError, match='semantic_host_task_binding'):
        host_task.task(plan, row, stage, {**bound, 'request_sha256':'0'*64}, tmp_path, raw, tmp_path/'material.json')
    (tmp_path/'material.json').write_bytes(b'{}')
    with pytest.raises(ValueError, match='semantic_host_material_binding'):
        host_task.task(plan, row, stage, bound, tmp_path, raw, tmp_path/'material.json')
