"""Append-only recovery of a recorded HTTP service failure in original15.

The historical terminal, outcome, checkpoints, receipts and budget stay intact.
An explicit manifest selects a new terminal name for this one continuation.
Other active cases gain manual service-error pauses, never automatic retries.
Frozen method bodies are copied in memory with enumerated, checked edits only.
"""
import inspect
import json
from pathlib import Path
import textwrap

from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, SessionBlocked, canonical, digest
from app.evaluation.golden_journal import write_new_json
from app.providers.errors import ProviderResponseError
from app.runtime.sol_session_runtime import SessionBudget
from app.runtime.sol_session_receipts import request_from_raw

SERVICE_STATUSES = (429, 500, 502, 503)
TERMINAL = 'terminal-service-recovery.json'


def read(path):
    return json.loads(Path(path).read_bytes())


def service_failure(session, value):
    """Require an owned, fully observed service error, without a model answer."""
    if not isinstance(value, dict) or value.get('ok') is not False:
        return None
    ordinal = value.get('budget', {}).get('calls')
    if type(ordinal) is not int or ordinal < 1:
        return None
    folder = session.transport_root / 'review' / f'call-{ordinal:03d}'
    receipt, obs, worker = (read(folder / name) for name in
        ('receipt.json', 'observation/observation.json', 'worker-result.json'))
    status = obs.get('response_status')
    code = f'http_status_{status}'
    http_error = (type(status) is int and status in SERVICE_STATUSES
        and receipt.get('worker_code') == code and worker.get('code') == code
        and obs.get('eof') is True and obs.get('closed') is True)
    connect_error = (status is None and receipt.get('worker_code') == 'request_failed'
        and worker.get('code') == 'request_failed'
        and receipt.get('failure_category') == worker.get('failure_category') == 'connect_error'
        and obs.get('phase') == 'response_headers_failed'
        and obs.get('exception_type') == 'connect_error'
        and obs.get('read_calls') == obs.get('raw_chunks') == obs.get('raw_bytes') == 0
        and obs.get('eof') is False and obs.get('closed') is False)
    if (not (http_error or connect_error)
            or receipt.get('ok') is not False or receipt.get('code') != 'worker_rejected'
            or receipt.get('reaped') is not True or receipt.get('worker_exit') != 0
            or receipt.get('usage_state') != 'unknown' or receipt.get('usage') is not None
            or receipt.get('usage_conflict') is not False
            or receipt.get('http_requests') != 1 or type(obs.get('http_requests')) is not int
            or obs['http_requests'] != 1 or obs.get('schema_version') != 'stream-observation-v1'
            or obs.get('body_free') is not True or obs.get('response_contract') is not None
            or worker.get('public_tool_call') is not None or worker.get('usage') is not None
            or worker.get('diagnostic_tool_call') is not None):
        return None
    attempt = read(session.root / 'operations' / f'attempt-{ordinal:03d}.json')
    return dict(status=status, ordinal=ordinal, issued_raw=attempt['issued_raw'],
        receipt_sha256=digest((folder / 'receipt.json').read_bytes()))


def terminal_for(session):
    return session.root / (TERMINAL if getattr(session, 'service_recovery', None) else 'terminal.json')


def rewrite(function, replacements, extra):
    """No filesystem source edits; fail if the pinned implementation drifts."""
    source = textwrap.dedent(inspect.getsource(function))
    for old, new, count in replacements:
        if source.count(old) != count:
            raise ValueError('original15_service_recovery_source_shape')
        source = source.replace(old, new)
    namespace = function.__globals__
    namespace.update(extra)
    exec(compile(source, inspect.getsourcefile(function), 'exec'), namespace)
    return namespace[function.__name__]


def source_functions(launch):
    from app.evaluation.sol_session_review import SessionReviewGate
    return dict(operation=CandidateSession.operation, close=CandidateSession.close,
        status=CandidateSession.status, reconcile=CandidateSession.reconcile_completed,
        submit=SessionReviewGate.submit, execute=launch.execute,
        frontier=launch.frontier, replay_case=launch.replay_case)


