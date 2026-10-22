"""Explicit, resumable natural-task development entry; no default paid action.

Preparation and native task/import/replay never load credentials. Only `run`
loads an explicitly authorized Zhipu config or prompts for its key, then prompts
for the distinct reviewer key, after a pinned grant, CI and native preflight.
This entry does not reopen any historical trial or grant product qualification.
"""
import argparse
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import getpass
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import warnings

from app.evaluation import sol_natural_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import REQUEST
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, SessionPaused, canonical, digest
from app.evaluation.sol_session_review import SessionReviewGate
from scripts import natural_duty_preparation as base
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.prepare_sol_natural import capture
from scripts.review_independence_contract import freeze_v2_identity, MODE_V2, FINAL_POLICY
from scripts.reviewer_profile_batch import source_identity, inventory
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_natural_duty_development import current_head, verify_ci

ROOT = contract.ROOT
VERSION = 'sol-natural-launch-v1'
CODEX = Path('C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe')


def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)


def source():
    identity = source_identity()
    for folder in (ROOT/'data/rag_docs', base.SOURCES):
        identity['files'].update({(folder/relative).relative_to(ROOT).as_posix(): pin
                                  for relative, pin in inventory(folder).items()})
    return identity


def limits():
    descriptor = contract.CONTRACT.descriptor()
    return {k: descriptor[k] for k in ('max_calls', 'total_tokens', 'execution_timeout_s',
                                      'transport_retries', 'request_timeout_s')}


def first_pin(first):
    # The offline capture sees the issued request AFTER budget annotation;
    # CandidateSession sees the same request BEFORE that annotation.
    metadata = dict(first.metadata)
    metadata.pop('coach_budget_contract', None)
    normalized = json.loads(REQUEST.dump_json(replace(first, timeout_s=300.0, metadata=metadata)))
    return digest(canonical(normalized))


def require_paths(plan):
    if (Path.cwd().resolve() != ROOT.resolve() or plan['cwd'] != str(ROOT.resolve())
            or plan['python'] != str(Path(sys.executable).resolve())
            or plan['codex'] != str(CODEX.resolve())):
        raise ValueError('launch_actual_execution_paths_changed')
    operator = Path(plan['operator'])
    if (not operator.is_absolute() or operator.resolve() != operator
            or operator.is_relative_to(ROOT) or ROOT.is_relative_to(operator)):
        raise ValueError('launch_operator_must_be_external')
    return operator


def prepare(operator, run_id, primary, independent, *, parent_operator=None, parent_seal_sha=None):
    head = current_head()
    operator = Path(operator).absolute()
    first, offline = capture(run_id)
    # SessionBudget normalizes ONLY the remaining timeout before local replay.
    review_plan = freeze_v2_identity(dict(host_review_submission_mode=MODE_V2,
        host_review_evidence_policy=FINAL_POLICY), root_thread_id=primary,
        primary_id=primary, independent_id=independent)
    plan = dict(version=VERSION, run_id=run_id, operator=str(operator), head=head,
        cwd=str(ROOT.resolve()), python=str(Path(sys.executable).resolve()), codex=str(CODEX.resolve()),
        source=source(), offline=offline, first_request_sha256=first_pin(first),
        review_plan=review_plan, limits=limits(), estimated_uncached_cny=offline['estimated_uncached_cny'],
        execution_authorized=False, publication_allowed=False, production_admitted=False)
    if parent_operator is not None:
        from scripts.sol_natural_continuation import parent_state, verify_source
        parent = parent_state(parent_operator, parent_seal_sha, limits_override=limits())
        parent_path = Path(parent['operator'])
        if operator.is_relative_to(parent_path) or parent_path.is_relative_to(operator):
            raise ValueError('launch_parent_operator_overlap')
        if (run_id != parent['run_id'] or plan['first_request_sha256'] != parent['first_request_sha256']
                or review_plan != parent['review_plan']):
            raise ValueError('launch_continuation_task_changed')
        plan['continuation'] = parent
        plan['continuation_source_changes'] = verify_source(parent, plan['source'])
        plan['estimated_uncached_cny'] = parent['estimated_additional_cny']
        plan['offline']['estimated_uncached_cny'] = parent['estimated_additional_cny']
        plan['offline']['continuation_frontier'] = preview_continuation(plan)
    require_paths(plan)
    if operator.exists():
        raise ValueError('launch_operator_already_exists')
    operator.mkdir(parents=True)
    write_new_json(operator/'plan.json', plan)
    return dict(plan_sha256=digest((operator/'plan.json').read_bytes()), operator=str(operator),
                provider_requests=0, key_read=False, paid_launcher_ready=False)


