"""External, explicitly recorded time allowance for one original15 continuation.

Keep the frozen contract, requests, checkpoints and cumulative clocks intact.
Only the selected session's remaining completion review receives more elapsed
time. This is an administrative exception, not an original-envelope pass.
"""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import textwrap
import types


VERSION = 'original15-one-case-execution-time-allowance-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def validate(manifest, *, plan_sha, authorization_sha, original_limits):
    if (manifest.get('version') != VERSION
            or manifest.get('plan_sha256') != plan_sha
            or manifest.get('authorization_sha256') != authorization_sha
            or manifest.get('case') != 'scope:3'
            or manifest.get('remaining_stage') != 'completion-fresh'
            or manifest.get('original_limits') != original_limits
            or type(manifest.get('additional_active_seconds')) is not int
            or manifest['additional_active_seconds'] != 3600
            or manifest.get('effective_case_active_seconds') != 7200
            or manifest.get('effective_batch_active_seconds') != 57600
            or manifest.get('reset_accounting') is not False
            or manifest.get('additional_requests') != 0
            or manifest.get('additional_tokens') != 0
            or manifest.get('extend_authorization_expiry') is not False
            or not manifest.get('user_authorization_evidence')):
        raise ValueError('original15_execution_time_allowance_invalid')


def adjusted_limits(budget, request, manifest, verify):
    """Change the local elapsed limit only; preserve all other contract fields."""
    limits = budget.contract.descriptor()
    session = getattr(budget, 'session', None)
    if session is None or Path(session.root) != Path(manifest['session_root']):
        return limits
    verify()
    if session.guard_sha != manifest['guard_sha256']:
        raise ValueError('original15_execution_time_allowance_guard')
    context = request.metadata.get('sol_review_validation', {})
    if context.get('duty') != 'completion' or context.get('stage') != 'fresh':
        return limits
    if hashlib.sha256(context.get('report', '').encode('utf-8')).hexdigest() != manifest['report_sha256']:
        raise ValueError('original15_execution_time_allowance_report')
    if limits['execution_timeout_s'] != manifest['original_limits']['per_case_active_seconds']:
        raise ValueError('original15_execution_time_allowance_base_limit')
    return dict(limits, execution_timeout_s=manifest['effective_case_active_seconds'])


def compile_chat(function, limits_for):
    """Retain the actual shared-budget implementation, replacing its one limit read."""
    source = textwrap.dedent(inspect.getsource(function))
    old = 'limits = self.contract.descriptor()'
    if source.count(old) != 1:
        raise ValueError('original15_execution_time_allowance_source_shape')
    namespace = dict(function.__globals__, _original15_time_limits=limits_for)
    source = source.replace(old, 'limits = _original15_time_limits(self, request)')
    # Use a synthetic filename: never claim the modified function is frozen source.
    exec(compile(source, '<original15-recorded-time-allowance>', 'exec'), namespace)
    return namespace[function.__name__]


def compile_retry(function, old, replacement, helper):
    """Keep closure bindings, including zero-argument super in ServiceBudget."""
    source = textwrap.dedent(inspect.getsource(function))
    if source.count(old) != 1:
        raise ValueError('original15_execution_time_allowance_retry_shape')
    namespace = dict(function.__globals__, **inspect.getclosurevars(function).nonlocals,
                     _original15_retry_limits=helper)
    source = source.replace(old, replacement)
    exec(compile('class _TimeAllowanceScope:\n' + textwrap.indent(source, '    '),
                 '<original15-recorded-time-allowance>', 'exec'), namespace)
    compiled = getattr(namespace['_TimeAllowanceScope'], function.__name__)
    cells = dict(zip(function.__code__.co_freevars, function.__closure__ or (), strict=True))
    closure = tuple(cells[name] for name in compiled.__code__.co_freevars)
    patched = types.FunctionType(compiled.__code__, namespace, function.__name__,
                                 function.__defaults__, closure or None)
    patched.__kwdefaults__ = deepcopy(function.__kwdefaults__)
    return patched


