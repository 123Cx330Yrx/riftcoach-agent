"""Real SQL/Worker with synthetic SSE: rejected content requires manual retry."""
from uuid import UUID

import pytest

from app.evaluation.sol_natural_session import tree
from app.persistence.task_continuations import PostgresTaskContinuations
from app.product import sol_contract as product
from app.product.protocol_failure_recovery import prepare, verify
from app.tasks.continuation import ContinuationError, ResumeContinuation
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, create, setup_worker


@pytest.fixture(params=['legacy', 'evidence_bound_v1'])
def rejected(continued_api, tmp_path, monkeypatch, request):
    owner, _, repo, _ = continued_api
    if request.param == 'legacy':
        task, run = create(owner); task = UUID(task)
    else:
        from app.tasks.service import ReviewTaskService, CreateReviewTaskCommand
        from app.product.recent_review import RecentReviewProductRequest
        from app.tasks.models import TaskPublicationMode
        created = ReviewTaskService(repository=repo).create(CreateReviewTaskCommand(
            owner_id='owner-1', idempotency_key='protocol-evidence',
            request=RecentReviewProductRequest(riot_id='DemoPlayer#TEST', routing_region='asia', focus='overall'),
            publication_mode=TaskPublicationMode.EVIDENCE_BOUND_V1))
        task, run = created.task.task_id, created.task.run_id
    make, _, _, calls = setup_worker(tmp_path, monkeypatch, repo, mode='protocol_unknown_preamble',
        contract=product, profile=product.WORKER_PROFILE)
    worker, _ = make(); outcome = worker.run_once()
    assert outcome.status.value == 'succeeded', repo.get_by_task_id(owner_id='owner-1', task_id=task).recovery_reason
    store = PostgresTaskContinuations(repo)
    ref = store.load(owner_id='owner-1', task_id=task)
    assert calls == [[200]] and ref['accounting']['retries'] == 0
    assert not repo.get_by_task_id(owner_id='owner-1', task_id=task).report_available
    parent = tmp_path/run
    return dict(task=task, run=run, store=store, repo=repo, parent=parent,
                root=tmp_path/'recovered', ref=ref, original=tree(parent), mode=request.param)


def recover(c):
    return prepare(parent_run=c['parent'], destination_root=c['root'], reference=c['ref'])


def adopt(c, path, sha, owner='owner-1'):
    return c['store'].recover_protocol_rejection(owner_id=owner, task_id=c['task'],
        proof_path=path, proof_sha256=sha, runs_root=str(c['root']))


def test_recovery_pauses_without_send_then_requires_explicit_retry(rejected, monkeypatch):
    c = rejected; path, sha = recover(c)
    verify(path, sha, runs_root=c['root'])
    with pytest.raises(ContinuationError, match='task_not_found'): adopt(c, path, sha, 'owner-2')
    assert adopt(c, path, sha)['status'] == 'recovery_required'
    assert adopt(c, path, sha)['replayed']
    ref = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert ref['accounting'] == c['ref']['accounting']
    with pytest.raises(ContinuationError, match='conflict'):
        c['store'].resume(owner_id='owner-1', task_id=c['task'], request_id='stale',
            command=ResumeContinuation(checkpoint_sha256=c['ref']['checkpoint_sha256']))
    c['store'].resume(owner_id='owner-1', task_id=c['task'], request_id='ordinary',
        command=ResumeContinuation(checkpoint_sha256=ref['checkpoint_sha256']))
    make, summary, factories, calls = setup_worker(c['root'], monkeypatch, c['repo'],
        contract=product, profile=product.WORKER_PROFILE)
    worker, _ = make(); assert worker.run_once().status.value == 'paused'
    paused = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert paused['pause_reason'] == 'session_protocol_awaiting_manual_retry'
    assert calls == [[]] and summary.reads == 0
    assert paused['accounting'] == c['ref']['accounting']
    assert all(not p.generator.requests for f in factories for p in f.providers.values())
    assert not c['repo'].get_by_task_id(owner_id='owner-1', task_id=c['task']).report_available
    c['store'].resume(owner_id='owner-1', task_id=c['task'], request_id='explicit-retry',
        command=ResumeContinuation(checkpoint_sha256=paused['checkpoint_sha256'], manual_retry=True))
    worker, _ = make(); assert worker.run_once().status.value == 'succeeded'
    assert calls == [[], [200, 200]] and summary.reads == 0
    assert all(not p.generator.requests for f in factories for p in f.providers.values())
    final = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert final['accounting']['retries'] == 1
    assert final['accounting']['requests_observed'] == c['ref']['accounting']['requests_observed']+2
    assert c['repo'].get_by_task_id(owner_id='owner-1', task_id=c['task']).report_available
    assert tree(c['parent']) == c['original']
    if c['mode'] == 'evidence_bound_v1':
        import sqlalchemy as sa
        from app.persistence.evidence_snapshot_record import EvidenceBundleSnapshotRecord
        with c['repo']._session_factory() as session:
            rows = session.scalars(sa.select(EvidenceBundleSnapshotRecord).where(
                EvidenceBundleSnapshotRecord.task_id == c['task']).order_by(EvidenceBundleSnapshotRecord.revision)).all()
            assert len(rows) == 2
            assert rows[0].refresh_id == 'publication-1'
            assert rows[1].refresh_id == 'publication-recovery-'+sha


