"""Prospective original15 execution; prepare is offline, execute requires a pinned grant.

Reuses the frozen full-chain state machine, author workspace and observed worker.
No authorization issuer, retry/resume command or product registration is provided.
"""
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import re

from scripts.full_chain_evidence import FullChainEvidence, ROOT, sha
from scripts import qualify_full_chain_controls as qualification

VERSION = 'full-chain-controls-execution-v1'
AUTH_VERSION = VERSION + '-authorization'
RUN_ID = 'document-full-chain-controls-20261013-v1'
SOURCES = ('scripts/full_chain_execution.py', 'scripts/qualify_full_chain_controls.py')


def fail(code):
    raise ValueError('full_chain_execution_' + code)


def budget_for(plan):
    from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
    roles = {'glm-5.3': 25, 'glm-5.3-flash': 10}
    prices = DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles
    cost = sum(n * (Decimal(64000) * prices['zhipu', model].input_cost_per_million
        + Decimal(32768) * prices['zhipu', model].output_cost_per_million) / 1_000_000
        for model, n in roles.items())
    return dict(max_calls=35, role_calls=roles, max_tokens=35 * 96768,
        max_active_seconds=15 * 900, max_host_seconds=86400, per_request_output=32768,
        per_request_seconds={'review':600, 'generation':300, 'revision':300},
        estimated_uncached_cny=str(cost), hard_billing_cap=False)


class ControlledFullChain(FullChainEvidence):
    def __init__(self, **kwargs):
        self.authorization_guard = lambda: None
        super().__init__(**kwargs)

    def prepare(self, **kwargs):
        plan = super().prepare(**kwargs)
        plan.update(execution_profile=VERSION, run_id=RUN_ID, budget=budget_for(plan))
        plan['source_sha256'].update({p: sha(ROOT/p) for p in SOURCES})
        return plan

    def check(self):
        # Also reached at Host polling, submit and the final child IO boundary.
        # Closed read-only sessions have no authorization guard installed.
        self.authorization_guard()
        return super().check()


def proposal(session):
    principals = qualification.PRINCIPALS
    plan = session.prepare(root_thread_id=principals['primary'],
        independent_thread_id=principals['independent'])
    prepared = qualification.prepare(execution_profile=VERSION)
    qualification.require_plan(dict(preparation_plan=plan,
        plan_sha256=session.runner.canonical_sha(plan), execution_head='0'*40, ci_run='1'), prepared)
    return dict(kind=VERSION, plan=plan, operator=str(session.workspace.answers.parent),
        plan_sha256=session.runner.canonical_sha(plan),
        qualification_preparation=prepared, execution_authorized=False)


def external_path(path, session):
    path = Path(path).absolute()
    roots = (*session.workspace.evidence_roots, session.workspace.answers, session.observations)
    if path.resolve() != path or any(path.is_relative_to(p.resolve()) for p in roots):
        fail('operator_path_inside_evidence')
    return path


def require_unused(session, operator):
    session.validate_paths()
    # Empty directories also count as used. Never clean up a failed attempt to retry.
    if any(p.exists() for p in (session.directory, session.workspace.answers, session.observations,
                               operator/'execution.json')):
        fail('already_started')


def require_authorization(path, expected_sha, prepared_sha, *, now=None):
    grant = qualification.pinned(path, expected_sha)
    if (set(grant) != {'kind', 'authorized', 'preparation_sha256', 'execution_head', 'ci_run',
                      'issued_at', 'expires_at'}
            or grant['kind'] != AUTH_VERSION or grant['authorized'] is not True
            or grant['preparation_sha256'] != prepared_sha
            or not re.fullmatch('[0-9a-f]{40}', str(grant['execution_head']))
            or not re.fullmatch('[1-9][0-9]*', str(grant['ci_run']))):
        fail('authorization_binding')
    try:
        issued = datetime.fromisoformat(grant['issued_at'])
        expires = datetime.fromisoformat(grant['expires_at'])
        current = now if now is not None else datetime.now(timezone.utc)
        valid = (issued.tzinfo is not None and expires.tzinfo is not None
            and issued <= current < expires and timedelta(0) < expires-issued <= timedelta(days=1))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        fail('authorization_expired_or_invalid')
    return grant


def load_proposal(path, expected_sha):
    saved = qualification.pinned(path, expected_sha)
    session = ControlledFullChain(**saved['plan']['evidence_paths'])
    if saved != proposal(session):
        fail('preparation_changed')
    # Production execution uses one fixed run path, never a caller-chosen retry suffix.
    if session.directory != ROOT/'data/runs/model_comparison'/RUN_ID:
        fail('run_path')
    return session, saved


