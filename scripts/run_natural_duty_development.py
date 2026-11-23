"""Prepare, execute once after a fresh grant, or replay one natural development task.

Preparation never loads credentials or sends requests. Execution keeps the
candidate's shared Runtime budget and unconditional publication rejection.
"""
import argparse
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import subprocess

from app.evaluation.golden_journal import write_new_json
from app.evaluation.natural_duty_contract import NaturalDutyProvider, ROOT, request_bytes
from app.runtime.dispatch_control import bind_dispatch_guard, DispatchStopped
from scripts.natural_duty_preparation import prepare, build_application, sha, canonical, inventory, LIMITS
from scripts.natural_duty_receipts import summarize, replay, validate_roots

RUN_ID = 'natural-duty-observed-20261015'
RUN_DIRECTORY = ROOT/'data/runs/model_comparison'/RUN_ID
GRANT_VERSION = 'natural-duty-observed-development-v1-authorization'


def emit(value):
    print(json.dumps(value, ensure_ascii=True, separators=(',', ':')), flush=True)


def current_head():
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('natural_clean_checkout_required')
    return head


def verify_ci(ci_run, expected_head):
    if current_head()!=expected_head:
        raise ValueError('natural_exact_head_required')
    env = dict(os.environ)
    env.update(HTTP_PROXY='http://127.0.0.1:12000', HTTPS_PROXY='http://127.0.0.1:12000')
    raw = subprocess.check_output(['gh','run','view',str(ci_run),'--json','headSha,status,conclusion,jobs'],
                                   cwd=ROOT, env=env, timeout=60)
    value = json.loads(raw)
    expected_jobs = {'web-checks','postgres-migrations','packaging-smoke',*(f'pytest-shards ({i})' for i in range(4))}
    names = {j['name'] for j in value['jobs']}
    if (value['headSha']!=expected_head or value['status']!='completed' or value['conclusion']!='success'
            or not expected_jobs.issubset(names) or any(j['conclusion']!='success' for j in value['jobs'])):
        raise ValueError('natural_exact_head_public_ci_required')
    return dict(run_id=str(ci_run), head_sha=expected_head, status='completed', conclusion='success', jobs=sorted(names))