def load(operator, plan_sha, *, frozen=False):
    path = Path(operator)/'plan.json'
    raw = path.read_bytes()
    if digest(raw) != plan_sha:
        raise ValueError('launch_original_plan_sha_required')
    plan = json.loads(raw)
    if plan['version'] != VERSION or require_paths(plan) != Path(operator).resolve():
        raise ValueError('launch_plan_binding')
    if frozen and (current_head() != plan['head'] or source() != plan['source']):
        raise ValueError('launch_frozen_source_changed')
    return plan


def validate_grant(grant, plan, plan_sha, *, now=None):
    now = now or datetime.now(timezone.utc)
    issued, expires = (datetime.fromisoformat(grant[k]) for k in ('issued_at', 'expires_at'))
    if (issued.utcoffset() is None or expires.utcoffset() is None or not issued <= now < expires
            or not timedelta(0) < expires-issued <= timedelta(days=1)
            or grant.get('version') != VERSION+'-authorization'
            or grant.get('plan_sha256') != plan_sha or grant.get('head') != plan['head']
            or grant.get('run_id') != plan['run_id'] or grant.get('limits') != plan['limits']
            or grant.get('estimated_uncached_cny') != plan['estimated_uncached_cny']
            or grant.get('retry_authorized') is not True or grant.get('production_admitted') is not False
            or not isinstance(grant.get('user_authorization_evidence'), str)
            or not grant['user_authorization_evidence'].strip()):
        raise ValueError('launch_specific_unexpired_authorization_required')
    if plan.get('continuation'):
        expected = dict(parent_seal_sha256=plan['continuation']['seal_sha256'],
            max_new_attempts=plan['continuation']['remaining_attempts'],
            max_new_tokens=plan['continuation']['max_new_tokens'], generation_requests=0)
        if grant.get('continuation') != expected:
            raise ValueError('launch_continuation_specific_authorization_required')


@contextmanager
def host(plan):
    with CodexReadOnlyClient(CODEX) as client:
        yield CodexHostReviewEventSource(client, plan['review_plan'])


def session_for(plan, plan_sha, event_source, *, preflight=False, guard=None, checkpoint=None,
                read_only=False, before=None, sink=emit, authorization_sha=None):
    operator = require_paths(plan)
    run_id = plan['run_id']
    folder = operator/('native-preflight' if preflight else 'execution')
    binding = dict(plan_sha256=plan_sha, run_id=run_id,
        review_plan_sha256=digest(canonical(plan['review_plan'])), fixture_only=preflight,
        authorization_sha256=authorization_sha)
    if not preflight:
        binding['first_request_sha256'] = plan['first_request_sha256']
    extra = {}
    if not preflight and plan.get('continuation'):
        extra['continuation'] = plan['continuation']
        binding['continuation_sha256'] = digest(canonical(plan['continuation']))
    session = CandidateSession(folder/'session', binding=binding,
        transport_root=folder/'transport'/run_id, journal_root=folder/'journal',
        guard_sha=guard, checkpoint_sha=checkpoint, read_only=read_only,
        checkpoint_sink=sink, before_new_model=before, **extra)
    workspace = HostReviewWorkspace(cwd=ROOT, python=sys.executable,
        answers=operator.with_name(operator.name+'-authors'), evidence_roots=[operator])
    gate = SessionReviewGate(session, plan=plan['review_plan'], workspace=workspace, event_source=event_source)
    return session, gate