def execute(*, preparation, preparation_sha, authorization, authorization_sha,
            operator, env_file, codex_executable):
    session, saved = load_proposal(preparation, preparation_sha)
    operator = external_path(operator, session)
    if str(operator) != saved['operator']:
        fail('operator_binding')
    preparation = external_path(preparation, session)
    authorization = external_path(authorization, session)
    plan, runner = saved['plan'], session.runner
    require_unused(session, operator)
    grant = require_authorization(authorization, authorization_sha, preparation_sha)

    def authorized():
        if sha(preparation) != preparation_sha:
            fail('preparation_changed')
        require_authorization(authorization, authorization_sha, preparation_sha)

    def before_send():
        authorized()
        runner.require_unchanged_checkout(grant['execution_head'])

    # Public CI querying inherits the operator's process-only GitHub proxy.
    # No credentials, factory or business directory is touched before these gates.
    if runner.verify_public_ci(str(grant['ci_run'])) != grant['execution_head']:
        fail('execution_head')
    startup = session.execution_paths_preflight()
    with runner.CodexReadOnlyClient(codex_executable) as client:
        native = runner.verify_native_principals(client, plan)
        source = runner.CodexHostReviewEventSource(client, plan)
        runner.require_execution_event_source(plan, source)
        if saved != proposal(session):
            fail('preparation_changed')
        before_send()
        require_unused(session, operator)
        operator.mkdir(parents=True, exist_ok=True)
        # Exclusive claim precedes secret access. Survives failures and is never removed.
        runner._write_json(operator/'execution.json', dict(kind=VERSION,
            preparation_sha256=preparation_sha, authorization_sha256=authorization_sha,
            execution_head=grant['execution_head'], ci_run=grant['ci_run'], startup=startup, native=native,
            started_at=datetime.now(timezone.utc).isoformat(), provider_calls_at_claim=0))
        session.authorization_guard = authorized
        observe_started = False
        try:
            before_send()
            generator, reviewer = runner.load_role_settings(env_file)
            session.directory.mkdir(parents=True, exist_ok=False)
            runner._write_json(session.directory/'plan.json', dict(preparation_plan=plan,
                plan_sha256=saved['plan_sha256'], execution_head=grant['execution_head'], ci_run=grant['ci_run']))
            factory = session.factory(generator_settings=generator, reviewer_settings=reviewer)
            with runner.route_environment('direct'):
                observe_started = True
                result = runner.observe(factory, session.directory, plan, event_source=source,
                                        before_send=before_send)
            runner._write_json(operator/'execution-exit.json', dict(scan_completed=result['scan_completed'],
                diagnostic_accepted=result['diagnostic_accepted'], provider_calls=result['provider_calls'],
                error_code=result.get('error_code'), restart_allowed=False))
            return result
        except BaseException as error:
            # Do not persist exception text: SDK/config errors may contain secrets.
            runner._write_json(operator/'execution-failure.json', dict(error_type=type(error).__name__,
                restart_allowed=False, provider_calls_unknown=observe_started))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'execute', 'task', 'submit', 'abort', 'replay', 'seal'))
    for name in ('preparation', 'authorization', 'operator', 'env-file', 'codex-executable', 'output',
                 'directory', 'answers', 'observations', 'cwd', 'python', 'notes'):
        parser.add_argument('--'+name, type=Path)
    for name in ('preparation-sha', 'authorization-sha', 'key', 'stage', 'event-id', 'checkpoint-sha', 'reason'):
        parser.add_argument('--'+name)
    args = parser.parse_args()
    def need(*names):
        if any(getattr(args, n) is None for n in names):
            parser.error('required: ' + ', '.join(names))
    if args.action == 'execute':
        fields = ('preparation', 'preparation_sha', 'authorization', 'authorization_sha', 'operator',
                  'env_file', 'codex_executable')
        need(*fields)
        try:
            result = execute(**{n:getattr(args, n) for n in fields})
        except Exception as error:
            # No traceback/SDK exception text on the public CLI either.
            raise SystemExit('full_chain_execution_failed: ' + type(error).__name__) from None
        print(json.dumps(dict(scan_completed=result['scan_completed'],
            diagnostic_accepted=result['diagnostic_accepted'], provider_calls=result['provider_calls'])))
        if not result['scan_completed']: raise SystemExit(1)
        return
    paths = ('directory', 'answers', 'observations', 'cwd', 'python')
    need(*paths)
    session = ControlledFullChain(**{n:getattr(args, n) for n in paths})
    runner, evidence = session.runner, session.evidence
    if args.action == 'prepare':
        need('output')
        output = external_path(args.output, session)
        if output.exists(): raise FileExistsError(output)
        session.execution_paths_preflight()
        value = proposal(session)
        runner._write_json(output, value)
        print(json.dumps(dict(preparation_sha256=sha(output), budget=value['plan']['budget'],
                              execution_authorized=False, provider_calls=0)))
        return
    if args.action in ('task', 'submit', 'abort'): need('key', 'stage')
    if args.action == 'task':
        session.check()
        print(evidence.task(session.directory, args.key, args.stage)); return
    if args.action == 'abort':
        need('reason')
        print(runner.compact(evidence.abort(session.directory, args.key, args.stage, args.reason))); return
    need('codex_executable')
    plan = evidence.load_plan(session.directory)
    with runner.CodexReadOnlyClient(args.codex_executable) as client:
        source = runner.CodexHostReviewEventSource(client, plan)
        if args.action == 'submit':
            need('notes', 'event_id', 'checkpoint_sha')
            value = evidence.submit(session.directory, args.key, args.stage, evidence.read(args.notes),
                                    args.event_id, source, args.checkpoint_sha)
        elif args.action == 'seal':
            need('output')
            value = evidence.seal(session.directory, args.output, event_source=source)
        else:
            value = evidence.replay(session.directory, event_source=source)
    print(runner.compact(value))


if __name__ == '__main__':
    main()
