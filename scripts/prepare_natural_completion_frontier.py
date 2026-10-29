"""Zero-send audit of the accepted prefix of a semantically rejected task.

Reuse the existing Runtime frontier replay. This is preparation, not a paid
launcher or permission to retry a rejected opinion until it passes. The old
completion response, rejection, seal and all costs remain parent evidence.
"""
import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

VERSION = 'natural-completion-frontier-audit-v1'


def read(path):
    return json.loads(Path(path).read_bytes())


def prefix_state(operator):
    """Select by committed operations and terminal, never by timestamps."""
    from app.evaluation.sol_natural_session import canonical, digest
    from app.evaluation import sol_review_contract as contract
    from scripts.reviewer_profile_batch import inventory
    root = Path(operator)
    folder = root/'execution/session'
    terminal = read(folder/'terminal.json')
    if (terminal.get('key') != 'completion-initial'
            or terminal.get('reason') != 'semantic_rejected'
            or terminal.get('publication_allowed') is not False
            or terminal.get('production_admitted') is not False):
        raise ValueError('frontier_completion_rejection_required')
    rows, values = [], []
    for n, path in enumerate(sorted((folder/'operations').glob('*-intent.json')), 1):
        row, result = read(path), read(path.with_name(path.name.replace('intent', 'result')))
        if (path.name != f'{n:04d}-intent.json' or row['ordinal'] != n
                or result['intent_sha256'] != digest(path.read_bytes())):
            raise ValueError('frontier_operation_binding')
        rows.append(row)
        values.append(result['value'])
    # The only Host tasks are the accepted facts and rejected completion.
    host = [n for n, row in enumerate(rows) if row['kind'] == 'host-task']
    if (len(host) != 2 or host[-1] != len(rows)-1
            or [rows[n]['request']['key'] for n in host] != ['facts-initial', 'completion-initial']):
        raise ValueError('frontier_initial_task_shape')
    accepted = host[0]
    if (accepted < 2 or host[1] != accepted+4
            or [r['kind'] for r in rows[accepted-2:]]
                != ['model', 'journal', 'host-task', 'host-decision', 'model', 'journal', 'host-task']
            or rows[accepted-1]['request'].get('name') != 'facts-initial'
            or rows[accepted+3]['request'].get('name') != 'completion-initial'
            or values[accepted+1] != {'accepted': True}):
        raise ValueError('frontier_accepted_facts_required')
    handles = [values[n] for n in host]
    for n, handle, duty in zip(host, handles, ('facts', 'completion')):
        issued = rows[n-2]['request']
        context = issued.get('metadata', {}).get(contract.CONTEXT, {})
        if (context.get('version') != contract.VERSION
                or (context.get('duty'), context.get('stage')) != (duty, 'initial')
                or values[n-2].get('ok') is not True
                or handle['binding'] != rows[n]['request']['binding']
                or handle['binding']['key'] != duty+'-initial'
                or Path(handle['folder']) != root/'execution/journal/host'/(duty+'-initial')):
            raise ValueError('frontier_source_or_handle_changed')
        decision = read(Path(handle['folder'])/'submission.json')
        if decision['primary']['decision']['accepted'] is not (duty == 'facts'):
            raise ValueError('frontier_original_decision_required')
    if rows[accepted+1]['request']['binding'] != handles[0]['binding']:
        raise ValueError('frontier_accepted_binding_changed')
    historical, prior = values[-3]['budget'], values[accepted-2]['budget']
    if (historical['logical'] != {'generation': 2, 'review': 2}
            or prior['logical'] != {'generation': 2, 'review': 1}
            or historical['calls'] != prior['calls']+1
            or historical['router_calls'] != historical['calls']
            or len(historical['attempts']) != historical['calls']
            or historical['attempts'][:-1] != prior['attempts']
            or historical['attempts'][-1]['status'] != 'completed'
            or historical['retries'] != prior['retries']
            or historical['reserved_tokens'] != prior['reserved_tokens']
            or historical['tokens'] <= prior['tokens']
            or historical['stopped'] or historical['failed']):
        raise ValueError('frontier_historical_accounting_changed')
    derived = deepcopy(historical)
    derived['logical']['review'] = 1
    return dict(prefix_operations=accepted+2, historical_budget=historical,
        derived_budget=derived, accepted_handle=handles[0],
        frontier=rows[accepted+2]['request'],
        frontier_sha256=digest(canonical(rows[accepted+2]['request'])),
        parent_operations_inventory=inventory(folder/'operations'))


