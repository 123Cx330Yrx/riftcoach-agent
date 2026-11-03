"""One authorized fixed-report development run; no grant issuer or retry path."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version as installed_version
import json
from pathlib import Path
import subprocess
import sys
import time

from pydantic import TypeAdapter

from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_review_experiment import SourceIndex
from app.evaluation.golden_journal import write_new_json
from scripts import review_duty_execution as execution
from scripts import review_duty_transport as transport
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.full_chain_modules import private_module
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.prepare_review_duty_execution import load_inputs
from scripts.review_duty_host_gate import Decision, sha
from scripts.review_independence_contract import require_execution_event_source, canonical_json
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import require_unchanged_checkout, load_role_settings

ROOT = execution.ROOT
VERSION = 'review-duty-chain-launch-v1'
RUN = ROOT/'data/runs/model_comparison/review-duty-chain-20261014'
PACKAGE = ROOT/'data/evaluation/fixtures/review_duty_chain_20261014'
PRIMARY = '01a1248f-e18c-7282-92bf-7ceb2eb5dce4'
INDEPENDENT = '01a12f0c-bb7c-74e3-ad92-775eefbe399a'
CODEX = Path('C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe')
AUTH_VERSION = VERSION+'-authorization'


def read(path):
    return json.loads(Path(path).read_bytes())


def pinned(path, digest):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink() or path.stat().st_nlink != 1 or sha(path) != digest:
        raise ValueError('duty_launch_pin')
    return read(path)


def source_inventory():
    # Conservative superset of transitive project code, including dynamically
    # loaded old modules. Packaged inputs remove runtime dependence on old labels.
    paths = {p for base in ('app','scripts') for p in (ROOT/base).rglob('*.py')}
    paths.update(p for base in ('skills','examples/runtime_profiles') for p in (ROOT/base).rglob('*')
        if p.is_file() and p.suffix in ('.md','.json','.yaml','.yml','.toml','.txt','.j2'))
    paths.update(p for name in ('pyproject.toml','uv.lock','requirements.txt') if (p:=ROOT/name).is_file())
    if any(p.resolve()!=p or p.is_symlink() or p.stat().st_nlink!=1 for p in paths):
        raise ValueError('duty_launch_linked_source')
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}


def runtime_identity():
    return dict(python=sys.version,packages={n:installed_version(n) for n in
        ('openai','httpx','pydantic','python-dotenv')})


def create_package():
    inputs = load_inputs()  # Verify the old full input once; do not import old judgments.
    PACKAGE.mkdir(parents=True,exist_ok=False)
    with (PACKAGE/'inputs.json').open('xb') as file:
        file.write(execution.request_bytes(inputs))
    for duty in execution.duty.DUTIES:
        with (PACKAGE/(duty+'-initial.json')).open('xb') as file:
            file.write(execution.request_bytes(execution.duty.review_request(inputs,duty)))
    return package_inventory()


def package_inventory():
    if PACKAGE.resolve()!=PACKAGE or not PACKAGE.is_dir():
        raise ValueError('duty_launch_package_path')
    files = {p.name:sha(p) for p in PACKAGE.iterdir() if p.is_file()}
    if set(files)!={'inputs.json','facts-initial.json','completion-initial.json'} or len(list(PACKAGE.iterdir()))!=3:
        raise ValueError('duty_launch_package_inventory')
    for p in PACKAGE.iterdir():
        if p.is_symlink() or p.resolve()!=p or p.stat().st_nlink!=1:
            raise ValueError('duty_launch_package_link')
    return files


def packaged_inputs():
    package_inventory()
    inputs = TypeAdapter(ReviewInput).validate_json((PACKAGE/'inputs.json').read_bytes())
    if SourceIndex.build(inputs.source.report,json.loads(inputs.pack_json)) != inputs.source:
        raise ValueError('duty_launch_input_source')
    if execution.report_inputs(inputs,inputs.source.report) != inputs:
        raise ValueError('duty_launch_input_projection')
    for duty in execution.duty.DUTIES:
        if (PACKAGE/(duty+'-initial.json')).read_bytes()!=execution.request_bytes(execution.duty.review_request(inputs,duty)):
            raise ValueError('duty_launch_initial_binding')
    return inputs


def external(path):
    path=Path(path).absolute()
    if path.resolve()!=path or path.is_relative_to(ROOT/'data/runs') or path.is_relative_to(PACKAGE):
        raise ValueError('duty_launch_external_path')
    return path


def control_path(path, saved):
    path = external(path)
    operator = Path(saved['operator'])
    if any(path.is_relative_to(operator/name) for name in ('author-answers','observations','host-controls')):
        raise ValueError('duty_launch_control_inside_evidence')
    return path


def proposal(operator, python):
    operator,python=external(operator),Path(python).absolute()
    if operator.is_relative_to(ROOT):
        raise ValueError('duty_launch_operator_outside_checkout')
    workspace=HostReviewWorkspace(cwd=ROOT,python=python,answers=operator/'author-answers',evidence_roots=(ROOT/'data/runs',))
    inputs=packaged_inputs()
    plan=execution.preparation(inputs,primary=PRIMARY,independent=INDEPENDENT)
    return dict(kind=VERSION,operator=str(operator),run=str(RUN),python=str(workspace.python),cwd=str(ROOT),
        plan=plan,plan_sha256=hashlib.sha256(canonical_json(plan)).hexdigest(),
        source_sha256=source_inventory(),package_sha256=package_inventory(),runtime=runtime_identity(),
        execution_ready=True,execution_authorized=False,production_admitted=False,
        budget=dict(maximum_calls=5,glm_high=4,flash_high=1,maximum_tokens=483840,
            maximum_active_seconds=2700,maximum_host_seconds=86400,per_review_seconds=600,
            per_edit_seconds=300,per_request_output=32768,uncached_cny='5.8609664',hard_billing_cap=False))


def validate_preparation(path, digest):
    path=external(path)
    saved=pinned(path,digest)
    if saved!=proposal(saved['operator'],saved['python']):
        raise ValueError('duty_launch_preparation_changed')
    control_path(path,saved)
    return saved


def authorization(path, digest, preparation_sha, *, now=None):
    # Reuse the established exact-schema, maximum-24h grant validator privately.
    module=private_module(ROOT/'scripts/full_chain_execution.py',{})
    module.AUTH_VERSION=AUTH_VERSION
    pinned(external(path),digest)
    return module.require_authorization(path,digest,preparation_sha,now=now)


def startup(saved):
    python=Path(saved['python'])
    if python.resolve()!=Path(sys.executable).resolve() or Path.cwd().resolve()!=ROOT.resolve():
        raise ValueError('duty_launch_actual_interpreter_or_cwd')
    result=subprocess.run([str(python),'-B','-c',
        'import json,os,sys; from pathlib import Path; import scripts.review_duty_launch as m; '
        'print(json.dumps(dict(cwd=os.getcwd(),python=sys.executable,module=str(Path(m.__file__).resolve())),ensure_ascii=True))'],
        cwd=saved['cwd'],capture_output=True,text=True,encoding='utf-8',timeout=30,check=True)
    proof=json.loads(result.stdout)
    if (Path(proof['cwd']).resolve()!=ROOT.resolve() or Path(proof['python']).resolve()!=python.resolve()
            or Path(proof['module']).resolve()!=(ROOT/'scripts/review_duty_launch.py').resolve()):
        raise ValueError('duty_launch_startup_identity')
    return proof


def unused(saved):
    operator=Path(saved['operator'])
    if any(p.exists() or p.is_symlink() or p.resolve()!=p for p in (RUN,operator/'author-answers',operator/'observations',
            operator/'execution.json',operator/'worker-guard.json',operator/'host-controls',
            operator/'execution-exit.json',operator/'execution-failure.json')):
        raise ValueError('duty_launch_already_started')


def require_guard(path, digest, prepared=None, *, closed=False):
    proof=pinned(external(path),digest)
    saved=validate_preparation(proof['preparation'],proof['preparation_sha256'])
    operator=Path(saved['operator'])
    if Path(path)!=operator/'worker-guard.json':
        raise ValueError('duty_launch_guard_path')
    claim=pinned(operator/'execution.json',proof['claim_sha256'])
    auth_path=control_path(proof['authorization'],saved)
    grant=authorization(auth_path,proof['authorization_sha256'],proof['preparation_sha256'],
        now=datetime.fromisoformat(claim['started_at']) if closed else None)
    if (claim['preparation_sha256']!=proof['preparation_sha256'] or claim['authorization_sha256']!=proof['authorization_sha256']
            or claim['execution_head']!=grant['execution_head'] or claim['ci_run']!=grant['ci_run']):
        raise ValueError('duty_launch_claim_binding')
    if prepared is not None and Path(prepared) not in {RUN/s/'prepared-request.json' for s in execution.SLOTS}:
        raise ValueError('duty_launch_child_path')
    if not closed:
        if any((operator/name).exists() for name in ('execution-exit.json','execution-failure.json','host-controls/abort.json')):
            raise ValueError('duty_launch_stopped')
        if Path(sys.executable).resolve()!=Path(saved['python']).resolve() or Path.cwd().resolve()!=ROOT:
            raise ValueError('duty_launch_actual_interpreter_or_cwd')
        require_unchanged_checkout(grant['execution_head'])
    return saved


class HostMailbox:
    def __init__(self, operator, guard):
        self.root=Path(operator)/'host-controls'
        self.guard=guard
        self.session=None
        self.inventory={}
        self.command=None

    def check_controls(self, allowed=()):
        if self.root.resolve()!=self.root:
            raise ValueError('duty_launch_control_link')
        current={}
        for p in self.root.iterdir():
            if not p.is_file() or p.is_symlink() or p.resolve()!=p or p.stat().st_nlink!=1:
                raise ValueError('duty_launch_control_link')
            current[str(p)]=sha(p)
        if (any(current.get(p)!=h for p,h in self.inventory.items())
                or not set(current).difference(self.inventory).issubset({str(p) for p in allowed})):
            raise ValueError('duty_launch_control_changed')
        self.inventory=current

    def __call__(self, handle, available):
        key=handle['binding']['key']
        self.guard()
        self.check_controls()
        pending=self.root/(key+'.pending.json')
        write_new_json(pending,handle)
        self.check_controls((pending,))
        print(json.dumps(dict(host_pending=key,checkpoint=str(Path(handle['folder'])/'task-checkpoint.json'),
            checkpoint_sha256=handle['checkpoint_sha256']),ensure_ascii=True),flush=True)
        started=time.monotonic()
        answer=self.session.workspace.answer_path(Path(handle['folder'])/'task-checkpoint.json',handle['checkpoint_sha256'])
        self.command=self.root/(key+'.submit.json')
        while True:
            self.guard()
            self.session.check(allow_new=(answer,))
            if (self.root/'abort.json').exists():
                raise ValueError('duty_launch_operator_abort')
            command=self.root/(key+'.submit.json')
            self.check_controls((command,))
            if command.exists():
                value=pinned(command,self.inventory[str(command)])
                if (set(value)!={'checkpoint_sha256','primary_decision','event_id'}
                        or value['checkpoint_sha256']!=handle['checkpoint_sha256']):
                    raise ValueError('duty_launch_submit_binding')
                Decision.model_validate(value['primary_decision'])
                self.guard()
                if time.monotonic()-started>=available:
                    raise TimeoutError('duty_launch_host_deadline')
                self.command=None
                return value['primary_decision'],value['event_id']
            if time.monotonic()-started>=available:
                raise TimeoutError('duty_launch_host_deadline')
            time.sleep(min(5,max(.01,available-(time.monotonic()-started))))


def execute(*, preparation, preparation_sha, authorization_path, authorization_sha, env_file, codex_executable):
    saved=validate_preparation(preparation,preparation_sha)
    operator=Path(saved['operator'])
    preparation,authorization_path=control_path(preparation,saved),control_path(authorization_path,saved)
    unused(saved)
    grant=authorization(authorization_path,authorization_sha,preparation_sha)
    if verify_public_ci(grant['ci_run'])!=grant['execution_head']:
        raise ValueError('duty_launch_ci_head')
    startup_proof=startup(saved)
    if Path(codex_executable).resolve()!=CODEX.resolve():
        raise ValueError('duty_launch_codex_path')
    with CodexReadOnlyClient(codex_executable) as client:
        native=verify_native_principals(client,saved['plan'])
        source=CodexHostReviewEventSource(client,saved['plan'])
        require_execution_event_source(saved['plan'],source)
        validate_preparation(preparation,preparation_sha)
        authorization(authorization_path,authorization_sha,preparation_sha)
        require_unchanged_checkout(grant['execution_head'])
        unused(saved)
        operator.mkdir(parents=True,exist_ok=True)
        # Exclusive creation survives failures; credentials are read only after it.
        write_new_json(operator/'execution.json',dict(kind=VERSION,preparation_sha256=preparation_sha,
            authorization_sha256=authorization_sha,execution_head=grant['execution_head'],ci_run=grant['ci_run'],
            startup=startup_proof,native=native,started_at=datetime.now(timezone.utc).isoformat(),provider_calls_at_claim=0))
        guard_path=operator/'worker-guard.json'
        write_new_json(guard_path,dict(preparation=str(preparation),preparation_sha256=preparation_sha,
            authorization=str(authorization_path),authorization_sha256=authorization_sha,
            claim_sha256=sha(operator/'execution.json')))
        guard_sha=sha(guard_path)
        print(json.dumps(dict(execution_guard=str(guard_path),execution_guard_sha256=guard_sha),ensure_ascii=True),flush=True)
        mailbox=None
        def guard():
            require_guard(guard_path,guard_sha)
            if mailbox is not None:
                mailbox.check_controls((mailbox.command,) if mailbox.command else ())
        session=None
        try:
            guard()
            generator,reviewer=load_role_settings(env_file)
            (operator/'host-controls').mkdir(exist_ok=False)
            mailbox=HostMailbox(operator,guard)
            sender=transport.Sender(settings_for_model=lambda model:generator if model=='glm-5.3-flash' else reviewer,
                observation_root=operator/'observations',execution_guard=(guard_path,guard_sha))
            session=execution.DevelopmentChain(directory=RUN,answers=operator/'author-answers',
                observations=operator/'observations',inputs=packaged_inputs(),plan=saved['plan'],
                event_source=source,send=sender,observe=transport.verify,judge=mailbox,before_send=guard)
            mailbox.session=session
            result=session.run()
            controls_valid=True
            try:
                mailbox.check_controls((mailbox.root/'abort.json',))
            except ValueError:
                controls_valid=False
            write_new_json(operator/'execution-exit.json',dict(outcome=result['outcome'],calls=result['calls'],
                guard_sha256=guard_sha,closure_sha256=getattr(session,'closure_sha256',None),
                host_controls_valid=controls_valid,host_control_sha256=mailbox.inventory,restart_allowed=False))
            print(json.dumps(dict(execution_exit_sha256=sha(operator/'execution-exit.json')),ensure_ascii=True),flush=True)
            return result
        except BaseException as error:
            write_new_json(operator/'execution-failure.json',dict(error_type=type(error).__name__,
                calls=session.budget.calls if session and session.budget else 0,restart_allowed=False))
            raise


def host_command(operator,key,*,guard_sha,action,checkpoint_sha=None,notes=None,event_id=None):
    operator=external(operator)
    if key not in (*execution.SLOTS,'compatibility'):
        raise ValueError('duty_launch_stage')
    proof=operator/'worker-guard.json'
    saved=require_guard(proof,guard_sha)
    if saved['operator']!=str(operator):
        raise ValueError('duty_launch_operator_binding')
    control=operator/'host-controls'
    handle=read(control/(key+'.pending.json'))
    folder=RUN/('host-'+key)
    if handle['folder']!=str(folder) or sha(folder/'task-checkpoint.json')!=handle['checkpoint_sha256']:
        raise ValueError('duty_launch_checkpoint')
    if ((folder/'submission.json').exists() or (operator/'execution-exit.json').exists()
            or (operator/'execution-failure.json').exists()):
        raise ValueError('duty_launch_host_closed')
    if action=='task':
        return (folder/'dispatch.txt').read_text(encoding='utf-8')
    if checkpoint_sha!=handle['checkpoint_sha256']:
        raise ValueError('duty_launch_checkpoint')
    if action=='abort':
        write_new_json(control/'abort.json',dict(key=key,checkpoint_sha256=checkpoint_sha))
    elif action=='submit':
        decision=Decision.model_validate(read(notes)).model_dump(mode='json')
        write_new_json(control/(key+'.submit.json'),dict(checkpoint_sha256=checkpoint_sha,
            primary_decision=decision,event_id=event_id))
    return 'queued'


def audit(operator, *, guard_sha, exit_sha, codex_executable, output=None):
    from scripts.review_duty_replay import replay
    operator=external(operator)
    saved=require_guard(operator/'worker-guard.json',guard_sha,closed=True)
    if saved['operator']!=str(operator):
        raise ValueError('duty_launch_operator_binding')
    closed=pinned(operator/'execution-exit.json',exit_sha)
    if (closed['guard_sha256']!=guard_sha or not closed['closure_sha256']
            or closed['host_controls_valid'] is not True):
        raise ValueError('duty_launch_closure_unavailable')
    controls=HostMailbox(operator,lambda:None)
    controls.inventory=closed['host_control_sha256']
    controls.check_controls()
    if Path(codex_executable).resolve()!=CODEX.resolve():
        raise ValueError('duty_launch_codex_path')
    with CodexReadOnlyClient(codex_executable) as client:
        record=replay(RUN,closure_sha256=closed['closure_sha256'],inputs=packaged_inputs(),
            event_source=CodexHostReviewEventSource(client,saved['plan']),observe=transport.verify)
    if record['outcome']!=closed['outcome'] or record['calls']!=closed['calls']:
        raise ValueError('duty_launch_close_binding')
    require_guard(operator/'worker-guard.json',guard_sha,closed=True)
    pinned(operator/'execution-exit.json',exit_sha)
    controls.check_controls()
    closure=pinned(RUN/'closure.json',closed['closure_sha256'])
    actual={str(p):sha(p) if p.is_file() else 'directory' for root in
        (RUN,Path(closure['answers']),Path(closure['observations'])) for p in root.rglob('*')}
    if actual!={**closure['files'],str(RUN/'closure.json'):closed['closure_sha256']}:
        raise ValueError('duty_launch_seal_inventory')
    record.update(execution_guard_sha256=guard_sha,execution_exit_sha256=exit_sha)
    if output is not None:
        # The launch-level seal has one fixed create-only destination.
        if Path(output).absolute()!=operator/'seal.json':
            raise ValueError('duty_launch_seal_path')
        write_new_json(control_path(output,saved),record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','execute','task','submit','abort','replay','seal'))
    for name in ('operator','python','output','preparation','authorization','env-file','codex-executable','notes'):
        parser.add_argument('--'+name,type=Path)
    for name in ('preparation-sha','authorization-sha','guard-sha','exit-sha','key','checkpoint-sha','event-id'):
        parser.add_argument('--'+name)
    args=parser.parse_args()
    def need(*names):
        if any(getattr(args,n) is None for n in names):parser.error('required: '+', '.join(names))
    try:
        if args.action=='prepare':
            need('operator','python','output')
            if not PACKAGE.exists():create_package()
            saved=proposal(args.operator,args.python)
            startup(saved)
            write_new_json(control_path(args.output,saved),saved)
            print(json.dumps(dict(preparation_sha256=sha(args.output),execution_authorized=False),ensure_ascii=True))
        elif args.action=='execute':
            need('preparation','preparation_sha','authorization','authorization_sha','env_file','codex_executable')
            result=execute(preparation=args.preparation,preparation_sha=args.preparation_sha,
                authorization_path=args.authorization,authorization_sha=args.authorization_sha,
                env_file=args.env_file,codex_executable=args.codex_executable)
            print(json.dumps(dict(outcome=result['outcome'],calls=result['calls']),ensure_ascii=True))
            if result['outcome']=='hard_failure':raise SystemExit(1)
        elif args.action in ('replay','seal'):
            need('operator','guard_sha','exit_sha','codex_executable')
            if args.action=='seal':need('output')
            print(json.dumps(audit(args.operator,guard_sha=args.guard_sha,exit_sha=args.exit_sha,
                codex_executable=args.codex_executable,output=args.output if args.action=='seal' else None),ensure_ascii=True))
        else:
            need('operator','key','guard_sha')
            if args.action!='task':need('checkpoint_sha')
            if args.action=='submit':need('notes','event_id')
            print(host_command(args.operator,args.key,guard_sha=args.guard_sha,action=args.action,checkpoint_sha=args.checkpoint_sha,
                notes=args.notes,event_id=args.event_id))
    except Exception as error:
        raise SystemExit('duty_launch_failed: '+type(error).__name__) from None


if __name__=='__main__':
    main()