def native_task(plan, plan_sha, event_source):
    """One explicit administrative fixture. Never substitutes for business review."""
    verify_native_principals(event_source.client, plan['review_plan'])
    session, gate = session_for(plan, plan_sha, event_source, preflight=True)
    try:
        with session:
            gate.require('startup-preflight', 'opinion', dict(
                fixture_only=True, administrative_preflight=True, responses=[],
                report='Administrative fixture: zero third-party calls; no business quality claim.',
                sources={'scope': 'administrative fixture only'},
                instructions='Verify this administrative scope and the author/check-answer/native import path only.'),
                'Administrative fixture: zero third-party calls; no business quality claim.')
    except SessionPaused:
        pass
    return dict(provider_requests=0, key_read=False, native_preflight_complete=False)


def inspect_task(plan, plan_sha, event_source, **kwargs):
    session, gate = session_for(plan, plan_sha, event_source, read_only=True, **kwargs)
    with session:
        handles = list(gate.handles())
        if not handles:
            raise ValueError('launch_no_pending_host_task')
        handle = handles[-1]
        if (Path(handle['folder'])/'submission.json').exists():
            raise ValueError('launch_task_already_submitted')
        # Print the saved full dispatch, never reconstruct or summarize it.
        return (Path(handle['folder'])/'dispatch.txt').read_text(encoding='utf-8')


def submit(plan, plan_sha, event_source, key, primary_file, event_id, **kwargs):
    session, gate = session_for(plan, plan_sha, event_source, **kwargs)
    with session:
        accepted = gate.submit(key, json.loads(Path(primary_file).read_bytes()), event_id)
    return dict(accepted=accepted, provider_requests=0, key_read=False)


def verify_preflight(plan, plan_sha, event_source, proof):
    session, gate = session_for(plan, plan_sha, event_source, preflight=True, read_only=True,
        guard=proof['guard_sha256'], checkpoint=proof['checkpoint_sha256'])
    with session:
        handles = list(gate.handles())
        if len(handles) != 1 or handles[0]['binding']['key'] != 'startup-preflight':
            raise ValueError('launch_native_preflight_missing')
        if not gate.native.replay(handles[0]):
            raise ValueError('launch_native_preflight_rejected')
    return True


def credentials(zhipu_env_file=None):
    # Refuse echoed fallback; only an explicitly selected file may supply Zhipu.
    if not sys.stdin.isatty():
        raise ValueError('launch_interactive_hidden_key_input_required')
    from app.providers.config import ZhipuSettings
    if zhipu_env_file is not None:
        from scripts.run_role_coach_development import load_role_settings
        path = Path(zhipu_env_file)
        if not path.is_absolute() or not path.is_file():
            raise ValueError('launch_explicit_zhipu_config_required')
        generator = load_role_settings(path)[0]
        if generator.base_url.rstrip('/') != 'https://open.bigmodel.cn/api/paas/v4':
            raise ValueError('launch_zhipu_standard_endpoint_required')
        generator = replace(generator, default_timeout_s=300)
    else:
        generator = None
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        if generator is None:
            flash = getpass.getpass('Zhipu Flash API key (hidden): ')
            generator = ZhipuSettings(api_key=flash, base_url='https://open.bigmodel.cn/api/paas/v4',
                                     model='glm-5.3-flash', default_timeout_s=300)
        sol = getpass.getpass('Tianjige GPT-pro API key (hidden): ')
    if not sol.strip() or generator.api_key == sol:
        raise ValueError('launch_distinct_provider_keys_required')
    return generator, sol


