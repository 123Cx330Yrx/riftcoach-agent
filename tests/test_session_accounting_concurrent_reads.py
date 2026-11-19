"""Concurrent readback must wait for the same pinned session, never resend."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from app.evaluation.sol_natural_session import CandidateSession, digest, tree
from app.product import sol_contract
from app.product.run_query import RunQueryService, RunQueryError
from app.product.session_usage import session_accounting


def prepared(tmp_path):
    run = 'query-readers'
    root = tmp_path / run / '.continuation'
    binding = dict(worker_profile=sol_contract.WORKER_PROFILE,
        candidate_contract=sol_contract.VERSION, task_id='query-test', run_id=run)
    kwargs = dict(binding=binding, transport_root=root/'transport'/run,
        journal_root=root/'journal', contract_module=sol_contract, worker_product=True)
    with CandidateSession(root/'session', **kwargs) as session:
        accounting = session_accounting(session)
    pins = dict(guard_sha=digest((root/'session/guard.json').read_bytes()),
        checkpoint_sha=digest(sorted((root/'session/checkpoints').glob('*.json'))[-1].read_bytes()))
    reference = dict(binding=binding, profile=sol_contract.WORKER_PROFILE,
        guard_sha256=pins['guard_sha'], checkpoint_sha256=pins['checkpoint_sha'], accounting=accounting)
    return root, run, kwargs, pins, reference


def test_readback_waits_for_concurrent_reader_without_writes(tmp_path, monkeypatch):
    root, run, kwargs, pins, reference = prepared(tmp_path)
    before = tree(root/'session')
    contended = Event()
    original = CandidateSession.__enter__
    def enter(self):
        try:
            return original(self)
        except ValueError as exc:
            if str(exc) == 'session_executor_active': contended.set()
            raise
    monkeypatch.setattr(CandidateSession, '__enter__', enter)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with CandidateSession(root/'session', **kwargs, **pins, read_only=True):
            future = pool.submit(RunQueryService(tmp_path).get_session_accounting, run, reference)
            assert contended.wait(3), 'test must actually contend on the OS lock'
        assert future.result(timeout=5).model_dump(mode='json') == reference['accounting']
    assert tree(root/'session') == before


def test_readback_does_not_retry_integrity_failure(tmp_path, monkeypatch):
    _, run, _, _, reference = prepared(tmp_path)
    calls = []
    def corrupt(self):
        calls.append(1)
        raise ValueError('session_prior_evidence_changed')
    monkeypatch.setattr(CandidateSession, '__enter__', corrupt)
    with pytest.raises(ValueError, match='session_prior_evidence_changed'):
        RunQueryService(tmp_path).get_session_accounting(run, reference)
    assert calls == [1]


def test_busy_readback_has_a_bounded_wait(tmp_path, monkeypatch):
    root, run, kwargs, pins, reference = prepared(tmp_path)
    from app.product import run_query
    ticks = iter([0.0, 6.0])
    monkeypatch.setattr(run_query.time, 'monotonic', lambda: next(ticks))
    with CandidateSession(root/'session', **kwargs, **pins, read_only=True):
        with pytest.raises(RunQueryError, match='run_not_ready'):
            RunQueryService(tmp_path).get_session_accounting(run, reference)