def function_pins(launch):
    return {name: digest(inspect.getsource(function).encode('utf-8'))
            for name, function in source_functions(launch).items()}


def activate(launch, manifest, reload_manifest):
    """Install once in a fresh controller process, scoped by original manifest."""
    from app.evaluation.sol_session_review import SessionReviewGate
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    if getattr(launch, '_service_recovery_installed', False):
        raise ValueError('original15_service_recovery_already_installed')
    manifests = manifest.get('recoveries', [manifest])
    if (not manifests or len({m['case_root'] for m in manifests}) != len(manifests)
            or any(function_pins(launch) != m['function_sha256'] for m in manifests)):
        raise ValueError('original15_service_recovery_source_changed')
    original_open = launch.open_case
    original_budget = launch.engine.SessionBudget
    original_workflow = launch.engine.FixedReportWorkflow
    record_roots = {Path(m['case_root']) / 'session': m for m in manifests}

    def verify_manifest(session=None):
        if reload_manifest() != manifest:
            raise SessionBlocked('original15_service_recovery_controls_changed')
        selected = record_roots.get(session.root) if session is not None else None
        if selected is not None:
            for name, pin in selected['inventory'].items():
                path = Path(selected['case_root']) / name
                if path.resolve() != path or path.stat().st_nlink != 1 or digest(path.read_bytes()) != pin:
                    raise SessionBlocked('original15_service_recovery_parent_changed')

    class RecoverySession(CandidateSession):
        def verify(self):
            verify_manifest(self)
            return super().verify()

        def status(self):
            value = patched_status(self)
            paths = sorted((self.root / 'operations').glob('*-result.json'))
            failed = read(paths[-1])['value'] if paths else None
            # The historical failure journal follows its failed model operation.
            if self.service_recovery:
                ordinal = self.service_recovery.get('failed_operation_ordinal', 1)
                if len(paths) == ordinal + 1:
                    failed = read(self.root/'operations'/f'{ordinal:04d}-result.json')['value']
            value['transport_waiting'] = (not value['closed'] and not value['unresolved']
                and service_failure(self, failed) is not None)
            return value

    common = dict(_service_terminal=terminal_for)
    for name in ('operation', 'close', 'reconcile_completed'):
        old = getattr(CandidateSession, name)
        setattr(RecoverySession, name, rewrite(old,
            [("self.root/'terminal.json'", '_service_terminal(self)', 1)], common))
    patched_status = rewrite(CandidateSession.status,
        [("self.root/'terminal.json'", '_service_terminal(self)', 1)], common)

    patched_submit = rewrite(SessionReviewGate.submit,
        [("session.root/'terminal.json'", '_service_terminal(session)', 2)], common)

    def open_case(*args, **kwargs):
        session, gate = original_open(*args, **kwargs)
        session.__class__ = RecoverySession
        session.service_recovery = record_roots.get(session.root)
        gate.submit = patched_submit.__get__(gate, type(gate))
        return session, gate

    class ServiceBudget(original_budget):
        def chat(self, request):
            if not isinstance(self.session, RecoverySession):
                return super().chat(request)
            while True:
                try:
                    return super().chat(request)
                except ProviderResponseError:
                    session = self.session
                    path = session.root / 'operations' / f'{session.cursor:04d}-result.json'
                    if not path.exists():
                        raise
                    value = read(path)['value']
                    failure = service_failure(session, value)
                    if failure is None:
                        raise
                    # Verify request/profile/transport/unknown reservation using
                    # the unchanged full receipt auditor before retry authority.
                    launch.audit_transport(session)
                    selected = session.service_recovery
                    if selected and session.cursor == selected.get('failed_operation_ordinal', 1):
                        journal = read(session.root / 'operations' / f'{session.cursor+1:04d}-intent.json')
                        if journal['kind'] != 'journal' or journal['request']['name'] != 'outcome':
                            raise SessionBlocked('original15_service_recovery_journal_changed')
                        session.operation('journal', journal['request'],
                            lambda: (_ for _ in ()).throw(AssertionError('historical replay only')))
                    bound = dict(failed_result_sha256=digest(path.read_bytes()), failure=failure,
                        budget=value['budget'], recovery_manifest_sha256=(selected or manifests[0])['manifest_identity'])
                    next_path = session.root / 'operations' / f'{session.cursor+1:04d}-intent.json'
                    if not next_path.exists():
                        if session.read_only or not session.manual_retry:
                            raise SessionPaused('session_service_awaiting_manual_retry')
                        limits = self.contract_module.CONTRACT.descriptor()
                        issued = request_from_raw(failure['issued_raw'])
                        reserve = estimate_runtime_request_input_ceiling(issued) + issued.max_tokens
                        if (self.calls >= limits['max_calls'] or self.router._retries >= limits['transport_retries']
                                or self.tokens + self.reserved_tokens + reserve > limits['total_tokens']
                                or session.active_seconds >= limits['execution_timeout_s']):
                            raise SessionPaused('session_retry_budget_extension_required')

                    def approve():
                        session.manual_retry = False
                        self.router._retry_request = request_from_raw(failure['issued_raw'])
                        self.router._retries += 1
                        self.router._failed = self.stopped = False
                        return dict(budget=self.snapshot(), automatic=False, same_stage=True,
                            historical_failure_preserved=True)

                    decision, replayed = session.operation('service-retry', bound, approve)
                    if replayed:
                        self.restore(decision['budget'])
                        next_result = session.root / 'operations' / f'{session.cursor+1:04d}-result.json'
                        if not next_result.exists():
                            session.manual_retry = False

    class RecoveryWorkflow(original_workflow):
        def record(self, name, data):
            if name != 'outcome' or not getattr(self.session, 'service_recovery', None):
                return super().record(name, data)
            def save():
                write_new_json(self.journal_root / 'outcome-service-recovery.json', data)
                return dict(recorded=True)
            return self.session.operation('journal', dict(name=name, data=data), save)

    def case_terminal(folder):
        folder = Path(folder)
        return folder / ('session/' + TERMINAL if folder / 'session' in record_roots else 'session/terminal.json')

    launch.open_case = open_case
    launch.engine.SessionBudget = ServiceBudget
    launch.engine.FixedReportWorkflow = RecoveryWorkflow
    launch.execute = rewrite(launch.execute,
        [("status['timeout_waiting'] or status['format_waiting']",
          "status['timeout_waiting'] or status['format_waiting'] or status.get('transport_waiting', False)", 1)], {})
    launch.frontier = rewrite(launch.frontier,
        [("(folder/'session/terminal.json')", '_service_case_terminal(folder)', 1)],
        dict(_service_case_terminal=case_terminal))
    launch.replay_case = rewrite(launch.replay_case,
        [("session.root/'terminal.json'", '_service_terminal(session)', 1)], common)
    launch._service_recovery_installed = True
    return dict(verify=verify_manifest, session_class=RecoverySession)


def install(control, config, launch):
    selection = config.get('service_error_recovery')
    if selection is None:
        return
    control = Path(control)
    def load():
        module = control / 'original15_transport_recovery.py'
        values = []
        for item in [selection, *config.get('service_error_recovery_extensions', [])]:
            path = control / item['file']
            if (path.parent != control or digest(module.read_bytes()) != item['module_sha256']
                    or digest(path.read_bytes()) != item['sha256']):
                raise ValueError('original15_service_recovery_controls_changed')
            value = read(path)
            if value['plan_sha256'] != config['plan_sha256']:
                raise ValueError('original15_service_recovery_plan_changed')
            identity = dict(value)
            identity.pop('manifest_identity')
            if digest(canonical(identity)) != value['manifest_identity']:
                raise ValueError('original15_service_recovery_manifest_identity')
            values.append(value)
        return values[0] if len(values) == 1 else dict(recoveries=values)
    return activate(launch, load(), load)
