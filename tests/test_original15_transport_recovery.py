"""Real session/owned mock HTTP worker; no provider or native network requests."""
import json
from pathlib import Path

import pytest

from app.evaluation.sol_natural_session import SessionPaused, SessionBlocked, tree, digest, canonical
from scripts import sol_original15_launch as launch
from scripts import original15_transport_recovery as recovery
from tests.test_sol_original15_session import setup, offline, router, author


def activate(monkeypatch, current):
    manifest = dict(case_root=str(current.root.parent), plan_sha256='1'*64,
        inventory={p.relative_to(current.root.parent).as_posix(): digest(p.read_bytes())
            for p in current.root.parent.rglob('*') if p.is_file() and p.name != 'session.lock'},
        function_sha256=recovery.function_pins(launch))
    manifest['manifest_identity'] = digest(canonical(manifest))
    # Restore the module aliases after each test; frozen classes stay untouched.
    for obj, names in [(launch, ['open_case', 'execute', 'frontier', 'replay_case']),
                       (launch.engine, ['SessionBudget', 'FixedReportWorkflow'])]:
        for name in names:
            monkeypatch.setattr(obj, name, getattr(obj, name))
    monkeypatch.setattr(launch, '_service_recovery_installed', False, raising=False)
    installed = recovery.activate(launch, manifest, lambda: manifest)
    def adapt(session, gate):
        session.__class__ = installed['session_class']
        session.service_recovery = manifest
        # Tests also use the actual launch.open_case for the submit method below.
        from app.evaluation.sol_session_review import SessionReviewGate
        gate.submit = recovery.rewrite(SessionReviewGate.submit,
            [("session.root/'terminal.json'", '_service_terminal(session)', 2)],
            dict(_service_terminal=recovery.terminal_for)).__get__(gate, type(gate))
        return session, gate
    return manifest, adapt


def failed(opened):
    current, gate = opened()
    calls = []
    with current, pytest.raises(Exception):
        launch.advance_case(current, router(current, calls, status=500))
    assert calls == [500] and current.status()['closed']
    return current


def test_closed_500_append_recovery_repeated_service_pause_same_request_and_native_path(setup, monkeypatch):
    opened, turns, operator = setup
    current = failed(opened)
    manifest, adapt = activate(monkeypatch, current)
    preserved = dict(manifest['inventory'])
    # Without a manual decision, no new call; original terminal remains.
    waiting, gate = adapt(*opened(previous=current))
    calls = []
    with waiting, pytest.raises(SessionPaused, match='service_awaiting_manual_retry'):
        launch.engine.run_case(waiting, router(waiting, calls))
    assert calls == [] and waiting.status()['transport_waiting'] and not waiting.status()['closed']
    # A second 500 pauses locally, retains both unknown reservations and buys no automatic third call.
    retry, gate = adapt(*opened(previous=waiting, manual_retry=True))
    with retry, pytest.raises(SessionPaused, match='service_awaiting_manual_retry'):
        launch.engine.run_case(retry, router(retry, calls, status=500))
    assert calls == [500] and retry.status()['transport_waiting']
    # Explicit retry succeeds and stops at the real native author/import boundary.
    success, gate = adapt(*opened(previous=retry, manual_retry=True))
    with success, pytest.raises(SessionPaused, match='awaiting_native_review'):
        launch.engine.run_case(success, router(success, calls))
    assert calls == [500, 200]
    importer, gate = adapt(*opened(previous=success))
    with importer:
        handle = list(gate.handles())[-1]
        primary, event = author(handle, turns, gate.native.workspace)
        assert gate.submit('facts-initial', primary, event)
    # Finish the unchanged workflow and verify a distinct terminal/outcome.
    previous = importer
    while True:
        session, gate = adapt(*opened(previous=previous))
        try:
            with session:
                result = launch.engine.run_case(session, router(session, calls))
                session.close(dict(result=result))
        except SessionPaused:
            importer, gate = adapt(*opened(previous=session))
            with importer:
                handle = list(gate.handles())[-1]
                primary, event = author(handle, turns, gate.native.workspace)
                assert gate.submit(handle['binding']['key'], primary, event)
            previous = importer
        else:
            break
    assert result['matched'] and result['accounting']['calls'] == 6
    assert result['accounting']['retries'] == 2 and result['accounting']['reserved_tokens'] > 0
    assert session.status()['closed'] and (session.root/recovery.TERMINAL).exists()
    assert (session.journal_root/'outcome-service-recovery.json').exists()
    for name, pin in preserved.items():
        assert digest((current.root.parent/name).read_bytes()) == pin
    readonly, _ = adapt(*opened(previous=session, read_only=True))
    before = tree(current.root.parent)
    with readonly:
        replay = launch.engine.run_case(readonly, router(readonly, []))
        audit = launch.audit_transport(readonly)
    assert replay == result and audit['actual_attempts'] == 6
    assert audit['failed_calls'] == 2 and audit['http_requests_known'] == 6
    assert tree(current.root.parent) == before


@pytest.mark.parametrize('status', [400, 401, 403, 404, 200, 524])
def test_no_service_recovery_for_identity_auth_schema_or_other_status(setup, status):
    opened, _, _ = setup
    current, _ = opened()
    with current, pytest.raises(BaseException):
        launch.advance_case(current, router(current, [], status=status, mode='wrong_model'))
    first = json.loads((current.root/'operations/0001-result.json').read_bytes())['value']
    assert recovery.service_failure(current, first) is None


def test_original_failure_tampering_rejected(setup, monkeypatch):
    opened, _, _ = setup
    current = failed(opened)
    _, adapt = activate(monkeypatch, current)
    old = current.root/'terminal.json'
    old.write_bytes(old.read_bytes()+b' ')
    replay, _ = adapt(*opened(previous=current))
    with pytest.raises(SessionBlocked, match='parent_changed'), replay:
        pass


def test_future_active_case_service_error_pauses_without_terminal_or_outcome(setup, monkeypatch):
    opened, _, _ = setup
    parent = failed(opened)
    _, adapt = activate(monkeypatch, parent)
    current, gate = adapt(*opened(key='claim-scope:1'))
    current.service_recovery = None
    calls = []
    with current, pytest.raises(SessionPaused, match='service_awaiting_manual_retry'):
        launch.engine.run_case(current, router(current, calls, status=500))
    assert calls == [500] and current.status()['transport_waiting']
    assert not current.status()['closed'] and not (current.root/'terminal.json').exists()
    assert not (current.journal_root/'outcome.json').exists()
