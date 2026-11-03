"""One pinned facts-initial diagnostic, using the existing owned worker.

No generation, automatic retry, batch reopening, native judgment or admission.
The original grant is evidence for a narrower, explicitly rebound diagnostic;
its issue/expiry and all spent/unknown history are retained, not reset.
"""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import sys
import warnings

from app.evaluation.sol_natural_contract import validate_business
from scripts import reviewer_responses_nonstream as codec
from scripts.reviewer_responses_process import read_json, run_once, write_json
from scripts.reviewer_responses_transport import Profile, digest
from scripts.reviewer_profile_batch import inventory, source_identity
from scripts.run_natural_duty_development import current_head, verify_ci

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'sol-reasoning-single-v1'
LIMITS = dict(http_requests=1, input_tokens=64000, output_tokens=16384,
              reserved_tokens=80384, request_seconds=300, automatic_retries=0, generation=0)
HISTORY = dict(http_requests=6, known_tokens=80137, unknown_reserved_tokens=145824, retries=1)
PARENT_SEAL = '1d0a2f49dda848068ad4d74ed84cc09ce065b54531603b9d51498b7a9682f774'
PARENT_GRANT = 'b7ab806d4823182ac7556ea42e88413c1978d4f7140872c92cd4a159f0b40683'
PARENT_STDOUT = '608760243e7669399a3f623575ee800bf738f13f2f72a8841a0a4de7f54b13ec'
REQUEST_SHA = '008987be27dc121516010a488e2fae70d5d167f454f555b9bccbb7db435b3eae'
CONTEXT_SHA = 'f5520898301e46c7682e2781f469700298dcbdc64516ff56dada65643c0358d3'
WIRE_SHA = '527e860587a234abf5cbc37ae27e0c968fbfe8ede8aa0f1e760b0d2af8590c8f'
REPORT_SHA = '00338bbc5e5e81a06ad462069024027be255411fb1221cba55c0abf9da3c2d32'
CALL = 'execution/transport/sol-natural-observed-20261021/review/call-006'
CODEX = Path('C:/Users/33502/AppData/Local/Programs/OpenAI/Codex/bin/codex.exe')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def parent_material(parent, control):
    parent, control = Path(parent), Path(control)
    require(sha(parent/'seal.json') == PARENT_SEAL, 'diagnostic_parent_seal_changed')
    seal = read_json(parent/'seal.json')
    require(inventory(parent) == {**seal['inventory'], 'seal.json': PARENT_SEAL},
            'diagnostic_parent_inventory_changed')
    require(sha(control/'start-0001.stdout.txt') == PARENT_STDOUT,
            'diagnostic_original_stdout_changed')
    require(sha(control/'authorization.json') == PARENT_GRANT,
            'diagnostic_original_authorization_changed')
    grant = read_json(control/'authorization.json')
    original_plan = read_json(parent/'plan.json')
    require(grant['plan_sha256'] == sha(parent/'plan.json') and
            grant['head'] == original_plan['head'] and
            seal['original_roots']['authorization_sha'] == PARENT_GRANT and
            seal['result']['accounting'] == dict(calls=6, tokens=80137, reserved_tokens=145824, retries=1) and
            grant['continuation']['max_new_attempts'] - seal['result']['continuation']['new_calls'] >= 1 and
            grant['continuation']['max_new_tokens'] - seal['result']['continuation']['new_known_tokens'] >= 80384,
            'diagnostic_parent_scope_changed')
    call = parent/CALL
    require(sha(call/'request.json') == REQUEST_SHA and sha(call/'validation-context.json') == CONTEXT_SHA,
            'diagnostic_original_material_changed')
    business, context = read_json(call/'request.json'), read_json(call/'validation-context.json')
    validate_business(business, context)
    require(context['duty'] == 'facts' and context['stage'] == 'initial' and
            hashlib.sha256(context['report'].encode('utf-8')).hexdigest() == REPORT_SHA and
            digest(codec.build_wire(business)) == WIRE_SHA, 'diagnostic_wire_changed')
    return business, context, grant


