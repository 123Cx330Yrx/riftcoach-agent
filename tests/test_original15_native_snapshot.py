from types import SimpleNamespace

import pytest

import hashlib
import json

from scripts.original15_native_snapshot import ValidationReadSnapshot, wrap_validation, install


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