def continuation_credentials():
    """Only the unfinished reviewer can send; no generator key is loaded."""
    if not sys.stdin.isatty():
        raise ValueError('launch_interactive_hidden_key_input_required')
    from app.providers.config import ZhipuSettings
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        key = getpass.getpass('Tianjige GPT-pro API key (hidden): ')
    if not key.strip():
        raise ValueError('launch_explicit_reviewer_key_required')
    return ZhipuSettings(api_key='UNUSED_GENERATION_FORBIDDEN',
        base_url='https://open.bigmodel.cn/api/paas/v4', model='glm-5.3-flash'), key


def preview_continuation(plan):
    """Replay the saved prefix through the actual app, stopping before any IO."""
    from app.providers.config import ZhipuSettings
    from app.runtime.sol_natural_provider import SolNaturalProviderFactory
    parent = plan['continuation']
    def forbidden(*args, **kwargs):
        raise AssertionError('offline continuation attempted IO or native reading')
    # A correctly typed event source that cannot read anything. No Host task
    # exists before the paused first review; future native checks remain live.
    class NoNative:
        request = forbidden
    with TemporaryDirectory(prefix='sol-continuation-preview-') as directory:
        root = Path(directory)
        session = CandidateSession(root/'session',
            binding=dict(first_request_sha256=plan['first_request_sha256'],
                review_plan_sha256=digest(canonical(plan['review_plan'])),
                continuation_sha256=digest(canonical(parent)), fixture_only=False),
            continuation=parent, transport_root=root/'transport'/plan['run_id'],
            journal_root=root/'journal', before_new_model=forbidden, max_new_models=0)
        workspace = HostReviewWorkspace(cwd=ROOT, python=sys.executable,
            answers=root/'authors', evidence_roots=[root/'journal'])
        SessionReviewGate(session, plan=plan['review_plan'], workspace=workspace,
            event_source=CodexHostReviewEventSource(NoNative(), plan['review_plan']))
        factory = SolNaturalProviderFactory(generator_settings=ZhipuSettings(
            api_key='OFFLINE_NO_SEND', base_url='https://open.bigmodel.cn/api/paas/v4',
            model='glm-5.3-flash'), api_key='OFFLINE_NO_SEND', transport_root=root/'transport')
        try:
            with session:
                prepared = base.build_application(provider_factory=factory, output_root=root/'derived',
                    run_id=plan['run_id'], candidate=contract, execution_session=session)
                prepared.run()
        except SessionPaused as error:
            if str(error) != 'session_model_boundary' or session.cursor != parent['prefix_operations']:
                raise
        else:
            raise ValueError('launch_continuation_frontier_not_reached')
        if inventory(root/'transport') or inventory(root/'journal'):
            raise ValueError('launch_continuation_preview_unexpected_io')
    return dict(provider_requests=0, key_read=False, imported_operations=parent['prefix_operations'],
        generation_requests=0, next_stage='facts-initial',
        exact_frontier_request_sha256=parent['frontier_request_sha256'],
        report_sha256=parent['report_sha256'])


def verify_derived(plan, session):
    expected = {}
    for path in sorted(session.root.glob('derived-*.json')):
        row = json.loads(path.read_bytes())
        expected.update({row['segment']+'/'+name: pin for name, pin in row['files'].items()})
    if inventory(Path(plan['operator'])/'derived') != expected:
        raise SessionBlocked('launch_derived_evidence_changed')