def sealed_inputs(operator, seal_sha, evidence_file):
    from app.evaluation.sol_natural_session import digest
    from scripts.reviewer_profile_batch import inventory
    root = Path(operator).resolve()
    evidence = read(evidence_file)
    seal = read(root/'seal.json')
    actual = inventory(root)
    if (actual.get('seal.json') != seal_sha or evidence['seal_sha256'] != seal_sha
            or Path(evidence['operator']).resolve() != root
            or actual != {**seal['inventory'], 'seal.json':seal_sha}
            or actual.get('plan.json') != seal['plan_sha256']
            or seal['result'] != evidence['replay']
            or seal['result'].get('strict_replay') is not True
            or seal['result'].get('reason') != 'semantic_rejected'):
        raise ValueError('frontier_original_seal_required')
    control = Path(evidence['control'])
    pins = evidence['native_administrative_recovery']
    for name, key in (('rejected_native_recovery.py', 'adapter_sha256'),
                      ('rejected-native-recovery-manifest.json', 'manifest_sha256')):
        if digest((control/name).read_bytes()) != pins[key]:
            raise ValueError('frontier_reject_only_reader_changed')
    return root, read(root/'plan.json'), evidence, actual


def frozen_readback(operator, seal_sha, evidence_file):
    from app.evaluation.sol_natural_session import digest
    from scripts import sol_natural_launch as launch
    from scripts.reviewer_profile_batch import inventory
    root, plan, evidence, before = sealed_inputs(operator, seal_sha, evidence_file)
    if (Path.cwd().resolve() != Path(plan['cwd']).resolve()
            or Path(sys.executable).resolve() != Path(plan['python']).resolve()
            or launch.current_head() != plan['head']
            or subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()):
        raise ValueError('frontier_original_frozen_execution_required')
    authors = root.with_name(root.name+'-authors')
    author_before = inventory(authors)
    if len(author_before) != 3:
        raise ValueError('frontier_original_author_inventory_changed')
    control = Path(evidence['control'])
    spec = importlib.util.spec_from_file_location('frontier_reject_reader', control/'rejected_native_recovery.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    # The original helper predates a facts timeout in this prefix. Use the
    # audited external scratch copier, retaining the frozen Runtime/contract
    # and every parent byte. This is not a patch to the frozen application.
    helper_path = Path(__file__).with_name('prepare_completion_continuation.py')
    helper_spec = importlib.util.spec_from_file_location('frontier_scratch_helper', helper_path)
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    roots = evidence['original_stdout_roots']
    launch.load(root, evidence['plan_sha256'], frozen=True)
    with adapter.RejectedOpinionRecoveryClient(launch.CODEX,
            recovery_path=control/'rejected-native-recovery-manifest.json',
            recovery_sha256=evidence['native_administrative_recovery']['manifest_sha256']) as client:
        events = launch.CodexHostReviewEventSource(client, plan['review_plan'])
        replay = launch.replay(plan, evidence['plan_sha256'], events, **roots)
        if replay != evidence['replay']:
            raise ValueError('frontier_original_replay_changed')
        state = prefix_state(root)
        _, gate = launch.session_for(plan, evidence['plan_sha256'], events,
                                    read_only=True, **roots)
        proof = helper.preview_prefix(root, state, launch.candidate_for(plan), gate.native.workspace, events)
    if inventory(root) != before or inventory(authors) != author_before:
        raise ValueError('frontier_parent_changed_during_readback')
    if replay['accounting'] != {k:state['historical_budget'][k]
                              for k in ('calls', 'tokens', 'reserved_tokens', 'retries')}:
        raise ValueError('frontier_original_cost_changed')
    return dict(version=VERSION, **proof, state=state, parent_operator=str(root),
        parent_inventory=before, parent_author_inventory=author_before,
        parent_seal_sha256=seal_sha, original_strict_replay=replay,
        original_rejected_completion_retained=True, ordinary_rejected_native_import=False,
        external_scratch_helper_sha256=digest(helper_path.read_bytes()))


def prepare(operator, seal_sha, evidence_file, output):
    from app.evaluation import sol_review_contract as contract
    from app.evaluation.sol_natural_session import digest
    from scripts.prepare_completion_continuation import preview_prefix
    from scripts.reviewer_profile_batch import inventory
    from scripts.host_review_workspace import HostReviewWorkspace
    from scripts import sol_natural_launch as launch
    from scripts.prepare_reviewer_profile_screen import visible, json_value
    root, plan, evidence, before = sealed_inputs(operator, seal_sha, evidence_file)
    output = Path(output).absolute()
    authors = root.with_name(root.name+'-authors')
    forbidden = (root, authors, Path(evidence['control']), contract.ROOT, Path(plan['cwd']))
    if (output.exists() or output.resolve() != output
            or any(output.is_relative_to(p.resolve()) or p.resolve().is_relative_to(output) for p in forbidden)):
        raise ValueError('frontier_new_external_output_required')
    with TemporaryDirectory(prefix='natural-frontier-readback-') as temporary:
        result_file = Path(temporary)/'readback.json'
        completed = subprocess.run([plan['python'], '-X', 'utf8', str(Path(__file__).resolve()),
            '--frozen-worker', '--operator', str(root), '--seal-sha', seal_sha,
            '--evidence-file', str(Path(evidence_file).resolve()), '--output', str(result_file)],
            cwd=plan['cwd'], capture_output=True, timeout=300)
        if completed.returncode:
            failure = read(result_file) if result_file.exists() else {}
            code = failure.get('error_code', '')
            if not re.fullmatch(r'(frontier|completion|launch|session|codex_review_host)_[a-z0-9_]+', code):
                code = 'frontier_frozen_readback_failed'
            raise ValueError(code)
        original = read(result_file)
    workspace = HostReviewWorkspace(cwd=plan['cwd'], python=plan['python'],
        answers=authors, evidence_roots=[root])
    with launch.host(plan) as events:
        current = preview_prefix(root, original['state'], contract, workspace, events)
    if (current != {k:original[k] for k in current}
            or inventory(root) != before or inventory(authors) != original['parent_author_inventory']):
        raise ValueError('frontier_current_runtime_or_originals_changed')
    context = current['frontier']['metadata'][contract.CONTEXT]
    inputs = contract.restore_context(context)
    request = contract.make_request(inputs, 'completion', 'initial')
    if visible(json_value(request)) != visible(current['frontier']):
        raise ValueError('frontier_current_business_request_changed')
    from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
    per_request = estimate_runtime_request_input_ceiling(request)+request.max_tokens
    recipe = dict(version=VERSION, status='offline_verified_not_a_paid_launcher',
        accepted_prefix_operations=current['imported_operations'], next_stage='completion-initial',
        original_failure='semantic_rejected', old_completion_accepted=False,
        original_generation_reused=True, original_facts_native_replayed=True,
        same_policy_retry_is_not_quality_improvement=True,
        minimum_fresh_live_chain_if_selected=['completion-initial', 'compatibility-host',
            'edit-host', 'unique-application', 'facts-fresh', 'completion-fresh'],
        logical_model_requests=3, historical_accounting=original['original_strict_replay']['accounting'],
        first_request_reservation=per_request,
        retained_fresh_evidence_is_not_a_formal_application=True,
        remaining_before_paid_execution=['Select a mechanism or integration question worth a new trial; do not retry until pass.',
            'Bind a separate continuation entry, original native owner and complete end-to-end recovery tests.',
            'Freeze execution code, exact new scope, native preflight and a specific new grant.'],
        execution_ready=False, execution_authorized=False, provider_requests=0, key_reads=0,
        qualified=False, publication_allowed=False, production_admitted=False)
    files = {'frozen-prefix-proof.json':original, 'current-prefix-proof.json':current,
        'completion-request.json':visible(json_value(request)),
        'completion-validation-context.json':context, 'continuation-recipe.json':recipe}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in files.items():
        with (output/name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(value, ensure_ascii=True, indent=2)+'\n')
    return dict(version=VERSION, output=str(output), files=inventory(output),
        accepted_prefix_operations=current['imported_operations'], provider_requests=0, key_reads=0,
        execution_ready=False, old_completion_accepted=False,
        completion_request_sha256=contract.request_sha(request))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator', type=Path, required=True)
    parser.add_argument('--seal-sha', required=True)
    parser.add_argument('--evidence-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frozen-worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.frozen_worker:
        sys.path.insert(0, str(Path.cwd()))
        try:
            result = frozen_readback(args.operator, args.seal_sha, args.evidence_file)
        except Exception as error:
            message = str(error)
            code = message if re.fullmatch(
                r'(frontier|completion|launch|session|codex_review_host)_[a-z0-9_]+', message
            ) else 'frontier_frozen_readback_failed'
            with args.output.open('x', encoding='utf-8') as stream:
                json.dump(dict(error_code=code, error_type=type(error).__name__), stream, ensure_ascii=True)
            raise SystemExit(1) from None
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=True, indent=2)
    else:
        # `python -m` keeps project imports in the selected development checkout.
        result = prepare(args.operator, args.seal_sha, args.evidence_file, args.output)
        print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
