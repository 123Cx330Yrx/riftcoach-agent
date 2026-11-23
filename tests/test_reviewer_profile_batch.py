"""Injected engineering state-machine fixtures, never native/semantic evidence."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import socket

import pytest

from scripts import host_review_task_checkpoint as checkpoint
from scripts.codex_review_event_source import review_task
from scripts import prepare_reviewer_profile_screen as screen
from scripts import reviewer_profile_batch as batch_module
from scripts.reviewer_responses_process import write_json
from scripts.reviewer_responses_transport import TOOL, build_wire, digest


KEYS = ('r01-facts', 'r01-completion', 'r02-facts', 'r02-completion')
USAGE = dict(input_tokens=125, output_tokens=70, total_tokens=195,
             cached_input_tokens=20, reasoning_tokens=30)
REVIEW = dict(score=100, verdict='pass', issues=[], issue_resolutions=[], advisories=[], repairs=[])


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(path):
    """Include timestamps so an identical-content rewrite is not read-only."""
    return {p.relative_to(path).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in path.rglob('*') if p.is_file()}


class FixtureSource:
    """Deliberately non-native authority used only in these engineering tests."""
    def __init__(self):
        self.decisions = {}
        self.handles = []
        self.replayed = []

    def fetch(self, **kwargs):
        raise AssertionError('FakeGate must not be treated as a native event source')


class FakeGate:
    """Persist and reread fixture decisions; never certify their provenance."""
    def __init__(self, plan, workspace, event_source):
        self.plan, self.workspace, self.source = plan, workspace, event_source

    def publish(self, folder, bound, kind, material):
        folder = Path(folder)
        folder.mkdir(exist_ok=False)
        write_json(folder / 'material.json', material)
        write_json(folder / 'independent-task.json', json.loads(review_task(
            bound, 'Engineering fixture only; no native or semantic certification.')))
        pin = checkpoint.publish(folder / 'task-checkpoint.json', folder / 'independent-task.json',
                                 self.plan['review_principals']['independent']['principal_id'])
        (folder / 'dispatch.txt').write_text('ENGINEERING FIXTURE ONLY', encoding='utf-8')
        handle = dict(folder=str(folder), binding=deepcopy(bound), kind=kind,
                      material_sha256=sha(folder / 'material.json'), checkpoint_sha256=pin,
                      task_sha256=sha(folder / 'independent-task.json'))
        self.source.handles.append(handle)
        return handle

    def submit(self, handle, primary_decision, event_id):
        decision = self.source.decisions[event_id]
        write_json(Path(handle['folder']) / 'submission.json', dict(
            fixture_only=True, native_review_certified=False, event_id=event_id,
            primary=primary_decision, independent=deepcopy(decision)))
        return self.replay(handle)

    def replay(self, handle):
        self.source.replayed.append(handle['binding']['key'])
        path = Path(handle['folder']) / 'submission.json'
        value = json.loads(path.read_text(encoding='utf-8'))
        if self.source.decisions.get(value['event_id']) != value['independent']:
            raise ValueError('fixture_external_review_changed')
        assert value['fixture_only'] and not value['native_review_certified']
        return value['primary']['accepted'] and value['independent']['accepted']


class Sender:
    """Write the actual supervisor artifact shapes, without model or HTTP IO."""
    def __init__(self, *, ok=True, usage=USAGE, code='ok', state=None):
        self.calls = []
        self.ok, self.usage, self.code, self.state = ok, usage, code, state

    def __call__(self, business, profile, directory, timeout_s):
        directory = Path(directory)
        key = next(key for key in KEYS if json.loads(
            (screen.PACKAGE / 'requests' / f'{key}.json').read_text(encoding='utf-8')) == business)
        self.calls.append((key, directory, timeout_s))
        directory.mkdir(parents=True, exist_ok=False)
        write_json(directory / 'request.json', business)
        write_json(directory / 'profile.json', dict(**asdict(profile), reasoning_effort='high',
            api='responses', max_output_tokens=32768, max_retries=0, timeout_s=timeout_s,
            group_verified=False, upstream_identity_verified=False))
        if self.usage is not None:
            write_json(directory / 'usage.json', self.usage)
        if self.state != 'not_sent':
            write_json(directory / 'worker-result.json', dict(ok=self.ok, code=self.code,
                usage=self.usage, public_tool_call=dict(id='fc_1', call_id='call_1', name=TOOL,
                    arguments=json.dumps(REVIEW)), business_validated=self.ok,
                semantic_approval=False, upstream_identity_verified=False))
            observation = directory / 'observation'
            observation.mkdir()
            write_json(observation / 'observation.json', dict(schema_version='stream-observation-v1',
                body_free=True, http_requests=1, response_status=200, eof=True, closed=True,
                exception_type=None))
        receipt = dict(version='research-responses-single-call-v1', ok=self.ok, code=self.code,
            request_sha256=digest(business), wire_sha256=digest(build_wire(business)),
            profile=asdict(profile), usage=self.usage,
            usage_state=self.state or ('known' if self.usage is not None else 'unknown'),
            usage_conflict=False, conflicting_worker_usage=None,
            http_requests=0 if self.state == 'not_sent' else 1,
            reaped=True, worker_exit=None if self.state == 'not_sent' else 0,
            elapsed_s=1.0, semantic_approval=False,
            usage_basis='channel_reported_unverified_upstream', group_verified=False,
            upstream_identity_verified=False, qualified=False)
        write_json(directory / 'receipt.json', receipt)
        return receipt


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('batch engineering test attempted network')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def setup_batch(tmp_path):
    operator = tmp_path / 'operator'
    plan = batch_module.prepare(operator, group='GPT-pro', primary='primary-test', independent='independent-test')
    source = FixtureSource()
    batch = batch_module.ScreenBatch.create(plan, source, gate_factory=FakeGate)
    return operator, source, batch


def approve(batch, source, *, accepted=True):
    handle = source.handles[-1]
    event_id = f'fixture-event-{len(source.decisions) + 1}'
    decision = dict(kind='opinion', reviewer='primary-test',
        material_sha256=handle['material_sha256'], source_review='ENGINEERING FIXTURE ONLY',
        accepted=accepted, defects=[] if accepted else [dict(kind='wrong_correction', detail='fixture defect')],
        compatibility=None, actual_report_checked=True, report_assessment=None)
    source.decisions[event_id] = dict(accepted=accepted, fixture_only=True)
    return batch.submit_review(decision, event_id)


def load(operator, pin, source):
    return batch_module.ScreenBatch.load(operator, pin, source, gate_factory=FakeGate)


def test_create_is_offline_and_starts_with_fixed_first_request(setup_batch):
    operator, source, batch = setup_batch
    value = batch.status()
    assert value['phase'] == 'ready' and value['next_key'] == KEYS[0]
    assert value['calls'] == value['known_tokens'] == value['unknown_reserved_tokens'] == 0
    assert not source.handles and not source.replayed
    assert len(batch.checkpoint_sha) == 64


def test_each_send_is_one_request_and_requires_review_before_next(setup_batch):
    _, source, batch = setup_batch
    sender = Sender()
    batch.send_next(sender)
    assert [row[0] for row in sender.calls] == [KEYS[0]]
    assert batch.status()['phase'] == 'awaiting_review'
    assert batch.status()['known_tokens'] == USAGE['total_tokens']
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1
    approve(batch, source)
    assert batch.status()['phase'] == 'ready' and batch.status()['next_key'] == KEYS[1]
    batch.send_next(sender)
    assert [row[0] for row in sender.calls] == list(KEYS[:2])


def test_exact_four_calls_and_reviews_never_allow_fifth(setup_batch):
    _, source, batch = setup_batch
    sender = Sender()
    for index, key in enumerate(KEYS, 1):
        assert batch.status()['next_key'] == key
        batch.send_next(sender)
        assert len(sender.calls) == index and batch.status()['phase'] == 'awaiting_review'
        approve(batch, source)
    result = batch.status()
    assert result['phase'] == 'closed' and result['calls'] == 4
    assert result['known_tokens'] == 4 * USAGE['total_tokens']
    assert result['unknown_reserved_tokens'] == 0
    assert result['qualified'] is False and result['publication_allowed'] is False
    assert [row[0] for row in sender.calls] == list(KEYS)
    assert all(0 < row[2] <= 300 for row in sender.calls)
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 4


@pytest.mark.parametrize('code', ['cancelled', 'deadline_exceeded', 'sdk_or_stream_failed'])
def test_failed_unknown_call_closes_and_keeps_full_reservation(setup_batch, code):
    _, source, batch = setup_batch
    sender = Sender(ok=False, usage=None, code=code)
    batch.send_next(sender)
    value = batch.status()
    assert value['phase'] == 'closed' and value['calls'] == 1
    assert value['known_tokens'] == 0 and value['unknown_reserved_tokens'] == 64000 + 32768
    assert not source.handles
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1


def test_failure_with_known_usage_closes_but_keeps_tokens(setup_batch):
    _, _, batch = setup_batch
    sender = Sender(ok=False, code='business_contract_invalid')
    batch.send_next(sender)
    value = batch.status()
    assert value['phase'] == 'closed' and value['known_tokens'] == USAGE['total_tokens']
    assert value['unknown_reserved_tokens'] == 0


def test_not_sent_cancellation_does_not_become_unknown_spend(setup_batch):
    _, _, batch = setup_batch
    sender = Sender(ok=False, usage=None, code='cancelled', state='not_sent')
    batch.send_next(sender)
    value = batch.status()
    assert value['phase'] == 'closed'
    assert value['known_tokens'] == value['unknown_reserved_tokens'] == 0
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1


def test_before_send_failure_never_creates_claim_or_calls_sender(setup_batch):
    operator, _, batch = setup_batch
    sender = Sender()
    before = set(tree(operator))

    def stop():
        raise ValueError('fixture preflight rejected')

    with pytest.raises(ValueError):
        batch.send_next(sender, before_send=stop)
    value = batch.status()
    assert not sender.calls and value['phase'] == 'closed'
    assert value['calls'] == value['known_tokens'] == value['unknown_reserved_tokens'] == 0
    assert not any('claim' in name for name in set(tree(operator)) - before)


def test_sender_failure_after_claim_cannot_be_retried(setup_batch):
    operator, source, batch = setup_batch
    attempts = []

    def crashed(business, profile, directory, timeout_s):
        attempts.append(directory)
        Path(directory).mkdir(parents=True, exist_ok=False)
        raise OSError('fixture crash after durable claim')

    batch.send_next(crashed)
    assert batch.status()['phase'] == 'closed'
    restored = load(operator, batch.checkpoint_sha, source)
    with pytest.raises(ValueError):
        restored.send_next(crashed)
    assert len(attempts) == 1


def test_repeated_load_and_status_are_read_only(setup_batch):
    operator, source, batch = setup_batch
    batch.send_next(Sender())
    pin = batch.checkpoint_sha
    before = tree(operator)
    first = load(operator, pin, source)
    second = load(operator, pin, source)
    assert first.status() == second.status() == batch.status()
    assert first.status()['phase'] == 'awaiting_review'
    assert tree(operator) == before


def test_load_replays_saved_judgments_against_external_source(setup_batch):
    operator, source, batch = setup_batch
    batch.send_next(Sender())
    approve(batch, source)
    source.replayed.clear()
    restored = load(operator, batch.checkpoint_sha, source)
    assert source.replayed and restored.status()['phase'] == 'ready'
    source.decisions.clear()  # The source can no longer substantiate the judgment.
    with pytest.raises(ValueError):
        load(operator, batch.checkpoint_sha, source)


def test_semantic_rejection_closes_instead_of_buying_next(setup_batch):
    _, source, batch = setup_batch
    sender = Sender()
    batch.send_next(sender)
    approve(batch, source, accepted=False)
    assert batch.status()['phase'] == 'closed'
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1


def test_extra_uncheckpointed_file_blocks_recovery_without_mutating_it(setup_batch):
    operator, source, batch = setup_batch
    pin = batch.checkpoint_sha
    (operator / 'unexpected.json').write_text('{}', encoding='utf-8')
    before = tree(operator)
    with pytest.raises(ValueError, match='batch_uncheckpointed_evidence'):
        load(operator, pin, source)
    assert tree(operator) == before


def test_orphaned_real_claim_is_not_reissued_or_silently_checkpointed(setup_batch):
    operator, source, batch = setup_batch
    sender = Sender()
    batch.send_next(sender)
    claim = operator / 'claims' / '00-r01-facts.json'
    assert claim.is_file()

    orphan = operator.parent / 'orphan'
    plan = batch_module.prepare(orphan, group='GPT-pro', primary='primary-test', independent='independent-test')
    stranded = batch_module.ScreenBatch.create(plan, source, gate_factory=FakeGate)
    pin = stranded.checkpoint_sha
    (orphan / 'claims').mkdir(exist_ok=True)
    (orphan / 'claims' / claim.name).write_bytes(claim.read_bytes())
    before = tree(orphan)
    with pytest.raises(ValueError, match='batch_uncheckpointed_evidence'):
        load(orphan, pin, source)
    with pytest.raises(ValueError):
        stranded.send_next(sender)
    assert tree(orphan) == before and len(sender.calls) == 1


@pytest.mark.parametrize('filename', ['request.json', 'receipt.json', 'worker-result.json'])
def test_tampering_with_saved_call_blocks_recovery(setup_batch, filename):
    operator, source, batch = setup_batch
    sender = Sender()
    batch.send_next(sender)
    path = sender.calls[0][1] / filename
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        load(operator, batch.checkpoint_sha, source)
    assert len(sender.calls) == 1


def test_stale_checkpoint_cannot_authorize_later_evidence(setup_batch):
    operator, source, batch = setup_batch
    old = batch.checkpoint_sha
    batch.send_next(Sender())
    assert batch.checkpoint_sha != old
    with pytest.raises(ValueError):
        load(operator, old, source)


def test_existing_operator_directory_cannot_be_recreated(setup_batch):
    operator, source, _ = setup_batch
    before = tree(operator)
    with pytest.raises((ValueError, FileExistsError)):
        plan = batch_module.prepare(operator, group='GPT-pro', primary='primary-test', independent='independent-test')
        batch_module.ScreenBatch.create(plan, source, gate_factory=FakeGate)
    assert tree(operator) == before


def test_two_loaded_controllers_cannot_send_same_slot_twice(setup_batch):
    operator, source, batch = setup_batch
    other = load(operator, batch.checkpoint_sha, source)
    sender = Sender()
    batch.send_next(sender)
    with pytest.raises(ValueError):
        other.send_next(sender)
    assert len(sender.calls) == 1


def test_prior_receipt_tamper_prevents_next_send_on_existing_object(setup_batch):
    _, source, batch = setup_batch
    sender = Sender()
    batch.send_next(sender)
    approve(batch, source)
    receipt = sender.calls[0][1] / 'receipt.json'
    receipt.write_bytes(receipt.read_bytes() + b' ')
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1


@pytest.mark.parametrize('usage', [
    dict(input_tokens=64001, output_tokens=1, total_tokens=64002, cached_input_tokens=0, reasoning_tokens=0),
    dict(input_tokens=1, output_tokens=32769, total_tokens=32770, cached_input_tokens=0, reasoning_tokens=0),
])
def test_success_claim_cannot_override_per_call_token_caps(setup_batch, usage):
    _, source, batch = setup_batch
    sender = Sender(usage=usage)
    batch.send_next(sender)
    assert batch.status()['phase'] == 'closed'
    assert batch.status()['known_tokens'] == usage['total_tokens']
    assert not source.handles
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1


def test_four_maximum_sized_calls_exactly_fill_shared_token_budget(setup_batch):
    _, source, batch = setup_batch
    usage = dict(input_tokens=64000, output_tokens=32768, total_tokens=96768,
                 cached_input_tokens=0, reasoning_tokens=32768)
    sender = Sender(usage=usage)
    for _ in KEYS:
        batch.send_next(sender)
        assert batch.status()['phase'] == 'awaiting_review'
        approve(batch, source)
    value = batch.status()
    assert value['phase'] == 'closed' and value['calls'] == 4
    assert value['known_tokens'] == 387072 and value['unknown_reserved_tokens'] == 0
    assert len(sender.calls) == 4


@pytest.mark.parametrize('field', ['request_sha256', 'wire_sha256', 'profile'])
def test_success_receipt_with_wrong_request_or_profile_binding_closes(setup_batch, field):
    _, source, batch = setup_batch
    sender = Sender()

    def mismatched(*args, **kwargs):
        receipt = sender(*args, **kwargs)
        receipt[field] = ({**receipt[field], 'group': 'GPT-plus'} if field == 'profile' else '0' * 64)
        path = sender.calls[-1][1] / 'receipt.json'
        path.write_text(json.dumps(receipt), encoding='utf-8')
        return receipt

    batch.send_next(mismatched)
    assert batch.status()['phase'] == 'closed' and not source.handles
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1


def test_receipt_storage_failure_does_not_erase_saved_known_usage(setup_batch):
    _, _, batch = setup_batch
    sender = Sender()

    def failed_storage(*args, **kwargs):
        receipt = sender(*args, **kwargs)
        (sender.calls[-1][1] / 'receipt.json').unlink()
        return {**receipt, 'ok': False, 'code': 'receipt_write_failed'}

    batch.send_next(failed_storage)
    value = batch.status()
    assert value['phase'] == 'closed'
    assert value['known_tokens'] == USAGE['total_tokens']
    assert value['unknown_reserved_tokens'] == 0
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 1


def test_sender_cannot_reseal_a_modified_previous_receipt(setup_batch):
    _, source, batch = setup_batch
    sender = Sender()
    batch.send_next(sender)
    approve(batch, source)
    original_receipt = sender.calls[0][1] / 'receipt.json'

    def changes_previous(*args, **kwargs):
        result = sender(*args, **kwargs)
        original_receipt.write_bytes(original_receipt.read_bytes() + b' ')
        return result

    with pytest.raises(ValueError):
        batch.send_next(changes_previous)
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 2


def test_sender_cannot_add_a_legally_named_file_to_a_finished_slot(setup_batch):
    _, source, batch = setup_batch
    sender = Sender()
    batch.send_next(sender)
    approve(batch, source)
    old_extra = sender.calls[0][1] / 'observation' / 'observation.tmp'

    def adds_to_previous(*args, **kwargs):
        result = sender(*args, **kwargs)
        old_extra.write_text('{}', encoding='utf-8')
        return result

    with pytest.raises(ValueError):
        batch.send_next(adds_to_previous)
    with pytest.raises(ValueError):
        batch.send_next(sender)
    assert len(sender.calls) == 2


def test_usage_recovery_cannot_attribute_a_different_profile_to_this_call(setup_batch):
    _, _, batch = setup_batch
    sender = Sender()

    def wrong_profile(*args, **kwargs):
        receipt = sender(*args, **kwargs)
        directory = sender.calls[-1][1]
        profile = json.loads((directory / 'profile.json').read_text())
        profile['group'] = 'GPT-plus'
        (directory / 'profile.json').write_text(json.dumps(profile), encoding='utf-8')
        return receipt

    batch.send_next(wrong_profile)
    value = batch.status()
    assert value['phase'] == 'closed' and value['known_tokens'] == 0
    assert value['unknown_reserved_tokens'] == 96768