def execute(plan, plan_sha, event_source, *, authorization_file, authorization_sha,
            ci_run, preflight_proof, guard=None, checkpoint=None, zhipu_env_file=None):
    raw = Path(authorization_file).read_bytes()
    if digest(raw) != authorization_sha:
        raise ValueError('launch_original_authorization_sha_required')
    grant = json.loads(raw)
    validate_grant(grant, plan, plan_sha)
    config_path = str(Path(zhipu_env_file).resolve()) if zhipu_env_file is not None else None
    if grant.get('zhipu_env_file') != config_path:
        raise ValueError('launch_authorized_zhipu_config_required')
    load(plan['operator'], plan_sha, frozen=True)
    ci = verify_ci(ci_run, plan['head'])
    verify_native_principals(event_source.client, plan['review_plan'])
    verify_preflight(plan, plan_sha, event_source, preflight_proof)

    def before():
        validate_grant(grant, plan, plan_sha)
        if Path(authorization_file).read_bytes() != raw:
            raise SessionBlocked('launch_authorization_changed')
        load(plan['operator'], plan_sha, frozen=True)
        verify_preflight(plan, plan_sha, event_source, preflight_proof)
        verify_native_principals(event_source.client, plan['review_plan'])

    session, gate = session_for(plan, plan_sha, event_source, guard=guard, checkpoint=checkpoint,
        before=before, authorization_sha=authorization_sha)
    try:
        with session:
            launch_record = dict(ci=ci, authorization_sha256=authorization_sha,
                native_preflight=preflight_proof, plan_sha256=plan_sha)
            if guard is None:
                with (session.root/'authorization.json').open('xb') as handle:
                    handle.write(raw)
                write_new_json(session.root/'launch.json', launch_record)
                session._checkpoint('launcher_verified')
            elif (json.loads((session.root/'launch.json').read_bytes()) != launch_record
                    or (session.root/'authorization.json').read_bytes() != raw):
                raise SessionBlocked('launch_original_controls_changed')
            status = session.status()
            if status['closed'] or status['unresolved']:
                raise SessionBlocked('launch_closed_or_unresolved_no_send')
            verify_derived(plan, session)
            handles = list(gate.handles())
            if handles and not (Path(handles[-1]['folder'])/'submission.json').exists():
                raise SessionPaused('session_awaiting_native_review')
            gate.verify_prior()
            # Ownership, frozen source, grant and live native checks precede prompts.
            if plan.get('continuation'):
                generator, key = continuation_credentials()
            else:
                generator, key = credentials(zhipu_env_file) if zhipu_env_file is not None else credentials()
            before()
            from app.runtime.sol_natural_provider import SolNaturalProviderFactory
            factory = SolNaturalProviderFactory(generator_settings=generator, api_key=key,
                                                 transport_root=session.transport_root.parent)
            derived = Path(plan['operator'])/'derived'
            derived.mkdir(exist_ok=True)
            segment = derived/f'{len(list(derived.iterdir()))+1:04d}'
            segment.mkdir(exist_ok=False)
            prepared = base.build_application(provider_factory=factory, output_root=segment,
                run_id=plan['run_id'], candidate=contract, execution_session=session)
            try:
                result = prepared.run()
            finally:
                write_new_json(session.root/f'derived-{segment.name}.json',
                    dict(segment=segment.name, files=inventory(segment)))
                session._checkpoint('derived_segment_retained')
            if result.output.report is not None or result.publication_status.value != 'rejected':
                raise SessionBlocked('launch_unqualified_publication')
            outcome_path = session.journal_root/'outcome.json'
            outcome = json.loads(outcome_path.read_bytes()) if outcome_path.exists() else None
            session.close(dict(runtime_status=result.runtime_status.value, candidate_outcome=outcome,
                               publication_allowed=False, production_admitted=False))
    except SessionPaused as error:
        return dict(phase='paused', reason=str(error), publication_allowed=False, production_admitted=False)
    return dict(phase='closed', publication_allowed=False, production_admitted=False)


