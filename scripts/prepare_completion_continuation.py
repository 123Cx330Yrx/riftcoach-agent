"""Read a sealed task with its frozen code and prove the completion frontier.

This entry has no paid/run action. Its disposable session replays the accepted
prefix, including the original native review, with the entire historical cost.
It prepares a continuation recipe, not an executable grant or model result.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


VERSION = 'completion-continuation-offline-v1'


def read(path):
    return json.loads(Path(path).read_bytes())


def prefix_state(operator):
    """Validate the exact supported boundary; call only after strict replay."""
    from app.evaluation.sol_natural_session import canonical, digest
    from scripts.reviewer_profile_batch import inventory
    root = Path(operator)
    operations = root/'execution/session/operations'
    intents = sorted(operations.glob('*-intent.json'))
    rows, results = [], []
    for n, path in enumerate(intents, 1):
        intent = read(path)
        result = read(operations/f'{n:04d}-result.json')
        if (path.name != f'{n:04d}-intent.json' or intent['ordinal'] != n
                or result['intent_sha256'] != digest(path.read_bytes())):
            raise ValueError('completion_parent_operation_binding')
        rows.append(intent)
        results.append(result['value'])
    # Search count may vary. The only native review is the accepted facts gate.
    tools = len(rows)-8
    if (tools < 0 or [r['kind'] for r in rows] != ['model']+['tool']*tools+
            ['model', 'model', 'journal', 'host-task', 'host-decision', 'model', 'journal']
            or any(r['request'].get('name') != 'knowledge.search' for r in rows[1:1+tools])
            or any(r.get('success') is not True for r in results[1:1+tools])
            or any(results[n].get('ok') is not True for n in (0, tools+1, tools+2))):
        raise ValueError('completion_parent_prefix_shape')
    for row, duty in ((rows[-5], None), (rows[-2], 'completion'), (rows[-6], 'facts')):
        if duty is None:
            if row['request'].get('name') != 'facts-initial':
                raise ValueError('completion_parent_facts_journal')
        else:
            context = row['request'].get('metadata', {}).get('sol_necessity_validation')
            if not context or (context.get('duty'), context.get('stage')) != (duty, 'initial'):
                raise ValueError('completion_parent_stage')
    handle = results[-4]
    if (rows[-4]['request'].get('key') != 'facts-initial'
            or rows[-3]['request'].get('key') != 'facts-initial'
            or handle['binding'] != rows[-3]['request']['binding']
            or results[-3] != {'accepted': True}
            or handle['binding'].get('key') != 'facts-initial'
            or Path(handle['folder']) != root/'execution/journal/host/facts-initial'
            or not (Path(handle['folder'])/'submission.json').is_file()
            or rows[-1]['request'].get('name') != 'outcome'
            or rows[-1]['request']['data'].get('outcome') != 'candidate_execution_failed'):
        raise ValueError('completion_parent_accepted_facts_required')
    prior, failed = results[-6]['budget'], results[-2]
    budget = failed['budget']
    if (failed.get('ok') is not False or failed.get('error_code') != 'sol_call_failed'
            or prior['logical'] != {'generation': 2, 'review': 1}
            or budget['logical'] != {'generation': 2, 'review': 2}
            or budget['calls'] != prior['calls']+1 or budget['router_calls'] != budget['calls']
            or len(budget['attempts']) != budget['calls']
            or budget['attempts'][:-1] != prior['attempts']
            or budget['attempts'][-1]['status'] != 'failed'
            or budget['retries'] != prior['retries']
            or budget['stopped'] is not True or budget['failed'] is not True):
        raise ValueError('completion_parent_failure_accounting')
    receipt_root = root/'execution/transport'/read(root/'plan.json')['run_id']/'review'/f"call-{budget['calls']:03d}"
    receipt, worker = read(receipt_root/'receipt.json'), read(receipt_root/'worker-result.json')
    observation = read(receipt_root/'observation/observation.json')
    if (receipt.get('worker_code') != 'non_tool_output' or worker.get('code') != 'non_tool_output'
            or receipt.get('ok') is not False or receipt.get('reaped') is not True
            or receipt.get('usage_state') != 'known' or receipt.get('http_requests') != 1
            or receipt.get('usage_conflict') is not False or receipt.get('worker_exit') != 0
            or receipt.get('usage') != worker.get('usage')
            or observation.get('response_status') != 200 or observation.get('http_requests') != 1
            or observation.get('eof') is not True or observation.get('closed') is not True
            or observation.get('response_contract') != worker.get('response_observation')
            or observation['response_contract'].get('model_matches') is not True
            or budget['tokens'] != prior['tokens']+receipt['usage']['total_tokens']
            or budget['reserved_tokens'] != prior['reserved_tokens']):
        raise ValueError('completion_parent_failure_receipt')
    carried = deepcopy(budget)
    carried.update(stopped=False, failed=False)
    carried['logical']['review'] = 1
    carried.pop('retry_issued_raw', None)
    return dict(prefix_operations=len(rows)-2, historical_budget=budget,
        derived_budget=carried, accepted_handle=handle,
        frontier=rows[-2]['request'], frontier_sha256=digest(canonical(rows[-2]['request'])),
        parent_operations_inventory=inventory(operations))


def preview_prefix(operator, spec, candidate, workspace, event_source, builder=None):
    """Replay actual Runtime in scratch space; old native handles keep their owner."""
    from app.evaluation.sol_natural_session import CandidateSession, SessionPaused, canonical, digest
    from app.evaluation.sol_session_review import SessionReviewGate
    from scripts.host_review_workspace import HostReviewWorkspace
    from scripts.reviewer_profile_batch import inventory
    root = Path(operator)
    plan = read(root/'plan.json')
    guard = read(root/'execution/session/guard.json')

    def forbidden(*args, **kwargs):
        raise AssertionError('completion_preview_io_forbidden')

    with TemporaryDirectory(prefix='completion-prefix-') as directory:
        scratch = Path(directory)
        session = CandidateSession(scratch/'session', binding=guard['binding'],
            transport_root=scratch/'transport'/plan['run_id'], journal_root=scratch/'journal',
            contract_module=candidate, max_new_models=0, before_new_model=forbidden)
        frontier = []
        original_operation = session.operation

        def observe_boundary(kind, request, action):
            if session.cursor == spec['prefix_operations']:
                if kind != 'model' or digest(canonical(request)) != spec['frontier_sha256']:
                    raise ValueError('completion_frontier_changed')
                frontier.append(deepcopy(request))
            return original_operation(kind, request, action)

        # Scratch-only observer; the exact CandidateSession still owns replay,
        # integrity and max_new_models=0. No product type check is bypassed.
        session.operation = observe_boundary
        # Reuse the original author and native source, never a newly synthesized
        # decision or a copied 'accepted' flag interpreted under another owner.
        inherited_workspace = HostReviewWorkspace(cwd=workspace.cwd, python=workspace.python,
            answers=workspace.answers, evidence_roots=[*workspace.evidence_roots, session.journal_root])
        gate = SessionReviewGate(session, plan=plan['review_plan'],
            workspace=inherited_workspace, event_source=event_source)
        try:
            with session:
                originals = root/'execution/session/operations'
                for n in range(1, spec['prefix_operations']+1):
                    for suffix in ('intent', 'result'):
                        name = f'{n:04d}-{suffix}.json'
                        raw = (originals/name).read_bytes()
                        row = json.loads(raw)
                        # The facts response remains exact. Only its disposable
                        # budget snapshot carries the later failed completion.
                        if suffix == 'result' and row['value'].get('budget') is not None:
                            # Carry later cost only at the final ACCEPTED facts
                            # result. A prior failed facts attempt also has
                            # logical.review == 1; changing that snapshot breaks
                            # its committed manual-retry request on replay.
                            if (n == spec['prefix_operations']-3
                                    and row['value'].get('ok') is True
                                    and row['value']['budget']['logical'] == {'generation': 2, 'review': 1}):
                                row['value']['budget'] = spec['derived_budget']
                                row['imported_from_sha256'] = digest(raw)
                                raw = canonical(row)
                        (session.root/'operations'/name).write_bytes(raw)
                shutil.copytree(root/'execution/transport'/plan['run_id'], session.transport_root)
                session.journal_root.mkdir()
                shutil.copy2(root/'execution/journal/facts-initial.json', session.journal_root/'facts-initial.json')
                session.active_before = read(sorted((root/'execution/session/checkpoints').glob('*.json'))[-1])['active_seconds']
                session._checkpoint('offline_prefix_imported')
                before = session._inventory()
                gate.verify_prior()
                if builder is None:
                    from app.providers.config import ZhipuSettings
                    from app.runtime.sol_natural_provider import SolNaturalProviderFactory
                    from scripts import natural_duty_preparation as base
                    factory = SolNaturalProviderFactory(generator_settings=ZhipuSettings(
                        api_key='OFFLINE_NO_SEND', base_url='https://open.bigmodel.cn/api/paas/v4',
                        model='glm-5.3-flash'), api_key='OFFLINE_NO_SEND',
                        transport_root=session.transport_root.parent, contract_module=candidate)
                    prepared = base.build_application(provider_factory=factory, output_root=scratch/'derived',
                        run_id=plan['run_id'], candidate=candidate, execution_session=session)
                    prepared.run()
                else:
                    builder(scratch, session)
        except SessionPaused as error:
            if (str(error) != 'session_model_boundary' or len(frontier) != 1
                    or session.cursor != spec['prefix_operations']):
                raise
        else:
            raise ValueError('completion_frontier_not_reached')
        # __exit__ may add a scratch checkpoint, never a new business operation.
        if (session._inventory() != before or session.new_models != 0
                or inventory(root/'execution/session/operations') != spec['parent_operations_inventory']):
            raise ValueError('completion_preview_unexpected_operation')
    return dict(frontier=frontier[0], imported_operations=spec['prefix_operations'],
        historical_budget=spec['historical_budget'], derived_budget=spec['derived_budget'],
        inherited_active_seconds=session.active_before, original_native_review_replayed=True,
        accepted_handle=spec['accepted_handle'], provider_requests=0, key_reads=0)


def frozen_readback(operator, seal_sha):
    """Runs under the PARENT checkout, retaining its original contract/receiver."""
    from app.evaluation.sol_natural_session import digest
    from scripts import sol_natural_launch as launch
    from scripts.reviewer_profile_batch import inventory
    root = Path(operator).resolve()
    before = inventory(root)
    if before.get('seal.json') != seal_sha:
        raise ValueError('completion_original_seal_required')
    seal = read(root/'seal.json')
    if {k:v for k,v in before.items() if k != 'seal.json'} != seal['inventory']:
        raise ValueError('completion_parent_inventory_changed')
    roots = seal['original_roots']
    plan = launch.load(root, seal['plan_sha256'], frozen=True)
    if subprocess.run(['git', 'status', '--porcelain'], check=True, capture_output=True,
                      text=True).stdout.strip():
        raise ValueError('completion_frozen_checkout_dirty')
    authors = root.with_name(root.name+'-authors')
    author_before = inventory(authors)
    with launch.host(plan) as event_source:
        checked = launch.replay(plan, seal['plan_sha256'], event_source, **roots)
        if checked != seal['result'] or checked['native_reviews'] != 1:
            raise ValueError('completion_parent_replay_changed')
        spec = prefix_state(root)
        if checked['accounting'] != {k:spec['historical_budget'][k]
                for k in ('calls', 'tokens', 'reserved_tokens', 'retries')}:
            raise ValueError('completion_parent_accounting_changed')
        _, gate = launch.session_for(plan, seal['plan_sha256'], event_source,
            guard=roots['guard'], checkpoint=roots['checkpoint'], read_only=True,
            authorization_sha=roots['authorization_sha'])
        proof = preview_prefix(root, spec, launch.candidate_for(plan), gate.native.workspace, event_source)
    if inventory(root) != before or inventory(authors) != author_before:
        raise ValueError('completion_originals_changed_during_readback')
    return dict(version=VERSION, parent_operator=str(root), parent_seal_sha256=seal_sha,
        parent_plan_sha256=seal['plan_sha256'], parent_roots=roots,
        parent_inventory=before, parent_author_inventory=author_before,
        frozen_head=plan['head'], frozen_contract=launch.candidate_for(plan).CONTRACT.snapshot().model_dump(mode='json'),
        strict_parent_replay=checked, **proof)


def prepare(operator, seal_sha, output):
    from app.evaluation.sol_natural_session import digest
    from scripts import review_completion_necessity_candidate as contrast
    from scripts.reviewer_profile_batch import inventory
    from scripts.prepare_reviewer_profile_screen import visible
    output, root = Path(output).absolute(), Path(operator).resolve()
    # Pin controls BEFORE launching the interpreter named by those controls.
    pinned = inventory(root)
    if pinned.get('seal.json') != seal_sha:
        raise ValueError('completion_original_seal_required')
    seal = read(root/'seal.json')
    if ({k:v for k,v in pinned.items() if k != 'seal.json'} != seal['inventory']
            or pinned.get('plan.json') != seal['plan_sha256']):
        raise ValueError('completion_parent_inventory_changed')
    plan = read(root/'plan.json')
    frozen = Path(plan['cwd']).resolve()
    authors = root.with_name(root.name+'-authors')
    if Path(plan['python']).resolve() != Path(sys.executable).resolve():
        raise ValueError('completion_actual_interpreter_required')
    if (output.exists() or output.resolve() != output or output.is_relative_to(root)
            or output.is_relative_to(frozen) or output.is_relative_to(contrast.baseline.ROOT)
            or output.is_relative_to(authors) or authors.is_relative_to(output)
            or root.is_relative_to(output) or frozen.is_relative_to(output)):
        raise ValueError('completion_output_must_be_new_external_directory')
    # Invoke this stdlib entry with the original working directory/interpreter.
    # The script is outside the frozen tree; no source or sealed file is edited.
    with TemporaryDirectory(prefix='completion-readback-') as directory:
        result_file = Path(directory)/'proof.json'
        completed = subprocess.run([plan['python'], '-X', 'utf8', str(Path(__file__).resolve()),
            '--frozen-worker', '--operator', str(root), '--seal-sha', seal_sha,
            '--output', str(result_file)], cwd=frozen, capture_output=True, timeout=300)
        if completed.returncode != 0:
            # No arbitrary subprocess text (native/private data) in logs.
            failure = read(result_file) if result_file.exists() else {}
            code = failure.get('error_code', '')
            if not re.fullmatch(r'(completion|launch|session|batch|host_workspace|codex_review_host)_[a-z0-9_]+', code):
                code = 'completion_frozen_readback_failed'
            raise ValueError(code)
        proof = read(result_file)
    material = contrast.materials()
    baseline = visible(contrast.json_value(contrast.make_request(material['a'], 'baseline')))
    if visible(proof['frontier']) != baseline:
        raise ValueError('completion_a_not_original_frontier')
    requests = {case:contrast.encode(visible(contrast.json_value(contrast.make_request(material[case]))))
                for case in ('b', 'c', 'd', 'a')}
    files = {f'{case}-candidate.json':raw for case,raw in requests.items()}
    files['parent-proof.json'] = contrast.encode(proof)
    files['continuation.json'] = contrast.encode(dict(version=VERSION,
        status='offline_frontier_verified_not_a_paid_launcher',
        parent_proof_sha256=digest(files['parent-proof.json']),
        fixture_inventory=inventory(contrast.PACKAGE),
        candidate_policy_sha256=digest(contrast.COMPLETION_NECESSITY_POLICY.encode('utf-8')),
        sequence=['b-control', 'c-control', 'd-control', 'a-completion-initial',
                  'compatibility', 'edit', 'unique-application', 'facts-fresh', 'completion-fresh'],
        candidate_requests={case:dict(file=f'{case}-candidate.json', sha256=digest(raw))
                            for case,raw in requests.items()},
        a_result_consumption='Consume the first accepted a response in the natural task; do not buy it twice.',
        historical_accounting=proof['strict_parent_replay']['accounting'],
        provider_requests=0, key_reads=0, execution_ready=False, execution_authorized=False,
        semantic_improvement_proven=False, qualified=False, publication_allowed=False,
        remaining=['Register the explicit candidate contract/receiver and inherited native routing.',
                   'Wire controls and natural stages to one cumulative budget and original receipts.',
                   'Verify the full simulated continuation through application and same-report fresh.',
                   'Bind a concrete new grant, time/budget envelope, frozen code/CI and live native preflight.']))
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in files.items():
        (output/name).write_bytes(raw)
    return dict(version=VERSION, output=str(output), files=inventory(output),
        imported_operations=proof['imported_operations'],
        historical_accounting=proof['strict_parent_replay']['accounting'],
        provider_requests=0, key_reads=0, execution_ready=False, publication_allowed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator', required=True, type=Path)
    parser.add_argument('--seal-sha', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--frozen-worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.frozen_worker:
        # Absolute script execution otherwise puts the development scripts folder
        # first. Explicit cwd is the already frozen parent, never an inferred path.
        sys.path.insert(0, str(Path.cwd()))
        try:
            result = frozen_readback(args.operator, args.seal_sha)
        except Exception as error:
            message = str(error)
            code = message if isinstance(error, ValueError) and re.fullmatch(
                r'(completion|launch|session|batch|host_workspace|codex_review_host)_[a-z0-9_]+', message) else 'completion_frozen_readback_failed'
            with args.output.open('x', encoding='utf-8') as stream:
                json.dump(dict(error_code=code, error_type=type(error).__name__), stream, ensure_ascii=True)
            raise SystemExit(1) from None
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(result, ensure_ascii=True, indent=2)+'\n')
    else:
        result = prepare(args.operator, args.seal_sha, args.output)
        print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