def application_time_exhausted(workflow, request, manifest, verify):
    """A committed application replays its original decision, not a new clock gate."""
    budget = workflow.send.provider
    original_limit = budget.contract.descriptor()['execution_timeout_s']
    session = getattr(workflow, 'session', None)
    if session is None or Path(session.root) != Path(manifest['session_root']):
        return budget.clock() - budget.started >= original_limit
    verify()
    if (session.guard_sha != manifest['guard_sha256']
            or hashlib.sha256(workflow.assembly.report.encode('utf-8')).hexdigest() != manifest['report_sha256']):
        raise ValueError('original15_application_time_binding')
    path = session.root / 'operations' / f'{session.cursor+1:04d}-intent.json'
    result = path.with_name(path.name.replace('-intent', '-result'))
    expected = dict(ordinal=session.cursor+1, kind='journal', request=dict(name='application', data=dict(
        version=workflow.contract_module.VERSION,
        report_sha256=hashlib.sha256(workflow.assembly.report.encode('utf-8')).hexdigest(),
        original_report_sha256=hashlib.sha256(request.report.encode('utf-8')).hexdigest(),
        deterministic_application=True, host_semantics_verified=False, production_admitted=False)))
    if (path.is_file() and result.is_file() and read(path) == expected
            and read(result) == dict(intent_sha256=sha(path), value=dict(recorded=True))):
        # Other source/preview/body checks and the exact operation replay still
        # execute in revise(). No clock, counter, checkpoint or original changes.
        return False
    return budget.clock() - budget.started >= manifest['effective_case_active_seconds']


def install(control, config, launch):
    selection = config.get('execution_time_allowance')
    if selection is None:
        return
    from app.runtime.coach_budget import CoachBudgetedProvider
    from app.runtime.sol_session_runtime import SessionBudget
    from app.runtime.sol_session_receipts import request_from_raw
    from app.evaluation.natural_duty_workflow import NaturalDutyWorkflow
    control = Path(control)
    path = control / selection['file']
    module = control / 'original15_execution_time_allowance.py'
    if path.parent != control or module.resolve() != module or path.resolve() != path:
        raise ValueError('original15_execution_time_allowance_path')
    original_chat = CoachBudgetedProvider._chat_once
    if getattr(original_chat, '_original15_time_allowance', False):
        raise ValueError('original15_execution_time_allowance_duplicate')
    manifest = read(path)

    def verify():
        if (sha(path) != selection['sha256'] or sha(module) != selection['module_sha256']
                or read(path) != manifest):
            raise ValueError('original15_execution_time_allowance_controls_changed')
        validate(manifest, plan_sha=config['plan_sha256'],
                 authorization_sha=config['authorization_sha256'], original_limits=launch.ENVELOPE)
        baseline = Path(manifest['baseline_checkpoint'])
        if (sha(baseline) != manifest['baseline_checkpoint_sha256']
                or sha(Path(manifest['session_root']) / 'guard.json') != manifest['guard_sha256']
                or sha(Path(manifest['application_path'])) != manifest['application_sha256']):
            raise ValueError('original15_execution_time_allowance_original_changed')
        if hashlib.sha256(inspect.getsource(original_chat).encode('utf-8')).hexdigest() != manifest['budget_chat_source_sha256']:
            raise ValueError('original15_execution_time_allowance_source_changed')
        for name, pin in manifest['stdout_evidence'].items():
            if Path(name).name != name or sha(control / 'segments' / name) != pin:
                raise ValueError('original15_execution_time_allowance_stdout_changed')

    verify()
    patched = compile_chat(original_chat,
        lambda budget, request: adjusted_limits(budget, request, manifest, verify))
    patched._original15_time_allowance = True
    CoachBudgetedProvider._chat_once = patched
    def retry_limits(budget, failed):
        attempt = failed.get('reaped_timeout') or failed.get('recoverable_format')
        request = request_from_raw(attempt['issued_raw'])
        return adjusted_limits(budget, request, manifest, verify)

    SessionBudget._manual_retry = compile_retry(SessionBudget._manual_retry,
        'limits = self.contract_module.CONTRACT.descriptor()',
        'limits = _original15_retry_limits(self, failed)', retry_limits)
    service_budget = launch.engine.SessionBudget
    # The service-recovery adapter is installed first. Its HTTP error branch
    # has the same elapsed test; preserve its captured manifest and super class.
    service_budget.chat = compile_retry(service_budget.chat,
        'limits = self.contract_module.CONTRACT.descriptor()',
        'limits = _original15_retry_limits(self, request)',
        lambda budget, request: adjusted_limits(budget, request, manifest, verify))
    NaturalDutyWorkflow.revise = compile_retry(NaturalDutyWorkflow.revise,
        "if budget.clock()-budget.started >= budget.contract.descriptor()['execution_timeout_s']:",
        'if _original15_retry_limits(self, request):',
        lambda workflow, request: application_time_exhausted(workflow, request, manifest, verify))
    return deepcopy(manifest)