def replay(plan, plan_sha, event_source, *, guard, checkpoint, authorization_sha):
    """Full local application replay into a disposable derived directory; no IO."""
    from app.providers.config import ZhipuSettings
    from app.runtime.sol_natural_provider import SolNaturalProviderFactory
    operator = Path(plan['operator'])
    before = inventory(operator)
    session, gate = session_for(plan, plan_sha, event_source, guard=guard, checkpoint=checkpoint,
        read_only=True, authorization_sha=authorization_sha)
    with session:
        if not session.status()['closed']:
            raise ValueError('launch_replay_requires_terminal')
        verify_derived(plan, session)
        saved_launch = json.loads((session.root/'launch.json').read_bytes())
        if (saved_launch['authorization_sha256'] != authorization_sha
                or digest((session.root/'authorization.json').read_bytes()) != authorization_sha
                or saved_launch['plan_sha256'] != plan_sha):
            raise ValueError('launch_replay_controls_changed')
        verify_preflight(plan, plan_sha, event_source, saved_launch['native_preflight'])
        terminal = json.loads((session.root/'terminal.json').read_bytes())
        decisions = [gate.native.replay(handle) for handle in gate.handles()]
        # A semantic rejection terminates at the imported decision, before
        # another app segment. It must remain a rejection in closure.
        if terminal.get('reason') == 'semantic_rejected':
            if not decisions or decisions[-1] is not False:
                raise ValueError('launch_replay_rejection_missing')
            result = dict(phase='closed', reason='semantic_rejected', strict_replay=True,
                publication_allowed=False, production_admitted=False)
        else:
            if not all(decisions):
                raise ValueError('launch_replay_rejection_ignored')
            factory = SolNaturalProviderFactory(generator_settings=ZhipuSettings(
                api_key='OFFLINE_REPLAY_NO_SEND', base_url='https://open.bigmodel.cn/api/paas/v4',
                model='glm-5.3-flash'), api_key='OFFLINE_REPLAY_NO_SEND',
                transport_root=session.transport_root.parent)
            with TemporaryDirectory(prefix='sol-launch-readback-') as directory:
                prepared = base.build_application(provider_factory=factory, output_root=directory,
                    run_id=plan['run_id'], candidate=contract, execution_session=session)
                application = prepared.run()
            if (application.output.report is not None or application.publication_status.value != 'rejected'
                    or application.runtime_status.value != terminal['value']['runtime_status']
                    or session.cursor != session.status()['operations']):
                raise ValueError('launch_replay_terminal_mismatch')
            outcome_path = session.journal_root/'outcome.json'
            outcome = json.loads(outcome_path.read_bytes()) if outcome_path.exists() else None
            if outcome != terminal['value']['candidate_outcome']:
                raise ValueError('launch_replay_outcome_changed')
            result = dict(phase='closed', strict_replay=True, candidate_outcome=outcome,
                publication_allowed=False, production_admitted=False)
        results = [json.loads(path.read_bytes())['value'] for path in
                   sorted((session.root/'operations').glob('*-result.json'))]
        budgets = [row['budget'] for row in results if isinstance(row, dict) and 'budget' in row]
        budget = budgets[-1] if budgets else dict(calls=0, tokens=0, reserved_tokens=0, retries=0)
        result['accounting'] = {k: budget[k] for k in ('calls', 'tokens', 'reserved_tokens', 'retries')}
        result['native_reviews'] = len(decisions)
        if plan.get('continuation'):
            parent = plan['continuation']
            result['continuation'] = dict(parent_seal_sha256=parent['seal_sha256'],
                historical_failure_retained=True, imported_generation_calls=2,
                new_calls=budget['calls']-parent['historical_budget']['calls'],
                new_known_tokens=budget['tokens']-parent['historical_budget']['tokens'])
    if inventory(operator) != before:
        raise ValueError('launch_replay_mutated_originals')
    return result