def validate_grant(grant, plan, head, *, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    issued = datetime.fromisoformat(grant['issued_at'])
    expires = datetime.fromisoformat(grant['expires_at'])
    if (issued.utcoffset() is None or expires.utcoffset() is None or not issued<=now<expires
            or not timedelta(0)<expires-issued<=timedelta(days=1)
            or grant.get('version')!=GRANT_VERSION or grant.get('run_id')!=RUN_ID
            or grant.get('execution_head')!=head or grant.get('limits')!=LIMITS
            or grant.get('preparation_plan_sha256')!=plan['preparation_plan_sha256']
            or grant.get('estimated_uncached_cny')!=plan['reservation_estimate']['estimated_uncached_cny']
            or grant.get('retry_authorized') is not False or grant.get('production_admitted') is not False
            or not isinstance(grant.get('user_authorization_evidence'),str) or not grant['user_authorization_evidence'].strip()):
        raise ValueError('natural_fresh_specific_authorization_required')


class FirstRequestFactory:
    """Keep the exact router type; bind its first child before any IO reservation."""
    def __init__(self, delegate, first):
        self.delegate, self.first, self.descriptor = delegate, first, delegate.descriptor
        self.used = self.matched = False

    def __call__(self, run_id):
        if self.used:
            raise ValueError('natural_factory_already_used')
        self.used = True
        routed = self.delegate(run_id)
        outer = self

        class FirstChild:
            def __getattr__(self, name):
                return getattr(routed.generator, name)

            def chat_at_ordinal(self, request, *, ordinal, role):
                if not outer.matched:
                    if (ordinal!=1 or role!='generation' or not 0<request.timeout_s<=outer.first.timeout_s
                            or replace(request, timeout_s=outer.first.timeout_s)!=outer.first):
                        raise ValueError('natural_first_request_changed')
                    outer.matched = True
                return routed.generator.chat_at_ordinal(request, ordinal=ordinal, role=role)

        self.provider = NaturalDutyProvider(FirstChild(), routed.reviewer, source_projection=routed.source_projection)
        return self.provider


def execute(*, preparation_file, authorization_file, ci_run, env_file, operator_directory):
    # All semantic, budget and source preparation precedes credentials/run claims.
    first, plan = prepare(RUN_ID)
    saved = json.loads(Path(preparation_file).read_bytes())
    if saved != plan:
        raise ValueError('natural_saved_preparation_changed')
    raw_grant = Path(authorization_file).read_bytes()
    grant = json.loads(raw_grant)
    head = current_head()
    validate_grant(grant, plan, head)
    ci = verify_ci(ci_run, head)
    operator_directory = Path(operator_directory).resolve()
    run_directory = RUN_DIRECTORY.resolve()
    if operator_directory.is_relative_to(run_directory) or run_directory.is_relative_to(operator_directory):
        raise ValueError('natural_operator_must_be_separate')
    operator_directory.mkdir(parents=True, exist_ok=True)
    if run_directory.exists() or any((operator_directory/n).exists() for n in ('claim.json','guard.json','closure.json')):
        raise FileExistsError('natural_run_or_claim_already_exists')
    # Cross-process exclusive claim. It remains even if startup fails.
    write_new_json(operator_directory/'claim.json', dict(run_id=RUN_ID, head=head, plan_sha256=plan['preparation_plan_sha256']))
    run_directory.mkdir(parents=True, exist_ok=False)
    guard = dict(version='natural-duty-execution-guard-v1', run_id=RUN_ID, run_directory=str(run_directory),
        head=head, ci=ci, authorization_sha256=sha(raw_grant), plan_sha256=plan['preparation_plan_sha256'],
        first_request_sha256=sha(request_bytes(first)), component_inventory_sha256=plan['component_inventory_sha256'])
    write_new_json(operator_directory/'guard.json', guard)
    guard_sha = sha((operator_directory/'guard.json').read_bytes())
    emit(dict(event='execution_guard', guard_sha256=guard_sha, run_id=RUN_ID))
    outcome = dict(version='natural-duty-development-result-v1', run_id=RUN_ID, status='failed',
        publication_allowed=False, semantic_approval=False, original_15_qualified=False,
        production_admitted=False, guard_sha256=guard_sha, first_request_matched=False)
    factory = None
    observed_inventory = {}
    observation_ordinal = 0

    def observe_transport():
        nonlocal observed_inventory, observation_ordinal
        validate_roots(run_directory,guard)
        if sha((operator_directory/'guard.json').read_bytes())!=guard_sha:
            raise ValueError('natural_original_guard_changed')
        transport = run_directory/'transport'/RUN_ID
        actual = inventory(transport.rglob('*'),root=transport)
        if any(actual.get(k)!=v for k,v in observed_inventory.items()):
            raise ValueError('natural_previous_transport_changed')
        accounting = summarize(transport)
        if actual != observed_inventory:
            observation_ordinal += 1
            write_new_json(operator_directory/f'observation-{observation_ordinal:03d}.json',
                dict(guard_sha256=guard_sha, transport_inventory=actual, accounting=accounting))
            observed_inventory = actual
        return accounting

    try:
        write_new_json(run_directory/'plan.json', plan)
        with (run_directory/'authorization.json').open('xb') as stream:
            stream.write(raw_grant)
        with (run_directory/'first-request.json').open('xb') as stream:
            stream.write(request_bytes(first))
        from scripts.run_role_coach_development import load_role_settings
        from app.runtime.natural_duty_provider_factory import NaturalDutyProviderFactory
        settings = load_role_settings(env_file)
        factory = FirstRequestFactory(NaturalDutyProviderFactory(generator_settings=settings[0],
            reviewer_settings=settings[1], transport_root=run_directory/'transport'), first)
        prepared = build_application(provider_factory=factory, output_root=run_directory, run_id=RUN_ID)

        def before_send():
            try:
                validate_grant(grant, plan, head)
                if Path(authorization_file).read_bytes()!=raw_grant or current_head()!=head:
                    raise ValueError('natural_execution_identity_changed')
                actual = inventory((ROOT/p for p in plan['component_files']))
                if actual != plan['component_files']:
                    raise ValueError('natural_components_changed')
                # Revalidate every previous complete receipt before another send.
                observe_transport()
                budget = factory.provider.candidate_budget
                if budget.clock()-budget.started >= LIMITS['execution_timeout_s']:
                    raise ValueError('natural_shared_deadline_exhausted')
            except Exception:
                raise DispatchStopped('natural_execution_preflight_failed') from None

        with bind_dispatch_guard(before_send):
            result = prepared.run()
        if result.output.report is not None or result.publication_status.value!='rejected':
            raise ValueError('natural_unqualified_publication')
        outcome.update(status='completed_unqualified', runtime_status=result.runtime_status.value,
                       application_publication_status=result.publication_status.value)
    except BaseException as error:
        outcome.update(status='cancelled' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'failed',
                       error_type=type(error).__name__)
    finally:
        outcome['first_request_matched'] = bool(factory and factory.matched)
        try:
            journal = run_directory/'reports'/RUN_ID/'natural-duty-journal/outcome.json'
            outcome['candidate_outcome'] = json.loads(journal.read_bytes()) if journal.exists() else None
            outcome['accounting'] = observe_transport()
            if (outcome['status']=='completed_unqualified' and (outcome['candidate_outcome'] or {}).get('outcome')
                    not in ('candidate_initial_pass_unqualified','candidate_repaired_pass_unqualified')):
                outcome['status'] = 'stopped_unqualified'
        except Exception as error:
            outcome.update(status='failed', accounting=dict(accounting_status='invalid_receipts',
                reserved_calls=None, completed_calls=None, unknown_usage_calls=None, error_type=type(error).__name__))
        write_new_json(run_directory/'result.json', outcome)
        closure = dict(version='natural-duty-closure-v1', run_id=RUN_ID, guard_sha256=guard_sha,
            run_inventory=inventory(run_directory.rglob('*'),root=run_directory), status=outcome['status'],
            operator_observations=inventory(operator_directory.glob('observation-*.json'),root=operator_directory))
        write_new_json(operator_directory/'closure.json', closure)
        closure_sha = sha((operator_directory/'closure.json').read_bytes())
        emit(dict(event='execution_closed', guard_sha256=guard_sha, closure_sha256=closure_sha,
                  status=outcome['status'], accounting=outcome['accounting']))
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare','execute','replay'))
    parser.add_argument('--preparation-file', type=Path, required=True)
    parser.add_argument('--request-file', type=Path)
    parser.add_argument('--authorization-file', type=Path)
    parser.add_argument('--operator-directory', type=Path)
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--guard-sha')
    parser.add_argument('--closure-sha')
    args = parser.parse_args()
    if args.mode=='prepare':
        first, plan = prepare(RUN_ID)
        write_new_json(args.preparation_file, plan)
        if args.request_file:
            with args.request_file.open('xb') as stream:
                stream.write(request_bytes(first))
        emit({k:v for k,v in plan.items() if k not in ('component_files','actual_compiled_task')})
    elif args.mode=='execute':
        if any(getattr(args,k) is None for k in ('authorization_file','operator_directory','ci_run','env_file')):
            raise ValueError('natural_execute_arguments_required')
        result = execute(preparation_file=args.preparation_file, authorization_file=args.authorization_file,
            ci_run=args.ci_run, env_file=args.env_file, operator_directory=args.operator_directory)
        if result['status']!='completed_unqualified':
            raise SystemExit(1)
    else:
        if not args.operator_directory or not args.guard_sha or not args.closure_sha:
            raise ValueError('natural_replay_original_stdout_roots_required')
        emit(replay(run_directory=RUN_DIRECTORY, operator_directory=args.operator_directory,
                    guard_sha=args.guard_sha, closure_sha=args.closure_sha))


if __name__=='__main__':
    main()
