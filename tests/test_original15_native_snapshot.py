from types import SimpleNamespace

import pytest

import hashlib
import json

from scripts.original15_native_snapshot import (
    ValidationReadSnapshot, wrap_validation, wrap_case_replay,
    install, install_case_replay,
)


class Client:
    def __init__(self):
        self.calls = []
        self.value = {'data': [{'id': 'real-native-final', 'text': 'original'}]}
        self.failure = False

    def request(self, method, params):
        self.calls.append((method, params))
        if self.failure:
            raise ValueError('native_unavailable')
        return self.value

    def read_collaboration_dispatch(self, *args):
        return 'original-reader'


def test_only_identical_read_method_and_parameters_share_a_response():
    client = Client()
    snapshot = ValidationReadSnapshot(client)
    params = dict(threadId='child', limit=50, itemsView='full')
    first = snapshot.request('thread/turns/list', params)
    first['data'][0]['text'] = 'mutated-copy'
    assert snapshot.request('thread/turns/list', dict(reversed(list(params.items())))) == client.value
    snapshot.request('thread/turns/list', dict(params, cursor='next'))
    snapshot.request('thread/read', params)
    snapshot.request('thread/resume', params)
    snapshot.request('thread/resume', params)
    assert len(client.calls) == 5
    assert snapshot.read_collaboration_dispatch() == 'original-reader'


def test_each_validation_reads_live_again_and_runs_both_existing_checks():
    client = Client()
    gate = SimpleNamespace(event_source=SimpleNamespace(client=client))
    checks = []
    def previous(self, handle, submission):
        for check in ('provenance', 'bytes'):
            checks.append(check)
            value = self.event_source.client.request('thread/read', {'threadId': 'child'})
            assert value['data'][0]['text'] == submission
        return True
    verified = []
    validate = wrap_validation(previous, lambda: verified.append(True))
    assert validate(gate, {}, 'original')
    assert gate.event_source.client is client
    client.value['data'][0]['text'] = 'changed-real-native'
    assert validate(gate, {}, 'changed-real-native')
    assert len(client.calls) == 2 and len(verified) == 2
    assert checks == ['provenance', 'bytes', 'provenance', 'bytes']


def test_read_failure_never_falls_back_to_a_previous_validation():
    client = Client()
    gate = SimpleNamespace(event_source=SimpleNamespace(client=client))
    def previous(self, *_):
        return self.event_source.client.request('thread/read', {'threadId': 'child'})
    validate = wrap_validation(previous, lambda: None)
    assert validate(gate, {}, {}) == client.value
    client.failure = True
    with pytest.raises(ValueError, match='native_unavailable'):
        validate(gate, {}, {})
    assert gate.event_source.client is client and len(client.calls) == 2


def test_original_rejection_restores_client_and_does_not_become_acceptance():
    client = Client()
    gate = SimpleNamespace(event_source=SimpleNamespace(client=client))
    def previous(self, *_):
        self.event_source.client.request('thread/read', {'threadId': 'child'})
        raise ValueError('batch_author_native_bytes_mismatch')
    validate = wrap_validation(previous, lambda: None)
    with pytest.raises(ValueError, match='batch_author_native_bytes_mismatch'):
        validate(gate, {}, {})
    assert gate.event_source.client is client


def test_control_failure_prevents_reads_and_validation():
    client = Client()
    gate = SimpleNamespace(event_source=SimpleNamespace(client=client))
    def verify():
        raise ValueError('original15_native_snapshot_controls_changed')
    validate = wrap_validation(lambda *_: pytest.fail('must not validate'), verify)
    with pytest.raises(ValueError, match='controls_changed'):
        validate(gate, {}, {})
    assert client.calls == [] and gate.event_source.client is client


def test_case_replay_runs_every_check_but_reads_identical_pages_once():
    client = Client()
    events = SimpleNamespace(client=client)
    gate = SimpleNamespace(event_source=events)
    checks = []
    def previous_validation(self, handle, expected):
        for kind in ('provenance', 'native_bytes', 'dispatch'):
            checks.append((handle, kind))
            value = self.event_source.client.request('thread/turns/list', {'threadId': 'child'})
            assert value == expected
        assert self.event_source.client.read_collaboration_dispatch() == 'original-reader'
        return True
    validate = wrap_validation(previous_validation, lambda: None)
    def original_replay(plan, pin, source, key):
        assert source is events
        return [validate(gate, handle, client.value) for handle in ('a', 'b', 'c')]
    replay = wrap_case_replay(original_replay, lambda: None)
    assert replay({}, 'pin', events, 'case1') == [True] * 3
    assert len(client.calls) == 1 and len(checks) == 9
    assert events.client is client
    client.value = {'data': [{'id': 'real-native-final', 'text': 'changed'}]}
    assert replay({}, 'pin', events, 'case2') == [True] * 3
    assert len(client.calls) == 2 and len(checks) == 18