def seal(plan, plan_sha, event_source, **roots):
    operator = Path(plan['operator'])
    path = operator/'seal.json'
    if path.exists():
        raise ValueError('launch_seal_already_exists')
    checked = replay(plan, plan_sha, event_source, **roots)
    files = inventory(operator)
    write_new_json(path, dict(version=VERSION+'-seal', plan_sha256=plan_sha,
        original_roots=roots, inventory=files, result=checked))
    return dict(sealed=True, seal_sha256=digest(path.read_bytes()), **checked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'native-task', 'task', 'submit', 'run', 'status', 'replay', 'seal'))
    parser.add_argument('--operator', required=True, type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--run-id')
    parser.add_argument('--primary')
    parser.add_argument('--independent')
    parser.add_argument('--parent-operator', type=Path)
    parser.add_argument('--parent-seal-sha')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--guard-sha')
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--authorization-sha')
    parser.add_argument('--authorization-file', type=Path)
    parser.add_argument('--zhipu-env-file', type=Path)
    parser.add_argument('--ci-run')
    parser.add_argument('--preflight-guard-sha')
    parser.add_argument('--preflight-checkpoint-sha')
    parser.add_argument('--key')
    parser.add_argument('--primary-file', type=Path)
    parser.add_argument('--event-id')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not all((args.run_id, args.primary, args.independent)):
            parser.error('prepare requires run-id, primary and independent')
        if bool(args.parent_operator) != bool(args.parent_seal_sha):
            parser.error('continuation requires parent-operator and parent-seal-sha')
        emit(prepare(args.operator, args.run_id, args.primary, args.independent,
                     parent_operator=args.parent_operator, parent_seal_sha=args.parent_seal_sha))
        return
    plan = load(args.operator, args.plan_sha, frozen=args.action in ('native-task', 'run', 'replay', 'seal'))
    with host(plan) as event_source:
        common = dict(preflight=args.preflight, guard=args.guard_sha,
            checkpoint=args.checkpoint_sha, authorization_sha=args.authorization_sha)
        if args.action in ('task', 'submit', 'status', 'replay', 'seal') and not all((args.guard_sha, args.checkpoint_sha)):
            parser.error('existing session requires original guard and latest checkpoint')
        if args.action == 'native-task':
            emit(native_task(plan, args.plan_sha, event_source))
        elif args.action == 'task':
            print(inspect_task(plan, args.plan_sha, event_source, **common), end='')
        elif args.action == 'submit':
            if not all((args.key, args.primary_file, args.event_id)):
                parser.error('submit requires key, primary-file and event-id')
            emit(submit(plan, args.plan_sha, event_source, args.key, args.primary_file, args.event_id, **common))
        elif args.action == 'status':
            session, gate = session_for(plan, args.plan_sha, event_source, read_only=True, **common)
            with session:
                gate.verify_prior()
                emit(session.status())
        elif args.action in ('replay', 'seal'):
            if args.preflight or not args.authorization_sha:
                parser.error('execution replay requires the original authorization SHA')
            common.pop('preflight')
            action = replay if args.action == 'replay' else seal
            emit(action(plan, args.plan_sha, event_source, **common))
        else:
            if args.preflight or not all((args.authorization_file, args.authorization_sha, args.ci_run,
                                          args.preflight_guard_sha, args.preflight_checkpoint_sha)):
                parser.error('run requires authorization, CI and original native preflight roots')
            emit(execute(plan, args.plan_sha, event_source, authorization_file=args.authorization_file,
                authorization_sha=args.authorization_sha, ci_run=args.ci_run,
                preflight_proof=dict(guard_sha256=args.preflight_guard_sha,
                    checkpoint_sha256=args.preflight_checkpoint_sha),
                guard=args.guard_sha, checkpoint=args.checkpoint_sha,
                zhipu_env_file=args.zhipu_env_file))


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        # Only allow local fixed validation codes; never provider/OS text.
        message = str(error)
        code = message if type(error) in (ValueError, SessionBlocked, SessionPaused) and re.fullmatch(
            r'(launch|session|natural|boundary_v2|codex_review_host)_[a-z0-9_]+', message) else 'execution_error'
        emit(dict(ok=False, code=code, error_type=type(error).__name__, publication_allowed=False))
        raise SystemExit(1) from None