@pytest.mark.parametrize('target', ['parent', 'archive', 'operations', 'proof'])
def test_tampered_recovery_not_adopted(rejected, target):
    c = rejected; path, sha = recover(c)
    victim = {'parent':c['parent']/'.continuation/session/terminal.json',
              'archive':c['root']/c['run']/'.continuation/protocol-parent.zip',
              'operations':next((c['root']/c['run']/'.continuation/session/operations').glob('*-result.json')),
              'proof':path}[target]
    victim.write_bytes(victim.read_bytes()+b' ')
    with pytest.raises(ContinuationError, match='invalid'): adopt(c, path, sha)
    assert c['store'].load(owner_id='owner-1', task_id=c['task'])['checkpoint_sha256'] == c['ref']['checkpoint_sha256']


def second_rejection(c, monkeypatch):
    path, sha = recover(c); adopt(c, path, sha)
    ref = c['store'].load(owner_id='owner-1', task_id=c['task'])
    c['store'].resume(owner_id='owner-1', task_id=c['task'], request_id='first-protocol-ordinary',
        command=ResumeContinuation(checkpoint_sha256=ref['checkpoint_sha256']))
    make, _, _, calls = setup_worker(c['root'], monkeypatch, c['repo'], mode='anonymous_rejected',
        contract=product, profile=product.WORKER_PROFILE)
    worker, _ = make(); assert worker.run_once().status.value == 'paused'
    ref = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert ref['pause_reason'] == 'session_protocol_awaiting_manual_retry'
    c['store'].resume(owner_id='owner-1', task_id=c['task'], request_id='first-protocol-retry',
        command=ResumeContinuation(checkpoint_sha256=ref['checkpoint_sha256'], manual_retry=True))
    worker, _ = make(); assert worker.run_once().status.value == 'succeeded'
    assert calls == [[], [200]]
    ref = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert ref['accounting']['retries'] == 1
    return dict(c, ref=ref, parent=c['root']/c['run'], root=c['root'].parent/'second-recovered',
                original=tree(c['root']/c['run']))


def test_second_recovery_preserves_both_failures_and_committed_retry(rejected, monkeypatch):
    first = rejected; c = second_rejection(first, monkeypatch)
    path, sha = recover(c); verify(path, sha, runs_root=c['root'])
    adopt(c, path, sha)
    assert adopt(c, path, sha)['replayed']
    ref = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert ref['protocol_recovery']['previous'] == c['ref']['protocol_recovery']
    c['store'].resume(owner_id='owner-1', task_id=c['task'], request_id='second-ordinary',
        command=ResumeContinuation(checkpoint_sha256=ref['checkpoint_sha256']))
    make, summary, factories, calls = setup_worker(c['root'], monkeypatch, c['repo'],
        contract=product, profile=product.WORKER_PROFILE)
    worker, _ = make(); assert worker.run_once().status.value == 'paused'
    paused = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert paused['pause_reason'] == 'session_protocol_awaiting_manual_retry'
    assert paused['accounting'] == c['ref']['accounting'] and calls == [[]] and summary.reads == 0
    assert all(not p.generator.requests for f in factories for p in f.providers.values())
    assert not c['repo'].get_by_task_id(owner_id='owner-1', task_id=c['task']).report_available
    assert tree(first['parent']) == first['original'] and tree(c['parent']) == c['original']
    assert tree(c['parent']/'.continuation/session/operations') == tree(c['root']/c['run']/'.continuation/session/operations')


@pytest.mark.parametrize('target', ['history_archive', 'history_marker', 'prior_result'])
def test_second_recovery_rejects_history_tampering(rejected, monkeypatch, target):
    c = second_rejection(rejected, monkeypatch)
    path, sha = recover(c)
    base = c['root']/c['run']/'.continuation'
    if target == 'history_archive': victim = base/'protocol-history-1.zip'
    elif target == 'history_marker': victim = base/'session/protocol-recovery.json'
    else: victim = next((base/'session/operations').glob('*-result.json'))
    victim.write_bytes(victim.read_bytes()+b' ')
    with pytest.raises(ContinuationError, match='invalid'): adopt(c, path, sha)
    assert c['store'].load(owner_id='owner-1', task_id=c['task']) == c['ref']
