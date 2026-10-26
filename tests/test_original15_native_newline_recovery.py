import pytest
import json

from scripts.original15_native_newline_recovery import digest, verify_bytes, install


def record(author, native):
    return dict(author_sha256=digest(author), native_final_sha256=digest(native))


def test_exact_recorded_terminal_lf():
    native = b'{"accepted":true}'
    verify_bytes(native + b'\n', native, record(native + b'\n', native))


@pytest.mark.parametrize('author,native', [
    (b'{"accepted":true}\n', b'{"accepted":false}'),
    (b'{"accepted":true}\n', b'{ "accepted":true}'),
    (b'{"accepted":true}\r\n', b'{"accepted":true}'),
    (b'{"accepted":true}\n\n', b'{"accepted":true}'),
    (b'{"accepted":true} ', b'{"accepted":true}'),
    (b'{"accepted":true}', b'{"accepted":true}'),
    (b'{"accepted":true}\n', b'{"accepted":true}\n'),
])
def test_rejects_every_other_byte_difference_even_with_matching_hashes(author, native):
    with pytest.raises(ValueError, match='terminal_lf_exception_mismatch'):
        verify_bytes(author, native, record(author, native))


@pytest.mark.parametrize('key', ['author_sha256', 'native_final_sha256'])
def test_rejects_changed_record_hash(key):
    native = b'{"accepted":true}'
    expected = record(native + b'\n', native)
    expected[key] = '0' * 64
    with pytest.raises(ValueError, match='terminal_lf_exception_mismatch'):
        verify_bytes(native + b'\n', native, expected)


@pytest.mark.parametrize('changed', ['checkpoint_sha256', 'binding', 'event_id', 'raw_event_sha256'])
def test_exception_never_covers_another_task_or_event(tmp_path, monkeypatch, changed):
    from scripts import reviewer_profile_batch as batch

    class Gate:
        def _validate(self, handle, submission):
            raise ValueError('batch_author_native_bytes_mismatch')

    monkeypatch.setattr(batch, 'ExactNativeGate', Gate)
    module = tmp_path / 'original15_native_newline_recovery.py'
    module.write_bytes(b'pinned test module')
    value = dict(version='original15-one-native-terminal-lf-recovery-v1',
                 launch_plan_sha256='plan', checkpoint_sha256='checkpoint',
                 binding={'key': 'facts-fresh'}, event_id='child/turn/final',
                 raw_event_sha256='raw-event')
    manifest = tmp_path / 'scope-4-facts-fresh-terminal-lf-recovery.json'
    manifest.write_text(json.dumps(value), encoding='utf-8')
    selected = dict(module_sha256=digest(module.read_bytes()),
                    manifest_sha256=digest(manifest.read_bytes()))
    install(tmp_path, dict(plan_sha256='plan', native_terminal_lf_recovery=selected))
    handle = dict(checkpoint_sha256='checkpoint', binding={'key': 'facts-fresh'})
    event = dict(event_id='child/turn/final', raw_event_sha256='raw-event')
    if changed in handle:
        handle[changed] = 'different'
    else:
        event[changed] = 'different'
    with pytest.raises(ValueError, match='batch_author_native_bytes_mismatch'):
        Gate()._validate(handle, {'independent': {'independent_source_event': event}})


def test_control_tampering_is_rechecked_on_every_validation(tmp_path, monkeypatch):
    from scripts import reviewer_profile_batch as batch

    class Gate:
        def _validate(self, handle, submission):
            return True

    monkeypatch.setattr(batch, 'ExactNativeGate', Gate)
    module = tmp_path / 'original15_native_newline_recovery.py'
    module.write_bytes(b'pinned test module')
    manifest = tmp_path / 'scope-4-facts-fresh-terminal-lf-recovery.json'
    manifest.write_text(json.dumps(dict(version='original15-one-native-terminal-lf-recovery-v1',
                                      launch_plan_sha256='plan')), encoding='utf-8')
    selected = dict(module_sha256=digest(module.read_bytes()),
                    manifest_sha256=digest(manifest.read_bytes()))
    install(tmp_path, dict(plan_sha256='plan', native_terminal_lf_recovery=selected))
    assert Gate()._validate({}, {}) is True
    manifest.write_bytes(manifest.read_bytes() + b' ')
    with pytest.raises(ValueError, match='terminal_lf_controls_changed'):
        Gate()._validate({}, {})