def prepare(operator, parent, control):
    """Offline/create-only; does not claim a call or read a credential."""
    head = current_head()
    operator, parent, control = (Path(p).absolute() for p in (operator, parent, control))
    require(all(p.resolve() == p for p in (operator, parent, control)) and
            not any(operator.is_relative_to(p) or p.is_relative_to(operator)
                    for p in (ROOT, parent, control)), 'diagnostic_operator_overlap')
    _, _, old = parent_material(parent, control)
    plan = dict(version=VERSION, operator=str(operator), parent=str(parent), control=str(control),
        head=head, cwd=str(ROOT.resolve()), python=str(Path(sys.executable).resolve()), source=source_identity(),
        limits=LIMITS, history=HISTORY, parent_seal_sha256=PARENT_SEAL, wire_sha256=WIRE_SHA,
        estimated_uncached_cny='0.058368', publication_allowed=False, qualified=False,
        authorization=dict(version=VERSION+'-authorization', head=head, original_grant_sha256=PARENT_GRANT,
            issued_at=old['issued_at'], expires_at=old['expires_at'], limits=LIMITS,
            user_evidence='User authorized necessary budget increases and continued diagnosis/repair/progression; '
                'latest continue follows the defined one-original-request diagnostic. Narrowed to one request, '
                'zero generation/retry; remaining original scope and original UTC expiry retained. '
                'Original exact-head grant is not reused as a grant for this new head.'))
    operator.mkdir(parents=True, exist_ok=False)
    write_json(operator/'plan.json', plan)
    return dict(plan_sha256=sha(operator/'plan.json'), provider_requests=0, key_read=False)


def check(operator, plan_sha, *, now=None, completed=False):
    operator = Path(operator).absolute()
    require(sha(operator/'plan.json') == plan_sha, 'diagnostic_original_plan_sha_required')
    plan = read_json(operator/'plan.json')
    require(plan['version'] == VERSION and plan['operator'] == str(operator) and
            Path.cwd().resolve() == ROOT.resolve() and plan['cwd'] == str(ROOT.resolve()) and
            plan['python'] == str(Path(sys.executable).resolve()), 'diagnostic_execution_paths_changed')
    require(current_head() == plan['head'] and source_identity() == plan['source'],
            'diagnostic_frozen_source_changed')
    if not completed:
        require(not (operator/'claim.json').exists() and not (operator/'call').exists() and
                not (operator/'seal.json').exists(), 'diagnostic_already_claimed_no_retry')
    business, context, old = parent_material(plan['parent'], plan['control'])
    grant = plan['authorization']
    issued, expires = (datetime.fromisoformat(grant[k]) for k in ('issued_at', 'expires_at'))
    require(grant['version'] == VERSION+'-authorization' and grant['head'] == plan['head'] and
            grant['original_grant_sha256'] == PARENT_GRANT and grant['limits'] == LIMITS and
            all(grant[k] == old[k] for k in ('issued_at', 'expires_at')) and
            issued.tzinfo is not None and expires.tzinfo is not None and issued < expires and
            (completed or issued <= (now or datetime.now(timezone.utc)) < expires),
            'diagnostic_specific_unexpired_authorization_required')
    require(plan['limits'] == LIMITS and plan['history'] == HISTORY and plan['wire_sha256'] == WIRE_SHA and
            plan['parent_seal_sha256'] == PARENT_SEAL, 'diagnostic_scope_changed')
    return plan, business, context


def hidden_key():
    require(sys.stdin.isatty(), 'diagnostic_interactive_hidden_key_required')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        key = getpass.getpass('Tianjige GPT-pro API key (hidden): ')
    require(bool(key.strip()), 'diagnostic_empty_key')
    return key


def native_state(plan):
    from scripts.codex_review_event_source import CodexReadOnlyClient
    from scripts.run_boundary_examples_v2 import verify_native_principals
    original_plan = read_json(Path(plan['parent'])/'plan.json')
    with CodexReadOnlyClient(CODEX) as client:
        return verify_native_principals(client, original_plan['review_plan'])


