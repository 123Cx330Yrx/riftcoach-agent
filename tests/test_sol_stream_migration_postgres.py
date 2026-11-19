"""Synthetic legacy receipts through real SQL and Worker; never paid requests."""
import json
from uuid import UUID

import pytest

from app.evaluation.sol_natural_session import CandidateSession, digest, tree
from app.persistence.task_continuations import PostgresTaskContinuations
from app.product import sol_contract as product
from app.product.stream_migration import prepare, verify, OLD_MODE
from app.tasks.continuation import ContinuationError, ResumeContinuation
from scripts.reviewer_responses_nonstream import build_wire
from scripts.reviewer_responses_transport import digest as wire_digest
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, create, setup_worker
from tests.test_sol_local_failure_recovery_postgres import receipt_stub


@pytest.fixture
def legacy_paused(continued_api, tmp_path, monkeypatch):
    owner, _, repo, _ = continued_api
    task, run = create(owner)
    make, _, _, calls = setup_worker(tmp_path, monkeypatch, repo, statuses=(524,),
        contract=product, profile=product.WORKER_PROFILE)
    operation, begin = CandidateSession.operation, PostgresTaskContinuations.begin
    def old_begin(self, task, binding):
        binding.pop('execution_contract', None)  # synthetic old producer only
        return begin(self, task, binding)
    def legacy_operation(self, kind, request, action):
        def observed():
            value = action()
            if kind == 'model' and value.get('ok'):
                receipt_stub(self, value)
            elif kind == 'model' and value.get('reaped_timeout'):
                ordinal=value['budget']['calls']; folder=self.transport_root/'review'/f'call-{ordinal:03d}'
                for name in ('profile.json','receipt.json'):
                    path=folder/name; saved=json.loads(path.read_bytes());saved['response_mode']=OLD_MODE
                    if name=='receipt.json': saved['wire_sha256']=wire_digest(build_wire(json.loads((folder/'request.json').read_bytes())))
                    path.write_text(json.dumps(saved),encoding='utf-8')
                value['reaped_timeout']['receipt_sha256']=digest((folder/'receipt.json').read_bytes())
                value['budget']['attempts'][-1]['transport_id']='natural-sol-dual-necessity-nonstream-v1'
                value['budget']['attempts'][-1]['profile']='sol-high-nonstream-v1'
            return value
        return operation(self,kind,request,observed)
    with monkeypatch.context() as scoped:
        scoped.setattr(PostgresTaskContinuations,'begin',old_begin)
        scoped.setattr(CandidateSession,'operation',legacy_operation)
        worker,_=make()
        assert worker.run_once().status.value=='paused'
    store=PostgresTaskContinuations(repo)
    reference=store.load(owner_id='owner-1',task_id=UUID(task))
    assert calls==[[524]] and reference['pause_reason']=='session_timeout_awaiting_manual_retry'
    return dict(task=UUID(task),run=run,repo=repo,store=store,reference=reference,
        parent=tmp_path/run,root=tmp_path/'migrated',original=tree(tmp_path/run))


def adopt(c,path,sha,owner='owner-1'):
    return c['store'].migrate_product_stream(owner_id=owner,task_id=c['task'],proof_path=path,proof_sha256=sha,runs_root=str(c['root']))


def test_explicit_migration_replays_generation_and_keeps_524(legacy_paused, monkeypatch):
    c=legacy_paused
    path,sha=prepare(parent_run=c['parent'],destination_root=c['root'],reference=c['reference'])
    proof=verify(path,sha,runs_root=c['root'])
    assert proof['parent_state']['successful_generation']==2 and proof['parent_state']['failed_nonstream_524']==1
    with pytest.raises(ContinuationError,match='task_not_found'):adopt(c,path,sha,'owner-2')
    assert not adopt(c,path,sha)['replayed']
    assert adopt(c,path,sha)['replayed']
    saved=c['store'].load(owner_id='owner-1',task_id=c['task'])
    assert saved['binding']['execution_contract']==product.CONTRACT.snapshot().model_dump(mode='json')
    with pytest.raises(ContinuationError,match='conflict'):
        c['store'].resume(owner_id='owner-1',task_id=c['task'],request_id='stale',
            command=ResumeContinuation(checkpoint_sha256=c['reference']['checkpoint_sha256']))
    for manual in (False,True):
        saved=c['store'].load(owner_id='owner-1',task_id=c['task'])
        c['store'].resume(owner_id='owner-1',task_id=c['task'],request_id='resume-'+str(manual),
            command=ResumeContinuation(checkpoint_sha256=saved['checkpoint_sha256'],manual_retry=manual))
        make,summary,factories,calls=setup_worker(c['root'],monkeypatch,c['repo'],contract=product,profile=product.WORKER_PROFILE)
        worker,_=make();result=worker.run_once()
        assert result.status.value==('succeeded' if manual else 'paused'),result
        assert calls==([[200,200]] if manual else [[]])
        assert summary.reads==0 and all(not p.generator.requests for f in factories for p in f.providers.values())
    final=c['store'].load(owner_id='owner-1',task_id=c['task'])['accounting']
    assert final['known_tokens']==80 and final['requests_observed']==5 and final['retries']==1
    assert final['unknown_token_reservation']==c['reference']['accounting']['unknown_token_reservation']
    assert tree(c['parent'])==c['original']


@pytest.mark.parametrize('mutation',['parent','child','proof'])
def test_tampered_migration_is_not_adopted(legacy_paused,mutation):
    c=legacy_paused
    path,sha=prepare(parent_run=c['parent'],destination_root=c['root'],reference=c['reference'])
    target=path if mutation=='proof' else c['root']/c['run']/'.continuation/nonstream-parent.zip' if mutation=='child' else c['parent']/'.continuation/session/guard.json'
    target.write_bytes(target.read_bytes()+b' ')
    with pytest.raises(ContinuationError,match='invalid'):adopt(c,path,sha)
    assert c['store'].load(owner_id='owner-1',task_id=c['task'])['binding']==c['reference']['binding']


def test_worker_does_not_implicitly_upgrade_legacy_binding(legacy_paused,monkeypatch):
    c=legacy_paused
    c['store'].resume(owner_id='owner-1',task_id=c['task'],request_id='no-migration',
        command=ResumeContinuation(checkpoint_sha256=c['reference']['checkpoint_sha256']))
    make,_,_,calls=setup_worker(c['parent'].parent,monkeypatch,c['repo'],contract=product,profile=product.WORKER_PROFILE)
    worker,_=make()
    assert worker.run_once().status.value=='paused'
    saved=c['store'].load(owner_id='owner-1',task_id=c['task'])
    assert saved['pause_reason']=='continuation_binding_changed' and calls==[]
    assert tree(c['parent'])==c['original']
