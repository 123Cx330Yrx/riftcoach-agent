"""Real owner resume and Worker pinning with scripted model transport."""
from uuid import UUID

from app.persistence.task_continuations import PostgresTaskContinuations
from app.product import sol_contract as product
from app.tasks.continuation import ResumeContinuation
from tests.test_product_budget_supplement import grant
from tests.test_evidence_product_api_postgres import migrated_product_api
from tests.test_natural_duty_worker_postgres import no_external_services
from tests.test_sol_worker_continuation_postgres import continued_api, create, setup_worker


def test_worker_persists_supplement_without_sending_and_resumes_same_task(continued_api,tmp_path,monkeypatch):
    from app.product.local_failure_recovery import _session
    owner,_,repo,_=continued_api
    task,run=create(owner);task=UUID(task)
    make,summary,factories,requests=setup_worker(tmp_path,monkeypatch,repo,statuses=(524,),
        contract=product,profile=product.WORKER_PROFILE)
    worker,_=make();assert worker.run_once().status.value=='paused'
    store=PostgresTaskContinuations(repo);ref=store.load(owner_id='owner-1',task_id=task)
    with _session(tmp_path/run,ref) as session:value=grant(session)
    store.resume(owner_id='owner-1',task_id=task,request_id='budget-activate',
        command=ResumeContinuation(checkpoint_sha256=ref['checkpoint_sha256']))
    worker,route=make();route.candidate.budget_supplement=value
    assert worker.run_once().status.value=='paused'
    current=store.load(owner_id='owner-1',task_id=task)
    assert current['checkpoint_sha256']!=ref['checkpoint_sha256']
    assert current['accounting']==ref['accounting'] and requests==[[524],[]]
    store.resume(owner_id='owner-1',task_id=task,request_id='budget-send',
        command=ResumeContinuation(checkpoint_sha256=current['checkpoint_sha256'],manual_retry=True))
    worker,_=make();assert worker.run_once().status.value=='succeeded'
    assert requests==[[524],[],[200,200]] and summary.reads==1
    current=store.load(owner_id='owner-1',task_id=task)
    assert current['accounting']['unknown_token_reservation']==ref['accounting']['unknown_token_reservation']
    assert current['accounting']['requests_observed']==5
