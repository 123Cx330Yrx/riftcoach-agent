"""Archived-source scope and real Worker-executor first-input boundary, no IO."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import socket

import pytest

from app.evidence.publication import EvidencePublicationSources
from app.providers.secrets import SecretConfigurationError
from scripts.archived_product_inputs import (ArchivedProductInputs, ExistingProductSecrets,
    read_existing_flash_key)
from scripts.preflight_archived_product import preflight


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('archived input check attempted network access')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


@pytest.fixture
def archived(tmp_path):
    from scripts.check_native_contract_options import corrected_case3
    source = deepcopy(corrected_case3()[0].player_summary)
    source['player']['puuid_prefix'] = 'ARCHIVED_TEST_ID...'
    args = dict(puuid='ARCHIVED_TEST_ID_FULL', routing_region='asia',
        game_name=source['player']['game_name'], tag_line=source['player']['tag_line'],
        count=source['request']['count'], queue=source['request']['requested_queue'])
    projection = EvidencePublicationSources(now=datetime(2026, 11, 3, tzinfo=timezone.utc)).project(source, routing_region='asia')
    root = tmp_path/'archive'

    def save(name, value):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(value, ensure_ascii=True).encode()
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    pins = dict(summary_sha256=save('inputs/player_summary.json', source),
        bundle_sha256=save('evidence_bundle.json', projection.bundle.model_dump(mode='json')),
        source_intent_sha256=save('.continuation/session/operations/0001-intent.json',
            dict(kind='source', request=dict(method='build_by_puuid', arguments=args))))
    pins['manifest_sha256'] = save('evidence_publication_manifest.json', dict(
        summary={'sha256': pins['summary_sha256']},
        bundle={'sha256': pins['bundle_sha256'], 'bundle_digest': projection.bundle.digest},
        summary_digest=projection.summary_digest))
    return root, pins


def test_scope_and_caller_mutation_cannot_change_archived_source(archived):
    inputs = ArchivedProductInputs(archived[0], **archived[1])
    args = inputs.arguments
    original = inputs.build_by_puuid(**args)
    changed = inputs.build_by_puuid(**args)
    changed['player'].clear()
    assert inputs.build_by_puuid(**args) == original
    for key, value in [('count', 10), ('queue', None), ('puuid', 'OTHER'), ('routing_region', 'europe')]:
        with pytest.raises(ValueError, match='archived_request_scope_mismatch'):
            inputs.build_by_puuid(**{**args, key: value})
    with pytest.raises(ValueError, match='conversation_identity_required'):
        inputs.build(**args)


@pytest.mark.parametrize('name', ['inputs/player_summary.json', 'evidence_bundle.json',
    'evidence_publication_manifest.json', '.continuation/session/operations/0001-intent.json'])
def test_changed_archive_stops_before_execution(archived, name):
    path = archived[0]/name
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='archived_input_pin_mismatch'):
        ArchivedProductInputs(archived[0], **archived[1])


@pytest.mark.parametrize('kind', ['manifest', 'source_scope'])
def test_rehashed_cross_artifact_conflict_is_not_accepted(archived, kind):
    root, pins = archived
    pins = dict(pins)
    if kind == 'manifest':
        path, key = root/'evidence_publication_manifest.json', 'manifest_sha256'
        value = json.loads(path.read_bytes())
        value['summary_digest'] = '0'*64
    else:
        path, key = root/'.continuation/session/operations/0001-intent.json', 'source_intent_sha256'
        value = json.loads(path.read_bytes())
        value['request']['arguments']['count'] = 10
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    pins[key] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match='archived_source_binding'):
        ArchivedProductInputs(root, **pins)


def test_existing_secret_source_never_reads_riot_or_process_environment(tmp_path):
    path = tmp_path/'.env'
    path.write_text('RIOT_API_KEY=excluded\nLLM_API_KEY=model-only\nZHIPU_API_KEY=fallback\n', encoding='utf-8')
    reads = []
    source = ExistingProductSecrets(flash_reader=lambda: read_existing_flash_key(path),
        reviewer_reader=lambda: reads.append('reviewer') or 'review-only')
    now = datetime.now(timezone.utc)
    assert source.read(name='llm-api', now=now).value == 'model-only'
    with pytest.raises(SecretConfigurationError, match='product_secret_scope'):
        source.read(name='riot-api', now=now)
    assert not reads and source.read_names == ['llm-api']


def test_worker_executor_compiles_complete_first_request_without_transport(archived, tmp_path):
    inputs = ArchivedProductInputs(archived[0], **archived[1])
    source = ExistingProductSecrets(flash_reader=lambda: 'OFFLINE_FLASH', reviewer_reader=lambda: 'OFFLINE_SOL')
    result = preflight(inputs, root=tmp_path/'preflight', secret_source=source)
    assert result['stop_reason'] == 'session_model_boundary'
    assert result['effects'] == dict(model_requests=0, new_source_requests=0, persisted_sql_tasks=0)
    assert result['first_request']['max_output_tokens'] == 16384
    assert result['first_request']['timeout_seconds'] == 300
    assert result['first_request']['first_plus_full_review_tail'] <= 401920
    assert result['limits']['sql_lifecycle_verified'] is False
    assert not list((tmp_path/'preflight').rglob('attempt-*.json'))
    assert not list((tmp_path/'preflight').rglob('call-*.json'))