def execute(operator, plan_sha, ci_run):
    plan, _, _ = check(operator, plan_sha)
    ci = verify_ci(ci_run, plan['head'])
    native_state(plan)
    # No active request clock or claim while the user waits at the hidden prompt.
    key = hidden_key()
    try:
        plan, business, context = check(operator, plan_sha)  # actual UTC/source/parent after input
        native = native_state(plan)
        require(datetime.now(timezone.utc) < datetime.fromisoformat(plan['authorization']['expires_at']),
                'diagnostic_authorization_expired_during_native_read')
        operator = Path(operator)
        write_json(operator/'claim.json', dict(version=VERSION, plan_sha256=plan_sha,
            claimed_at=datetime.now(timezone.utc).isoformat(), ci=ci, native=native, limits=LIMITS, history=HISTORY))
        print(json.dumps(dict(phase='claimed', plan_sha256=plan_sha,
            claim_sha256=sha(operator/'claim.json')), ensure_ascii=True), flush=True)
        receipt = run_once(business, profile=Profile(group='GPT-pro', route='proxy-12000'),
            api_key=key, directory=operator/'call', timeout_s=300,
            response_mode='natural-sol-v1', validation_context=context)
    finally:
        key = None
    # A failed postflight does not replace or delete a request/receipt; the claim
    # remains a hard no-resend boundary even after a crash or missing closure.
    parent_material(plan['parent'], plan['control'])
    summary = summarize(operator, receipt)
    write_json(operator/'seal.json', dict(version=VERSION+'-seal', plan_sha256=plan_sha,
        inventory=inventory(operator), result=summary))
    return dict(**summary, seal_sha256=sha(operator/'seal.json'))


def summarize(operator, receipt):
    worker = read_json(operator/'call/worker-result.json') or {}
    observation = read_json(operator/'call/observation/observation.json') or {}
    return dict(code=receipt['code'], worker_code=receipt['worker_code'], ok=receipt['ok'],
        http_requests=receipt['http_requests'], usage_state=receipt['usage_state'],
        response_status=observation.get('response_status'),
        decode=observation.get('response_decode'), public_opinion_retained=bool(worker.get('diagnostic_tool_call')),
        history=HISTORY, new_known_tokens=receipt['usage']['total_tokens']
            if receipt['usage_state'] == 'known' else 0,
        new_unknown_reserved_tokens=80384 if receipt['usage_state'] == 'unknown' else 0,
        semantic_approval=False, qualified=False, publication_allowed=False)


def replay(operator, plan_sha, seal_sha):
    """Strictly read-only closure inspection; never makes a diagnostic adoptable."""
    operator = Path(operator).absolute()
    before = inventory(operator)
    check(operator, plan_sha, completed=True)
    require(sha(operator/'seal.json') == seal_sha, 'diagnostic_original_seal_sha_required')
    seal = read_json(operator/'seal.json')
    require(before == {**seal['inventory'], 'seal.json': seal_sha} and
            seal['plan_sha256'] == plan_sha, 'diagnostic_sealed_inventory_changed')
    receipt = read_json(operator/'call/receipt.json')
    summary = summarize(operator, receipt)
    require(seal['result'] == summary and inventory(operator) == before, 'diagnostic_replay_changed')
    return dict(result=summary, readonly=True, seal_sha256=seal_sha)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'run', 'replay'])
    parser.add_argument('--operator', required=True, type=Path)
    parser.add_argument('--parent', type=Path)
    parser.add_argument('--control', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--seal-sha')
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            require(args.parent is not None and args.control is not None, 'diagnostic_parent_required')
            result = prepare(args.operator, args.parent, args.control)
        elif args.action == 'check':
            plan, _, _ = check(args.operator, args.plan_sha)
            result = dict(code='local_preflight_ok', head=plan['head'], provider_requests=0, key_read=False,
                          expires_at=plan['authorization']['expires_at'], native=native_state(plan))
        elif args.action == 'replay':
            result = replay(args.operator, args.plan_sha, args.seal_sha)
        else:
            require(bool(args.ci_run), 'diagnostic_ci_required')
            result = execute(args.operator, args.plan_sha, args.ci_run)
    except KeyboardInterrupt:
        result = dict(ok=False, code='cancelled_no_automatic_retry', publication_allowed=False)
    except Exception as error:
        # Only our fixed codes, never provider exceptions, request text or secrets.
        code = str(error) if type(error) is ValueError and str(error).startswith('diagnostic_') else 'diagnostic_preflight_or_storage_failed'
        result = dict(ok=False, code=code, publication_allowed=False)
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result.get('ok', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
