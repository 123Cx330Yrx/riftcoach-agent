"""Prospective four-review launch adapter; no authorization issuer or automatic execution.

prepare is create-only. execute requires its own exact grant, green CI, clean
HEAD, source/package pins and current native/path checks. Old grants never apply.
"""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from scripts import review_duty_patch_execution as execution
from scripts import review_duty_patch_transport as transport
from scripts import review_duty_patch_replay as replay
from scripts.full_chain_modules import private_module

# Keep legacy request/package helpers while routing initial requests to the new
# full-source schema. This facade does not change either public duty module.
_interface = SimpleNamespace(**vars(execution))
_interface.duty = SimpleNamespace(DUTIES=execution.duty.DUTIES,
    review_request=execution.direct.review_request)
_launch = private_module(execution.ROOT/'scripts/review_duty_launch.py', {
    'scripts.review_duty_execution': _interface,
    'scripts.review_duty_transport': transport,
    'scripts.review_duty_replay': replay})
_launch.VERSION = 'review-duty-direct-patch-launch-v1'
_launch.AUTH_VERSION = _launch.VERSION+'-authorization'
_launch.RUN = execution.ROOT/'data/runs/model_comparison/review-duty-direct-patch-20261014'
_launch.PACKAGE = execution.ROOT/'data/evaluation/fixtures/review_duty_direct_patch_20261014'
_proposal = _launch.proposal


def proposal(operator, python):
    saved = _proposal(operator, python)
    saved['budget'] = dict(maximum_calls=4, glm_high=4, flash_high=0, maximum_tokens=387072,
        maximum_active_seconds=2400, maximum_host_seconds=86400, per_review_seconds=600,
        per_request_output=32768, uncached_cny='5.718016', hard_billing_cap=False)
    return saved


def startup(saved):
    python, root = Path(saved['python']), _launch.ROOT
    if python.resolve() != Path(sys.executable).resolve() or Path.cwd().resolve() != root.resolve():
        raise ValueError('duty_launch_actual_interpreter_or_cwd')
    proof = subprocess.run([str(python), '-B', '-c',
        'import json,os,sys; from pathlib import Path; import scripts.review_duty_patch_launch as m; '
        'print(json.dumps(dict(cwd=os.getcwd(),python=sys.executable,module=str(Path(m.__file__).resolve())),ensure_ascii=True))'],
        cwd=saved['cwd'], capture_output=True, text=True, encoding='utf-8', timeout=30, check=True)
    value = json.loads(proof.stdout)
    if (Path(value['cwd']).resolve() != root.resolve()
            or Path(value['python']).resolve() != python.resolve()
            or Path(value['module']).resolve() != Path(__file__).resolve()):
        raise ValueError('duty_launch_startup_identity')
    return value


def host_command(operator, key, *, guard_sha, action, checkpoint_sha=None, notes=None, event_id=None):
    # edit is a Host-only stage: it must not become a model slot just to reuse
    # the old CLI's validation list.
    if key not in (*execution.SLOTS, 'compatibility', 'edit') or action not in ('task', 'submit', 'abort'):
        raise ValueError('duty_launch_stage')
    operator = _launch.external(operator)
    saved = _launch.require_guard(operator/'worker-guard.json', guard_sha)
    if saved['operator'] != str(operator):
        raise ValueError('duty_launch_operator_binding')
    control = operator/'host-controls'
    handle = _launch.read(control/(key+'.pending.json'))
    folder = _launch.RUN/('host-'+key)
    if handle['folder'] != str(folder) or execution.sha(folder/'task-checkpoint.json') != handle['checkpoint_sha256']:
        raise ValueError('duty_launch_checkpoint')
    if any(p.exists() for p in (folder/'submission.json', operator/'execution-exit.json', operator/'execution-failure.json')):
        raise ValueError('duty_launch_host_closed')
    if action == 'task':
        return (folder/'dispatch.txt').read_text(encoding='utf-8')
    if checkpoint_sha != handle['checkpoint_sha256']:
        raise ValueError('duty_launch_checkpoint')
    if action == 'abort':
        _launch.write_new_json(control/'abort.json', dict(key=key, checkpoint_sha256=checkpoint_sha))
    else:
        decision = _launch.Decision.model_validate(_launch.read(notes)).model_dump(mode='json')
        _launch.write_new_json(control/(key+'.submit.json'), dict(checkpoint_sha256=checkpoint_sha,
            primary_decision=decision, event_id=event_id))
    return 'queued'


_launch.proposal, _launch.startup, _launch.host_command = proposal, startup, host_command
require_guard, main = _launch.require_guard, _launch.main


if __name__ == '__main__':
    main()
