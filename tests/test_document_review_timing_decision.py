"""Public fixtures only; fake-clock budget counterexamples, zero network."""
import json
import socket

import pytest

from scripts import audit_document_review_timing as timing


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Timing audit must never send network traffic')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def test_public_snapshot_rebuilds_and_preserves_censoring():
    result = timing.audit()
    assert timing.encoded(result) == (timing.ROOT / timing.OUTPUT).read_bytes()
    assert len(result['observed_calls']) == 6
    assert result['accounting']['known_tokens'] == 81642
    last = result['observed_calls'][-1]
    assert last['state'] == 'deadline' and last['last_event_ms'] == 299094
    assert last['input_tokens'] is None and last['output_tokens'] is None
    assert result['right_censored']['predicted_finish_s'] is None
    assert not result['right_censored']['causal_root_established']
    assert not result['execution_ready'] and result['actual_new_provider_calls'] == 0
    serialized = timing.encoded(result).decode('utf-8')
    assert 'reasoning_content' not in serialized and 'api_key' not in serialized
    assert '你是RiftCoach报告审查员' not in serialized


@pytest.mark.parametrize('fault', ['bytes', 'extra_file', 'seal_binding'])
def test_metadata_change_cannot_relabel_closed_unknown_call(fault):
    seal = timing.load_seal()
    value = json.loads((timing.ROOT / timing.CAPSULE).read_text(encoding='utf-8'))
    if fault == 'bytes':
        key = timing.FILES[-2]
        raw = json.loads(value['files'][key]); raw['output_tokens'] = 0
        value['files'][key] = json.dumps(raw)
    elif fault == 'extra_file':
        value['files']['transport/fabricated/result.json'] = '{}'
    else:
        value['seal_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='timing_metadata_'):
        timing.validate_metadata(value, seal)


def test_legacy_seal_raw_bytes_are_required(tmp_path):
    path = tmp_path / timing.SEAL
    path.parent.mkdir(parents=True)
    path.write_bytes((timing.ROOT / timing.SEAL).read_bytes().replace(b'\r\n', b'\n'))
    with pytest.raises(ValueError, match='timing_seal_bytes_changed'):
        timing.load_seal(tmp_path)


def test_explicit_export_rejects_changed_original(tmp_path):
    path = tmp_path / timing.FILES[0]
    path.parent.mkdir(parents=True)
    path.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='timing_original_changed'):
        timing.export_metadata(tmp_path)


def test_longer_request_cannot_reset_whole_task_time_or_release_unknown_reservation():
    seal = timing.load_seal()
    old = timing.budget_probe(seal, review_cap=300)
    proposal = timing.budget_probe(seal, review_cap=600)
    clipped = timing.budget_probe(seal, review_cap=600, spent_before_s=500)
    exhausted = timing.budget_probe(seal, review_cap=600, spent_before_s=900)
    assert old['error'] == 'stream_deadline' and old['unknown_reserved_tokens'] == 77868
    assert proposal['completed'] and proposal['elapsed_s'] == 525.517
    assert proposal['unknown_reserved_tokens'] == 0
    assert clipped['error'] == 'stream_deadline' and clipped['elapsed_s'] == 900
    assert clipped['issued'][-1]['timeout_s'] == 324.483
    assert clipped['unknown_reserved_tokens'] == 77868 and clipped['stopped']
    assert exhausted['error'] == 'timeout' and not exhausted['issued']
    assert exhausted['synthetic_calls'] == 0


def test_existing_transport_and_observation_refuse_time_only_override():
    result = timing.audit()
    blockers = result['integration_blockers']
    assert blockers['old_transport_600_refusal'] == 'stream_request_budget'
    assert blockers['old_observation_450s_refused']
    assert result['diagnostic_limits']['batch_active_seconds'] == 8400
    assert not result['diagnostic_limits']['independent_case_900s_wall_enforced']


def test_source_fingerprints_are_portable_but_evidence_fingerprints_remain_raw(tmp_path):
    path = tmp_path / 'example.py'
    path.write_bytes(b'one\r\ntwo\r\n')
    raw = timing.sha(path.read_bytes())
    expected = timing.source_sha(path)
    path.write_bytes(b'one\ntwo\n')
    assert expected == timing.source_sha(path)
    assert raw != timing.sha(path.read_bytes())


def test_frozen_decision_checks_archived_source_without_rewriting_history(tmp_path):
    output = tmp_path / timing.OUTPUT
    output.parent.mkdir(parents=True)
    output.write_bytes((timing.ROOT / timing.OUTPUT).read_bytes())
    source = timing.FROZEN_SOURCES[0]
    archive = tmp_path / timing.SOURCE_ARCHIVE / (source.replace('/', '__') + '.txt')
    archive.parent.mkdir(parents=True)
    archive.write_text('changed historical source', encoding='utf-8')
    with pytest.raises(ValueError, match='timing_archived_source_changed'):
        timing.decision_source_sha(tmp_path, source)
