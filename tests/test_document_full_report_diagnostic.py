"""Offline wiring evidence for the three-report diagnostic, never live quality."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from scripts import document_full_report_diagnostic as diagnostic
from scripts.document_sampling_screening import load_private
from app.evaluation.golden_journal import write_new_json
from scripts.report_document_view import document, restore_document


@pytest.fixture(scope='module')
def prepared():
    return diagnostic.prepare(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')


def test_new_reports_preserve_complete_calibrated_text_sources_and_policy(prepared, monkeypatch):
    # Preparation must never use ignored run artifacts as a public prerequisite.
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert '/data/runs/' not in path.as_posix()
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    rows = diagnostic.controls()
    fixed = diagnostic.fixture()
    reports = {c['case_id']: c for c in fixed['cases']}
    assert [r['source_key'] for r, _, _ in rows] == ['V2', 'H5', 'S8']
    for cell, material, request in rows:
        assert request.temperature == 1.0 and request.top_p == .95
        assert request.timeout_s == 600 and request.max_tokens == 32768
        assert request.messages[0].content == fixed['full_policy_text']
        assert request.messages[3].content == fixed['deterministic_source_message']
        assert cell['stage'] == 'initial'
        assert material['report'] == diagnostic.report_text(reports[cell['source_key']])
        inputs = diagnostic.inputs_for(cell, material)
        assert len(inputs.source.blocks) == 18
        assert restore_document(document(inputs)[0], inputs) == material['report']
        for b in reports[cell['source_key']]['report']:
            assert b['text'] in material['report']
        assert not {'initial_stage', 'original_stage', 'expected_verdict'} & material.keys()
        assert not {'expected_verdict', 'source_key'} & request.metadata.keys()
    plan = prepared[0]
    assert plan['budget'] == dict(max_calls=3, role_calls={'glm-5.3': 3, 'glm-5.3-flash': 0},
        max_tokens=290304, max_active_seconds=1800, max_host_seconds=86400,
        per_request_seconds=600, per_request_output=32768,
        estimated_uncached_cny='4.288512', hard_billing_cap=False)
    assert plan['execution_authorized'] is plan['native_preflight_verified'] is False
    assert 'scripts/document_sampling_screening.py' in plan['source_sha256']


def test_package_rejects_changed_request_and_extra_file(tmp_path):
    package = diagnostic.Package(tmp_path / 'package')
    package.write(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    path = package.directory / 'report-V2-initial/prepared-request.json'
    original = path.read_bytes()
    path.write_bytes(original + b' ')
    with pytest.raises(ValueError, match='package_material_changed'):
        package.verify()
    path.write_bytes(original)
    (package.directory / 'unexpected.json').write_text('{}')
    with pytest.raises(ValueError, match='package_unexpected_file'):
        package.verify()


def test_changed_calibration_and_source_rejected(monkeypatch):
    monkeypatch.setattr(diagnostic, 'FIXTURE_SHA', '0' * 64)
    with pytest.raises(ValueError, match='fixture_changed'):
        diagnostic.controls()
    monkeypatch.undo()
    original = diagnostic.source_inputs
    def altered(report):
        inputs = original(report)
        from dataclasses import replace
        value = json.loads(inputs.data_json)
        value['user_utterance'] += ' altered'
        return replace(inputs, data_json=diagnostic.base.options.canonical(value).decode())
    monkeypatch.setattr(diagnostic, 'source_inputs', altered)
    # The existing workflow rejects this inconsistent projection even before
    # the new diagnostic's full-source comparison is reached.
    with pytest.raises(ValueError, match='correction_generation_projection_loss'):
        diagnostic.controls()


def execution(tmp_path, monkeypatch, prepared):
    plan, rows = deepcopy(prepared)
    monkeypatch.setattr(diagnostic.base, 'prepare', lambda **kw: (deepcopy(plan), rows))
    monkeypatch.setattr(diagnostic.base, 'controls', lambda: rows)
    fixtures = load_private(Path(__file__).with_name('test_document_semantic_execution.py'),
                            'tests._full_report_execution_fixtures')
    fixtures.runner = diagnostic.runner
    fixtures.identity = diagnostic.identity
    fixtures.transport = diagnostic.transport
    write_new_json(tmp_path / 'plan.json', dict(preparation_plan=plan,
        plan_sha256=diagnostic.base.sha(diagnostic.base.options.canonical(plan)),
        execution_head='f' * 40, ci_run='synthetic-ci'))
    now = datetime.now(timezone.utc)
    authorization = dict(version=diagnostic.base.AUTH_VERSION, authorized=True,
        user_instruction='OFFLINE ONLY authorization fixture',
        plan_sha256=diagnostic.base.sha(diagnostic.base.options.canonical(plan)), budget=plan['budget'],
        head='f' * 40, ci_run='synthetic-ci', issued_at=now.isoformat(),
        expires_at=(now + timedelta(hours=24)).isoformat())
    write_new_json(tmp_path / 'authorization.json', authorization)
    write_new_json(tmp_path / 'execution-preflight.json', dict(verified=True,
        root_thread_id='synthetic-root', independent_thread_id='synthetic-child',
        independent_agent_path='/root/synthetic', input_readability=dict(
            thread_id='synthetic-child', turn_id='synthetic-turn', dispatch_id='synthetic-dispatch',
            current_input_readable=True, future_input_guaranteed=False,
            current_route_and_final_available=True,
            host_review_evidence_policy=plan['host_review_evidence_policy'])))
    return plan, rows, fixtures


@pytest.mark.parametrize('fault', [None, 'abort', 'transport', 'native', 'checkpoint'])
def test_three_once_real_review_wiring_stop_and_readonly_seal(tmp_path, monkeypatch, prepared, fault):
    plan, rows, fixtures = execution(tmp_path, monkeypatch, prepared)
    provider = fixtures.OfflineProvider(fault)
    host = fixtures.OfflineNativeHost(plan, tmp_path, fault)
    result = diagnostic.runner.observe(tmp_path, plan, rows, provider, host.source,
                                       adjudicate=host.adjudicate)
    if fault is None:
        assert result['scan_completed'] and len(provider.calls) == 3, result
        assert result['completed'][1]['host_disagreement']
        assert not result['completed'][1]['semantic_accepted']
        assert result['completed'][2]['key'] == rows[2][0]['key']
        before = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        output = tmp_path.parent / (tmp_path.name + '-seal.json')
        assert diagnostic.runner.seal(tmp_path, output, event_source=host.source)['native_reviews'] == 3
        assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
        assert 'PRIVATE_FIXTURE' not in output.read_text()
        with pytest.raises(FileExistsError):
            diagnostic.runner.seal(tmp_path, output, event_source=host.source)
        task = json.loads((tmp_path / 'report-V2-initial/independent-task.json').read_bytes())
        assert 'no historical Provider stage' in task['instructions']
        assert 'historical initial journal/request' not in task['instructions']
        assert 'expected_verdict' not in task['instructions']
        assert 'report_assessment=null' in task['instructions']
    else:
        assert not result['scan_completed'] and len(provider.calls) == 2, result
        assert len(result['completed']) == 1 and result['unexecuted'] == [rows[2][0]['key']]
        if fault in ('abort', 'transport'):
            assert diagnostic.runner.replay(tmp_path, event_source=host.source)['native_reviews'] == 1
        if fault == 'transport':
            assert result['accounting']['unknown_usage_calls'] == 1
            assert result['accounting']['receiptless_calls'] == 1


def test_new_authorization_cannot_reuse_previous_batch_or_extend_budget(prepared):
    plan = prepared[0]
    now = datetime.now(timezone.utc)
    auth = dict(version=diagnostic.base.AUTH_VERSION, authorized=True,
        user_instruction='OFFLINE fixture', plan_sha256=diagnostic.base.sha(diagnostic.base.options.canonical(plan)),
        budget=deepcopy(plan['budget']), head='f' * 40, ci_run='ci', issued_at=now.isoformat(),
        expires_at=(now + timedelta(hours=24)).isoformat())
    diagnostic.base.check_authorization(auth, plan, 'f' * 40, 'ci', now=now)
    for changed in (dict(auth, version='document-sampling-screening-corrected-authorization-v1'),
                    dict(auth, budget={**auth['budget'], 'max_calls': 4}),
                    dict(auth, expires_at=(now - timedelta(seconds=1)).isoformat())):
        with pytest.raises(ValueError, match='authorization_invalid'):
            diagnostic.base.check_authorization(changed, plan, 'f' * 40, 'ci', now=now)


def test_real_worker_receives_baseline_and_complete_messages_only(tmp_path, monkeypatch, prepared):
    from tests.test_document_sampling_screening import _FAKE_SDK_CHILD
    bridge = diagnostic.identity.isolated_bridge()
    original = bridge.subprocess.Popen
    def child(command, **kwargs):
        at = command.index('-m')
        assert command[at + 1] == 'scripts.document_sampling_screening_request'
        return original([*command[:at], '-c', _FAKE_SDK_CHILD, *command[at + 2:]], **kwargs)
    monkeypatch.setattr(bridge.subprocess, 'Popen', child)
    provider = diagnostic.transport.SemanticProvider(NS(model='glm-5.3', api_key='OFFLINE_FIXTURE',
        base_url='https://open.bigmodel.cn/api/paas/v4'), bridge=bridge)
    for row, _, request in prepared[1]:
        path = tmp_path / row['key'].replace(':', '-')
        provider.chat(request, path)
        sdk = json.loads((path / 'stream-001/sdk-fixture.json').read_bytes())
        assert sdk['model'] == 'glm-5.3' and sdk['temperature'] == 1.0
        assert sdk['max_tokens'] == 32768 and sdk['top_p'] == .95
        assert [m['content'] for m in sdk['messages']] == [m.content for m in request.messages]
        assert 'metadata' not in sdk


@pytest.mark.parametrize('fault', ['package', 'authorization', 'native'])
def test_all_execution_gates_precede_credentials_and_run_creation(tmp_path, monkeypatch, prepared, fault):
    plan, rows = deepcopy(prepared)
    monkeypatch.setattr(diagnostic.base, 'prepare', lambda **kw: (deepcopy(plan), rows))
    package = diagnostic.Package(tmp_path / 'package')
    package.write(root_thread_id='synthetic-root', independent_thread_id='synthetic-child')
    now = datetime.now(timezone.utc)
    auth = dict(version=diagnostic.base.AUTH_VERSION, authorized=True,
        user_instruction='OFFLINE fixture', plan_sha256=diagnostic.base.sha(diagnostic.base.options.canonical(plan)),
        budget=deepcopy(plan['budget']), head='f' * 40, ci_run='ci', issued_at=now.isoformat(),
        expires_at=(now + timedelta(hours=24)).isoformat())
    if fault == 'package':
        (package.directory / 'report-V2-initial/material.json').write_text('{}')
    elif fault == 'authorization':
        auth['budget'] = {}
    write_new_json(tmp_path / 'authorization.json', auth)
    monkeypatch.setattr(diagnostic.base, 'ROOT', tmp_path)
    monkeypatch.setattr(diagnostic.base, 'verify_public_ci', lambda ci: 'f' * 40)
    monkeypatch.setattr(diagnostic.base, 'require_unchanged_checkout', lambda head: None)
    class Reader:
        def __init__(self, *args): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(diagnostic.base, 'CodexReadOnlyClient', Reader)
    def native(*args):
        raise ValueError('fixture_native_unavailable')
    monkeypatch.setattr(diagnostic.base, 'verify_native_principals', native)
    def secret(*args):
        raise AssertionError('credentials_must_not_be_read')
    monkeypatch.setattr(diagnostic.base, 'load_role_settings', secret)
    args = NS(package=package.directory, authorization=tmp_path / 'authorization.json', ci_run='ci',
              codex_executable='OFFLINE_NOT_LAUNCHED', env_file='OFFLINE_NOT_READ')
    expected = {'package': 'sampling_package_material_changed',
                'authorization': 'semantic_authorization_invalid_or_expired',
                'native': 'fixture_native_unavailable'}[fault]
    with pytest.raises(ValueError, match=expected):
        diagnostic.base.run(args)
    assert not (tmp_path / 'data/runs/model_comparison' / plan['run_id']).exists()


def test_artifact_change_prevents_dispatch_and_wait(tmp_path, monkeypatch, prepared):
    plan, rows, fixtures = execution(tmp_path, monkeypatch, prepared)
    provider = fixtures.OfflineProvider()
    host = fixtures.OfflineNativeHost(plan, tmp_path)
    publish = diagnostic.runner.checkpoint.publish
    def corrupt(path, *args, **kwargs):
        pin = publish(path, *args, **kwargs)
        response = path.parent / 'response.json'
        response.write_bytes(response.read_bytes() + b' ')
        return pin
    monkeypatch.setattr(diagnostic.runner.checkpoint, 'publish', corrupt)
    result = diagnostic.runner.observe(tmp_path, plan, rows, provider, host.source,
                                       adjudicate=host.adjudicate)
    folder = tmp_path / 'report-V2-initial'
    assert result['first_deviation']['code'] == 'host_artifacts_response_sha256'
    assert len(provider.calls) == 1 and not host.turns
    assert not (folder / 'dispatch.txt').exists()
    assert not (folder / 'review-wait-start.json').exists()
