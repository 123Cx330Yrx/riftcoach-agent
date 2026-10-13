"""Read-only qualification of one sealed, same-combination original15 batch.

No execute command, Provider factory, credential loading or product registration.
Only the installed read-only native reader can supply CLI Host evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts.audit_original15_alignment import audit
from scripts.full_chain_evidence import FullChainEvidence, ROOT, VERSION as EVIDENCE, sha
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts.run_golden_inference_development import verify_public_ci

VERSION = 'full-chain-original15-qualification-v1'
PRINCIPALS = dict(primary='01a1248f-e18c-7282-92bf-7ceb2eb5dce4',
    independent='01a12f0c-bb7c-74e3-ad92-775eefbe399a')


def fail(code):
    raise ValueError('full_chain_qualification_' + code)


def read(path):
    from app.evaluation.golden_inference_scope_v5 import strict_json
    return strict_json(Path(path).read_text(encoding='utf-8'))


def pinned(path, expected):
    if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected) or sha(path) != expected:
        fail('file_pin')
    return read(path)


def prepare(*, execution_profile=None):
    alignment = audit()
    value = dict(kind=VERSION, combination_sha256=alignment['combination_sha256'],
        combination=alignment['prepared_combination'],
        validator_source_sha256={'scripts/qualify_full_chain_controls.py': sha(Path(__file__))},
        principal_ids=dict(PRINCIPALS),
        required_distinct_inputs=15, required_batches=1, historical_credit=False,
        execution_authorized=False, execution_ready=False, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False)
    if execution_profile is not None:
        from scripts.full_chain_execution import VERSION as profile, SOURCES
        if execution_profile != profile:
            fail('execution_profile')
        value.update(execution_profile=profile,
            execution_source_sha256={p: sha(ROOT/p) for p in SOURCES})
    return value


def require_plan(saved, preparation):
    if set(saved) != {'preparation_plan', 'plan_sha256', 'execution_head', 'ci_run'}:
        fail('execution_binding')
    plan, combination = saved['preparation_plan'], preparation['combination']
    if (plan.get('root_thread_id') != preparation['principal_ids']['primary']
            or {k: v.get('principal_id') for k, v in plan.get('review_principals', {}).items()}
            != preparation['principal_ids']):
        fail('principal_binding')
    if (plan.get('kind') != EVIDENCE or plan.get('case_selection') != 'full15'
            or plan.get('timing_mode') != 'time600' or plan.get('sdk_retries') != 0
            or plan.get('historical_reviews_reused') is not False
            or plan.get('request_timing_identity') != combination['request_timing_identity']
            or plan.get('candidate_policy') != combination['policy']
            or plan.get('candidate_editor') != combination['editor']
            or plan.get('host_review_evidence_policy') != combination['host_policy']
            or plan.get('author_workspace_contract') != combination['author_contract']
            or plan.get('observation_contract') != combination['observation_contract']
            or plan.get('per_case_budget') != combination['task_budget']):
        fail('combination')
    expected = combination['cases']
    if (len(expected) != 15 or len({v['input_sha256'] for v in expected}) != 15
            or len({v['key'] for v in expected}) != 15
            or plan.get('sequence') != [v['key'] for v in expected]
            or len(plan.get('cells', [])) != 15):
        fail('coverage')
    fields = dict(key='key', expected_initial='original_label', input_sha256='frozen_original_input_sha256',
        report_sha256='report_sha256', manifest_sha256='original_manifest_sha256',
        candidate_request_sha256='request_sha256')
    for cell, target in zip(plan['cells'], expected, strict=True):
        if any(cell.get(k) != target[v] for k, v in fields.items()):
            fail('case_binding')
    # The preparation also binds the read-only alignment producer, which is
    # not a business-run dependency. All business dependencies must match.
    source = dict(combination['source_sha256'])
    source.pop('scripts/audit_original15_alignment.py')
    if preparation.get('execution_profile') is not None:
        from scripts.full_chain_execution import VERSION as profile, RUN_ID, budget_for
        if (preparation['execution_profile'] != profile or plan.get('execution_profile') != profile
                or plan.get('run_id') != RUN_ID or plan.get('budget') != budget_for(plan)):
            fail('execution_profile')
        source.update(preparation['execution_source_sha256'])
    elif 'execution_profile' in plan:
        fail('execution_profile')
    if plan.get('source_sha256') != source:
        fail('source_binding')
    if (not isinstance(saved['execution_head'], str)
            or not re.fullmatch('[0-9a-f]{40}', saved['execution_head'])
            or not re.fullmatch('[1-9][0-9]*', str(saved['ci_run']))):
        fail('execution_binding')
    return plan


def require_coverage(sealed, preparation):
    if sealed.get('kind') != EVIDENCE + '-result':
        fail('seal_kind')
    result = sealed['execution_result']
    if (result.get('scan_completed') is not True or result.get('diagnostic_accepted') is not True
            or result.get('unexecuted_keys') != [] or result.get('unfinished_keys') != []
            or any(k in result for k in ('error_type', 'error_code', 'accounting_error_type'))):
        fail('incomplete_or_rejected')
    targets = preparation['combination']['cases']
    cases = result.get('cases', [])
    if len(cases) != 15 or [v['key'] for v in cases] != [v['key'] for v in targets]:
        fail('coverage')
    stages = []
    for case, target in zip(cases, targets, strict=True):
        expected = ['initial'] if target['original_label'] == 'accept' else ['initial', 'revision', 'final']
        if (case.get('semantic_accepted') is not True or 'semantic_failure' in case
                or [s['stage'] for s in case['stages']] != expected
                or any(s.get('host_accepted') is not True for s in case['stages'])):
            fail('case_or_stage_rejected')
        if target['original_label'] == 'accept':
            if case.get('initial_verdict') != 'pass' or type(case.get('initial_score')) is not int or case['initial_score'] < 85:
                fail('initial_verdict')
        elif (case.get('initial_verdict') != 'needs_revision' or case.get('final_verdict') != 'pass'
                or type(case.get('final_score')) is not int or case['final_score'] < 85):
            fail('repair_or_fresh')
        stages.extend(dict(key=case['key'], **stage) for stage in case['stages'])
    accounting = sealed['accounting']
    if (sealed['stages'] != stages or result['provider_calls'] != len(stages)
            or accounting['calls'] != len(stages) or accounting['unknown_usage_calls'] != 0
            or accounting['local_attempts_without_transport_receipt'] != 0
            or result['unknown_reserved_tokens'] != 0):
        fail('stage_accounting')
    return stages


def require_http_observations(session, sealed, stages):
    observations = sealed.get('body_free_observations', [])
    if len(observations) != len(stages) or len(sealed.get('author_evidence', {})) != len(stages):
        fail('author_or_observation_inventory')
    required = {'binding.json', 'sampling/anchor.json', 'sampling/observation.json', 'parent-audit.json'}
    for row in observations:
        if row.get('state') != 'valid' or set(row.get('files', {})) != required:
            fail('real_observation_required')
        side = session.observations / hashlib.sha256(row['worker_directory'].encode()).hexdigest()
        parent, sample = read(side/'parent-audit.json'), read(side/'sampling/observation.json')
        if (set(parent) != {'transport_complete', 'elapsed_ms', 'observation_present', 'observation_age_ms',
                'observation_valid', 'observation_failure', 'files'}
                or parent['transport_complete'] is not True or parent['observation_present'] is not True
                or parent['observation_valid'] is not True or parent['observation_failure'] is not False
                or sample.get('schema_version') != 'stream-observation-v1' or sample.get('body_free') is not True
                or type(sample.get('http_requests')) is not int or sample['http_requests'] != 1
                or type(sample.get('response_status')) is not int or not 200 <= sample['response_status'] < 300
                or sample.get('closed') is not True or sample.get('exception_type') is not None
                or type(sample.get('raw_bytes')) is not int or sample['raw_bytes'] <= 0):
            fail('real_observation_required')


def validate(*, preparation_path, preparation_sha, directory, seal_path, seal_sha, codex_executable):
    preparation = pinned(preparation_path, preparation_sha)
    profile = preparation.get('execution_profile')
    if preparation != prepare(execution_profile=profile):
        fail('preparation_changed')
    sealed = pinned(seal_path, seal_sha)
    stages = require_coverage(sealed, preparation)
    directory = Path(directory).absolute()
    saved = read(directory / 'plan.json')
    plan = require_plan(saved, preparation)
    paths = plan['evidence_paths']
    if Path(paths['directory']) != directory:
        fail('directory_binding')
    if profile is not None:
        from scripts.full_chain_execution import ControlledFullChain
        session = ControlledFullChain(**paths)
    else:
        session = FullChainEvidence(**paths)
    # A closed run already owns this lock. Refuse before replay could create it.
    if not (directory/'submission-close.lock').is_file():
        fail('closed_lock_missing')
    before = session.snapshot()
    originals = {p.relative_to(directory).as_posix(): sha(p) for p in directory.rglob('*') if p.is_file()}
    if originals != sealed['original_file_sha256']:
        fail('original_inventory')
    session.evidence.load_plan(directory)  # Complete current request/source/path identity.
    session.check()  # Original author bytes, sidecar SHA and strict file whitelist.
    require_http_observations(session, sealed, stages)
    # Exact checkout and public CI are required, as for the original executor.
    if verify_public_ci(str(saved['ci_run'])) != saved['execution_head']:
        fail('execution_head')
    with CodexReadOnlyClient(codex_executable) as client:
        source = CodexHostReviewEventSource(client, plan)
        rebuilt = session.evidence.replay(directory, event_source=source)
    if rebuilt != sealed:
        fail('seal_replay_changed')
    require_coverage(rebuilt, preparation)
    if (before != session.snapshot() or sha(preparation_path) != preparation_sha
            or sha(seal_path) != seal_sha or preparation != prepare(execution_profile=profile)):
        fail('evidence_changed_during_validation')
    return dict(kind=VERSION + '-result', combination_sha256=preparation['combination_sha256'],
        qualification_preparation_sha256=preparation_sha, validator_source_sha256=preparation['validator_source_sha256'],
        run_directory=str(directory), seal_path=str(Path(seal_path).absolute()), seal_sha256=seal_sha,
        execution_head=saved['execution_head'], ci_run=saved['ci_run'], accepted_inputs=15,
        certified_stages=len(stages), accounting=rebuilt['accounting'],
        original_file_sha256=originals, strict_native_replay=True, historical_credit=False,
        review_controls_qualified=True, actual_product_task_qualified=False, production_admitted=False,
        provider_calls_during_validation=0, execution_authorized=False,
        limits=['Familiar fixed controls, not holdout or natural Coach/Training tasks.',
            'No runtime registration, publishing permission or paid execution authorization.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'validate'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execution-profile')
    for name in ('preparation', 'directory', 'seal', 'codex-executable'):
        parser.add_argument('--' + name, type=Path)
    for name in ('preparation-sha', 'seal-sha'):
        parser.add_argument('--' + name)
    args = parser.parse_args()
    output = args.output.absolute()
    if output.exists():
        raise FileExistsError(output)
    if args.action == 'prepare':
        if output.resolve().is_relative_to(ROOT / 'data/runs'):
            fail('output_inside_run')
        result = prepare(execution_profile=args.execution_profile)
    else:
        if any(getattr(args, name) is None for name in
                ('preparation', 'preparation_sha', 'directory', 'seal', 'seal_sha', 'codex_executable')):
            parser.error('validate requires preparation and seal pins, directory and operator-supplied codex-executable')
        # Check output containment before any validation or external read.
        paths = read(args.directory / 'plan.json')['preparation_plan'].get('evidence_paths')
        if not isinstance(paths, dict) or not {'directory', 'answers', 'observations'} <= paths.keys():
            fail('legacy_evidence_paths')
        roots = [ROOT/'data/runs', *(Path(paths[k]).resolve() for k in ('directory', 'answers', 'observations'))]
        if output.resolve() != output or any(output.is_relative_to(p) for p in roots):
            fail('output_inside_evidence')
        result = validate(preparation_path=args.preparation, preparation_sha=args.preparation_sha,
            directory=args.directory, seal_path=args.seal, seal_sha=args.seal_sha,
            codex_executable=args.codex_executable)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(action=args.action, review_controls_qualified=result['review_controls_qualified'],
        production_admitted=False, provider_calls=0)))


if __name__ == '__main__':
    main()