@pytest.mark.parametrize('failure', ['read', 'validator', 'post_controls'])
def test_case_replay_failure_restores_client_and_does_not_cache_next_case(failure):
    client = Client()
    events = SimpleNamespace(client=client)
    checked = []
    def verify():
        checked.append(True)
        if failure == 'post_controls' and len(checked) == 2:
            raise ValueError('changed_controls')
    def original_replay(plan, pin, source, key):
        source.client.request('thread/read', {'threadId': 'child'})
        if failure == 'validator':
            raise ValueError('changed_author_bytes')
        return True
    replay = wrap_case_replay(original_replay, verify)
    client.failure = failure == 'read'
    with pytest.raises(ValueError):
        replay({}, 'pin', events, 'case1')
    assert events.client is client
    client.failure = False
    value = wrap_case_replay(lambda p, n, e, k: e.client.request('thread/read', {'threadId': 'child'}), lambda: None)
    assert value({}, 'pin', events, 'case2') == client.value
    assert len(client.calls) == 2


def test_case_replay_cannot_bypass_controls_or_nest_a_validation_snapshot():
    events = SimpleNamespace(client=Client())
    def deny():
        raise ValueError('changed_controls')
    replay = wrap_case_replay(lambda *a: pytest.fail('must not replay'), deny)
    with pytest.raises(ValueError, match='changed_controls'):
        replay({}, 'pin', events, 'case')
    assert events.client.calls == []
    events.client = ValidationReadSnapshot(events.client)
    replay = wrap_case_replay(lambda *a: pytest.fail('must not replay'), lambda: None)
    with pytest.raises(ValueError, match='nested_replay'):
        replay({}, 'pin', events, 'case')


@pytest.mark.parametrize('changed', ['module', 'manifest'])
def test_case_snapshot_installed_controls_rechecked(tmp_path, monkeypatch, changed):
    from scripts import sol_original15_launch as launch
    module = tmp_path/'original15_native_snapshot.py'
    module.write_bytes(b'fixed module')
    manifest = tmp_path/'case-manifest.json'
    manifest.write_text(json.dumps(dict(version='original15-one-case-replay-read-snapshot-v1',
        plan_sha256='plan', scope='one_read_only_case_replay', cross_case_cache=False,
        cross_boundary_cache=False, existing_validators_unchanged=True,
        collaboration_file_reader_unchanged=True)), encoding='utf-8')
    config = dict(plan_sha256='plan', native_case_replay_snapshot=dict(file=manifest.name,
        sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        module_sha256=hashlib.sha256(module.read_bytes()).hexdigest()))
    monkeypatch.setattr(launch, 'replay_case', lambda *args: True)
    install_case_replay(tmp_path, config)
    events = SimpleNamespace(client=Client())
    assert launch.replay_case({}, 'pin', events, 'case') is True
    target = module if changed == 'module' else manifest
    target.write_bytes(target.read_bytes() + b' ')
    with pytest.raises(ValueError, match='controls_changed'):
        launch.replay_case({}, 'pin', events, 'case')


@pytest.mark.parametrize('changed', ['module', 'manifest'])
def test_installed_controls_are_rechecked_before_every_validation(tmp_path, monkeypatch, changed):
    from scripts import reviewer_profile_batch as batch
    class Gate:
        def _validate(self, *_):
            return True
    monkeypatch.setattr(batch, 'ExactNativeGate', Gate)
    module = tmp_path/'original15_native_snapshot.py'
    module.write_bytes(b'fixed module')
    manifest = tmp_path/'manifest.json'
    manifest.write_text(json.dumps(dict(version='original15-native-validation-snapshot-v1',
        plan_sha256='plan', scope='one_validation_call', cross_validation_cache=False,
        existing_validators_unchanged=True, collaboration_file_reader_unchanged=True)), encoding='utf-8')
    config = dict(plan_sha256='plan', native_validation_snapshot=dict(file=manifest.name,
        sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        module_sha256=hashlib.sha256(module.read_bytes()).hexdigest()))
    install(tmp_path, config)
    gate = Gate()
    gate.event_source = SimpleNamespace(client=Client())
    assert gate._validate({}, {}) is True
    target = module if changed == 'module' else manifest
    target.write_bytes(target.read_bytes() + b' ')
    with pytest.raises(ValueError, match='controls_changed'):
        gate._validate({}, {})
