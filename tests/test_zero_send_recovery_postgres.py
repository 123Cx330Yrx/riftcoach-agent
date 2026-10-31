"""Real SQL and Worker, scripted HTTP: preserve a failed pre-send retry."""
import json
from uuid import UUID

import pytest

from app.evaluation.sol_natural_session import CandidateSession, tree
from app.persistence.task_continuations import PostgresTaskContinuations
from app.product import sol_contract as product
from app.product.zero_send_recovery import prepare, verify
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
            owner_id='owner-1', idempotency_key='zero-send-evidence',
            request=RecentReviewProductRequest(riot_id='DemoPlayer#TEST', routing_region='asia', focus='overall'),
            publication_mode=TaskPublicationMode.EVIDENCE_BOUND_V1))
        task, run = created.task.task_id, created.task.run_id
    make, _, _, calls = setup_worker(tmp_path, monkeypatch, repo, statuses=(524,),
        contract=product, profile=product.WORKER_PROFILE)
    worker, _ = make(); assert worker.run_once().status.value == 'paused'
    store = PostgresTaskContinuations(repo)
    before = store.load(owner_id='owner-1', task_id=task)
    store.resume(owner_id='owner-1', task_id=task, request_id='manual',
        command=ResumeContinuation(checkpoint_sha256=before['checkpoint_sha256'], manual_retry=True))
    operation = CandidateSession.operation
    def fail_before_intent(self, kind, request, action):
        if kind == 'model' and not (self.root/'operations'/f'{self.cursor+1:04d}-intent.json').exists():
            raise PermissionError('scripted outer guard lock failure')
        return operation(self, kind, request, action)
    with monkeypatch.context() as patch:
        patch.setattr(CandidateSession, 'operation', fail_before_intent)
        worker, _ = make(); assert worker.run_once().status.value == 'succeeded'
    ref = store.load(owner_id='owner-1', task_id=task)
    assert calls == [[524], []] and ref['accounting']['retries'] == 1
    parent = tmp_path/run
    return dict(task=task, run=run, store=store, repo=repo, parent=parent,
                root=tmp_path/'recovered', ref=ref, baseline=before['checkpoint_sha256'], original=tree(parent),
                mode=request.param)


def recover(c):
    return prepare(parent_run=c['parent'], destination_root=c['root'],
                   reference=c['ref'], baseline_sha256=c['baseline'])


def adopt(c, path, sha, owner='owner-1'):
    return c['store'].recover_zero_send_rejection(owner_id=owner, task_id=c['task'],
        proof_path=path, proof_sha256=sha, runs_root=str(c['root']))


def test_recovery_preserves_retry_and_replays_to_publication(rejected, monkeypatch):
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
    worker, _ = make(); assert worker.run_once().status.value == 'succeeded'
    assert calls == [[200, 200]] and summary.reads == 0
    assert all(not p.generator.requests for f in factories for p in f.providers.values())
    final = c['store'].load(owner_id='owner-1', task_id=c['task'])
    assert final['accounting']['retries'] == 1
    assert final['accounting']['unknown_token_reservation'] == c['ref']['accounting']['unknown_token_reservation']
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
              'archive':c['root']/c['run']/'.continuation/zero-send-parent.zip',
              'operations':next((c['root']/c['run']/'.continuation/session/operations').glob('*-result.json')),
              'proof':path}[target]
    victim.write_bytes(victim.read_bytes()+b' ')
    with pytest.raises(ContinuationError, match='invalid'): adopt(c, path, sha)
    assert c['store'].load(owner_id='owner-1', task_id=c['task'])['checkpoint_sha256'] == c['ref']['checkpoint_sha256']


def test_baseline_must_end_exactly_before_one_retry(rejected):
    c = rejected
    with pytest.raises(ValueError, match='not_single_retry'):
        prepare(parent_run=c['parent'], destination_root=c['root'], reference=c['ref'],
                baseline_sha256=c['ref']['checkpoint_sha256'])
