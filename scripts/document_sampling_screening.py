"""Bounded paired review-temperature screening with native dual review.

This is an isolated diagnostic.  It reuses the owned stream bridge and the
existing full-source review gates, but never changes a production identity or
reopens a historical run.  The five fixed samples are sent in pairs:
temperature=1.0 control, then explicitly marked temperature=0.2 candidate.
"""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from types import SimpleNamespace

from app.evaluation import document_review_qualification as qualification
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_stream_bridge import RESPONSE, REQUEST
from app.evaluation.role_task_outcome import stage_identity
from scripts import prepare_document_semantic_options as options
from scripts import prepare_document_semantic_comparison as preparation
from scripts.report_timed_document_workflow import TimedDocumentWorkflow
from scripts.review_independence_contract import require_execution_event_source
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_full15_resumption_candidate import _validate_reviews
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.diagnose_block_review_route import route_environment
from scripts.codex_review_event_source import CodexReadOnlyClient, CodexHostReviewEventSource
from scripts import host_review_task_checkpoint as checkpoint
from scripts.export_partitioned_review import public_response
from scripts.review_independence_contract import MODE_V2, FINAL_POLICY, freeze_v2_identity

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'document-sampling-screening-v1'
AUTH_VERSION = 'document-sampling-screening-authorization-v1'
RUN_ID = 'document-sampling-screening-20261011'
ADAPTER_SOURCE = 'scripts/document_sampling_screening.py'
REQUEST_SOURCE = 'scripts/document_sampling_screening_request.py'
IDENTITY = 'scripts.document_sampling_screening_request'
OPERATOR_ROOT = Path('C:/Users/33502/Documents/Agent/outputs/riftcoach-bounded-sampling-screening-20261011')
SAMPLES = (
    ('claim-scope:4', 'initial', 'data/evaluation/results/golden_document_full15_time600_result_20261010.json', '30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576', 'accept'),
    ('scope:3', 'final', 'data/evaluation/results/golden_document_full15_time600_result_20261010.json', '30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576', 'accept'),
    ('scope:4', 'initial', 'data/evaluation/results/golden_document_full15_time600_result_20261010.json', '30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576', 'reject'),
    ('observed:3', 'final', 'data/evaluation/results/golden_document_remaining4_time600_result_20261011.json', 'a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec', 'accept'),
    ('observed:5', 'initial', 'data/evaluation/results/golden_document_remaining4_time600_result_20261011.json', 'a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec', 'reject'),
)


def load_private(path, name):
    spec = importlib.util.spec_from_file_location(name, Path(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


identity = load_private(ROOT / REQUEST_SOURCE, 'scripts._sampling_identity')
transport = load_private(ROOT / 'scripts/document_semantic_transport.py', 'scripts._sampling_transport')
host = load_private(ROOT / 'scripts/document_semantic_host_task.py', 'scripts._sampling_host')
runner = load_private(ROOT / 'scripts/document_semantic_comparison.py', 'scripts._sampling_base_runner')
transport.identity = identity
transport.sha = lambda raw: hashlib.sha256(raw).hexdigest()
_transport_validate_complete = transport.validate_complete
def _sampling_validate_complete(directory, request, response):
    receipt = _transport_validate_complete(directory, request, response)
    receipt.update(model=response.model, temperature=request.temperature)
    return receipt
transport.validate_complete = _sampling_validate_complete
host.identity = identity
host.stage_identity = stage_identity
runner.identity = identity
runner.transport = transport
runner.host = host
runner.ROOT = ROOT
runner.VERSION = VERSION
runner.AUTH_VERSION = AUTH_VERSION


def read(path):
    return strict_json(Path(path).read_text(encoding='utf-8'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_request(raw):
    value = json.loads(raw)
    request = REQUEST.validate_json(raw, strict=True)
    return replace(request, **{k: value[k] for k in ('temperature', 'timeout_s', 'top_p')})


host.preparation = SimpleNamespace(read_request=read_request, sha=sha, options=options)


def _source_map():
    return {cell['key']: source for cell, source in qualification.frozen_cases()[0]}


def controls():
    sources = _source_map()
    rows = []
    for index, (key, stage, seal_path, seal_sha, expected) in enumerate(SAMPLES, 1):
        seal_raw = (ROOT / seal_path).read_bytes()
        if sha(seal_raw) != seal_sha:
            raise ValueError('sampling_source_seal_changed')
        seal = json.loads(seal_raw)
        relative = key.replace(':', '-') + '/' + stage
        original = seal['public_json_contents'][relative + '/issued-request.json']
        original_request = read_request(json.dumps(original, ensure_ascii=False).encode())
        report = seal['public_json_contents'][relative + '/stage.json']['report']
        source = replace(sources[key], report=report)
        inputs = TimedDocumentWorkflow.build_inputs(source)
        rebuilt = TimedDocumentWorkflow.make_request(inputs)
        rebuilt = replace(rebuilt, timeout_s=original_request.timeout_s,
            metadata={**rebuilt.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
        if rebuilt != original_request:
            raise ValueError('sampling_complete_inputs_changed')
        material = dict(original_source=seal['public_json_contents'][key.replace(':', '-') + '/source.json'],
            current_input_json=inputs.data_json, report=report,
            original_stage=seal['public_json_contents'][relative + '/stage.json'],
            original_request=original,
            initial_stage=seal['public_json_contents'][key.replace(':', '-') + '/initial/stage.json'],
            initial_request=seal['public_json_contents'][key.replace(':', '-') + '/initial/issued-request.json'],
            source_seal=seal_path, source_seal_sha256=seal_sha, source_key=key, source_stage=stage)
        material_sha = sha(options.canonical(material))
        for variant in (identity.BASELINE, identity.CANDIDATE):
            request = identity.prepare_request(rebuilt, variant)
            raw = identity.request_bytes(request)
            row = dict(key=f'sample-{index}:{variant}', variant=variant,
                source_key=key, source_stage=stage, stage=stage, expected_verdict=expected,
                request_sha256=sha(raw), original_request_sha256=sha(identity.request_bytes(
                    identity.prepare_request(rebuilt, identity.BASELINE))),
                original_issued_request_sha256=sha(json.dumps(original, ensure_ascii=False).encode()),
                report_sha256=sha(report.encode()), material_sha256=material_sha,
                policy_sha256=sha(request.messages[0].content.encode()),
                temperature=request.temperature, candidate_marker=(
                    'document-review-sampling-temperature-02-v1' if variant == identity.CANDIDATE else None))
            rows.append((row, material, request))
    return rows


def prepare(*, root_thread_id, independent_thread_id):
    rows = controls()
    price = __import__('app.runtime.coach_contract', fromlist=['DOCUMENT_REVIEW_COACH_CONTRACT']).DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    from decimal import Decimal
    cost = len(rows) * (Decimal(64000) * price.input_cost_per_million + Decimal(32768) * price.output_cost_per_million) / 1_000_000
    source_paths = tuple(dict.fromkeys((*qualification.SOURCE_FILES, *preparation.FILES,
        REQUEST_SOURCE, ADAPTER_SOURCE,
        'scripts/document_semantic_transport.py', 'scripts/document_semantic_host_task.py',
        'scripts/codex_review_event_source.py', 'scripts/host_review_task_checkpoint.py',
        'scripts/run_boundary_examples_v2.py', 'scripts/run_full15_resumption_candidate.py',
        'scripts/report_timed_document_workflow.py', 'scripts/review_independence_contract.py',
        'app/evaluation/document_review_qualification.py', 'app/evaluation/golden_stream_bridge.py',
        'app/evaluation/golden_journal.py', 'app/runtime/coach_contract.py',
        'app/runtime/coach_budget.py', 'app/runtime/review_sender.py',
        'scripts/role_development_host_clock.py', 'scripts/run_scope_resolution_diagnostic.py',
        'scripts/full15_resumption_evidence.py', 'scripts/document_review_host_task.py',
        'scripts/run_role_coach_development.py', 'scripts/run_golden_inference_development.py',
        'scripts/export_partitioned_review.py', 'app/evaluation/document_review_timing_adapter.py',
        'app/evaluation/document_review_identity.py', 'scripts/report_contrast_review.py',
        'app/evaluation/golden_inference_scope_v5.py',
        'app/evaluation/role_task_outcome.py',
        'app/evaluation/golden_review_experiment.py',
        'app/providers/zhipu_stream_adapter.py', 'app/model_runtime.py',
        'tests/test_document_sampling_screening.py')))
    plan = dict(kind=VERSION, run_id=RUN_ID, cells=[r[0] for r in rows],
        sequence=[r[0]['key'] for r in rows], identity=IDENTITY,
        source_sha256={p: sha((ROOT / p).read_bytes()) for p in source_paths},
        source_seal_sha256={p: sha((ROOT / p).read_bytes()) for p in set(s[2] for s in SAMPLES)},
        sdk_retries=0, labels_sent_to_model=False, execution_authorized=False,
        execution_ready=False, native_preflight_verified=False,
        runner_contract='document-sampling-screening-run-v1',
        execution_checks=['exact-source-package', 'explicit-cost-authorization',
                          'clean-same-HEAD-public-CI', 'current-native-principals'],
        production_admitted=False, original15_qualified=False, new_qualification=0,
        host_review_submission_mode=MODE_V2, host_review_evidence_policy=FINAL_POLICY,
        root_thread_id=root_thread_id,
        review_principals={'primary': {'principal_id': root_thread_id},
                           'independent': {'principal_id': independent_thread_id}},
        max_host_seconds=86400,
        budget=dict(max_calls=10, role_calls={'glm-5.3': 10},
            max_tokens=967680, max_active_seconds=3000, max_host_seconds=86400,
            per_request_seconds=600, per_request_output=32768,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        candidate_marker='document-review-sampling-temperature-02-v1',
        pair_policy='Each fixed sample is sent once at temperature=1.0 then once at temperature=0.2.',
        recovery_dispatch_policy='Exactly one NEW_TASK per native turn; same checkpoint recovery uses MESSAGE only.',
        semantic_failure_rule='Record a semantic rejection or Host disagreement for that sample and continue only the next independent sample; never retry.',
        hard_failure_rule='Identity/source/native/checkpoint/protocol/transport/budget/availability failure stops the batch.',
        scope='Five fixed complete historical review requests, paired current and candidate temperature only; diagnostic evidence, not complete15 or qualification.',
        limitations=['No generation, revision or fresh stage is purchased by this run.',
            'Historical cases and prior qualifications remain immutable and separate.',
            'Passing this screen cannot grant new qualification or switch production defaults.'])
    return freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id), rows


class Package:
    def __init__(self, directory):
        self.directory = Path(directory)

    def write(self, *, root_thread_id, independent_thread_id):
        plan, rows = prepare(root_thread_id=root_thread_id,
            independent_thread_id=independent_thread_id)
        self.directory.mkdir(parents=True, exist_ok=False)
        manifests = []
        for row, material, request in rows:
            arm = self.directory / row['key'].replace(':', '-')
            arm.mkdir()
            raw = identity.request_bytes(request)
            (arm / 'prepared-request.json').write_bytes(raw)
            (arm / 'material.json').write_bytes(options.canonical(material))
            manifests.append(dict(key=row['key'], request_path=(arm.name + '/prepared-request.json'),
                request_sha256=sha(raw), material_path=arm.name + '/material.json',
                material_sha256=sha(options.canonical(material))))
        value = dict(preparation_plan=plan, plan_sha256=sha(options.canonical(plan)),
            files=manifests, provider_calls=0, native_reviews=0)
        write_new_json(self.directory / 'plan.json', value)
        self.verify()
        return value

    def verify(self):
        value = read(self.directory / 'plan.json')
        if set(value) != {'preparation_plan', 'plan_sha256', 'files',
                          'provider_calls', 'native_reviews'}:
            raise ValueError('sampling_package_fields_changed')
        plan, rows = prepare(root_thread_id=value['preparation_plan']['root_thread_id'],
            independent_thread_id=value['preparation_plan']['review_principals']['independent']['principal_id'])
        if value['preparation_plan'] != plan or value['plan_sha256'] != sha(options.canonical(plan)):
            raise ValueError('sampling_package_plan_changed')
        expected = {'plan.json'}
        manifests = []
        for row, material, request in rows:
            arm = row['key'].replace(':', '-')
            rp, mp = arm + '/prepared-request.json', arm + '/material.json'
            expected.update((rp, mp))
            raw = (self.directory / rp).read_bytes()
            mat = options.canonical(material)
            if raw != identity.request_bytes(request) or (self.directory / mp).read_bytes() != mat:
                raise ValueError('sampling_package_material_changed')
            manifests.append(dict(key=row['key'], request_path=rp, request_sha256=sha(raw),
                material_path=mp, material_sha256=sha(mat)))
        if value['files'] != manifests or value['provider_calls'] != 0 or value['native_reviews'] != 0:
            raise ValueError('sampling_package_inventory_changed')
        if {p.relative_to(self.directory).as_posix() for p in self.directory.rglob('*') if p.is_file()} != expected:
            raise ValueError('sampling_package_unexpected_file')
        return dict(verified=True, requests=len(rows), plan_sha256=value['plan_sha256'], provider_calls=0)


def selected(directory, key):
    value, rows = plan_for(directory)
    match = [x for x in rows if x[0]['key'] == key]
    if len(match) != 1:
        raise ValueError('sampling_key_unavailable')
    return value, match[0], Path(directory) / key.replace(':', '-')


def inputs_for(cell, material):
    source = next(s for c, s in qualification.frozen_cases()[0] if c['key'] == cell['source_key'])
    inputs = TimedDocumentWorkflow.build_inputs(replace(source, report=material['report']))
    if inputs.data_json != material['current_input_json']:
        raise ValueError('sampling_inputs_changed')
    return inputs


def reconstruct(directory, key):
    value, (cell, material, request), folder = selected(directory, key)
    raw = identity.request_bytes(request)
    if (folder / 'material.json').read_bytes() != options.canonical(material):
        raise ValueError('sampling_material_changed')
    response = RESPONSE.validate_json((folder / 'transport/raw-response.json').read_bytes())
    receipt = transport.validate_complete(folder / 'transport', request, response)
    if read(folder / 'transport/receipt.json') != receipt:
        raise ValueError('sampling_receipt_changed')
    wire, stage = host.stage_for(cell, inputs_for(cell, material), request, response)
    public_raw = options.canonical(public_response(json.loads(RESPONSE.dump_json(response))))
    if ((folder / 'issued-request.json').read_bytes() != raw
            or (folder / 'response.json').read_bytes() != public_raw
            or read(folder / 'stage.json') != stage):
        raise ValueError('sampling_stage_changed')
    bound = dict(plan_sha256=value['plan_sha256'], key=key, stage=cell['stage'],
        response_sha256=sha(public_raw), report_sha256=digest(stage['report']), request_sha256=sha(raw))
    required = dict(binding=bound, stage_sha256=stage_identity(stage))
    if read(folder / 'review-required.json') != required:
        raise ValueError('sampling_review_binding_changed')
    return value, cell, material, request, response, wire, stage, bound, folder


def task_for(directory, key):
    value, cell, _, request, _, _, stage, bound, folder = reconstruct(directory, key)
    return host.task(value['preparation_plan'], cell, stage, bound, folder,
        identity.request_bytes(request), folder / 'material.json')


def validate_submission(directory, key, submission, event_source):
    value, cell, _, _, _, _, stage, bound, folder = reconstruct(directory, key)
    plan = value['preparation_plan']
    for role, evidence in (('primary', 'primary_attestation'), ('independent', 'independent_source_event')):
        if set(submission[role]) != {'binding', 'stage_assessment', 'report_assessment', evidence}:
            raise ValueError('sampling_host_review_fields')
    expected_task = json.loads(task_for(directory, key))
    from scripts.full15_resumption_evidence import validate_checkpoint
    validate_checkpoint(folder, submission, expected_task, plan, bound)
    accepted = _validate_reviews(submission, stage, bound, plan, event_source,
        initial=cell['stage'] == 'initial')
    pinned_sha = checkpoint.digest((folder / 'task-checkpoint.json').read_bytes())
    checkpoint.read(folder / 'task-checkpoint.json', pinned_sha)
    independent = submission['independent']
    checkpoint.check_answer(folder / 'task-checkpoint.json', pinned_sha,
        options.canonical(dict(binding=bound, review={k: v for k, v in independent.items()
            if k != 'independent_source_event'})))
    return accepted


def outcome(cell, wire, bound, submission, accepted):
    matched = (wire.verdict == 'pass' and wire.score >= 85
        if cell['expected_verdict'] == 'accept' else wire.verdict == 'needs_revision')
    pa, ia = (submission[r]['stage_assessment']['accepted'] for r in ('primary', 'independent'))
    return dict(key=cell['key'], variant=cell['variant'], temperature=cell['temperature'],
        binding=bound, score=wire.score, verdict=wire.verdict,
        expected_verdict=cell['expected_verdict'], verdict_matched=matched,
        primary_accepted=pa, independent_accepted=ia, host_disagreement=pa != ia,
        semantic_accepted=accepted and matched, new_qualification=0)


def plan_for(directory):
    value = read(Path(directory) / 'plan.json')
    plan = value['preparation_plan']
    rebuilt, _ = prepare(root_thread_id=plan['root_thread_id'],
        independent_thread_id=plan['review_principals']['independent']['principal_id'])
    if (set(value) != {'preparation_plan', 'plan_sha256', 'execution_head', 'ci_run'}
            or not re.fullmatch(r'[a-f0-9]{40}', value['execution_head'])
            or not isinstance(value['ci_run'], str)
            or value.get('plan_sha256') != sha(options.canonical(plan)) or plan != rebuilt):
        raise ValueError('sampling_frozen_plan_changed')
    return value, controls()


# The generic runner is loaded in an isolated module object.  Bind only this
# diagnostic's reconstruction and review functions into that object; the
# historical runner module and its closed batches remain untouched.
runner.inputs_for = inputs_for
runner.reconstruct = reconstruct
runner.task_for = task_for
runner.validate_submission = validate_submission
runner.outcome = outcome
runner.plan_for = plan_for


def check_authorization(value, plan, head, ci_run, *, now=None):
    return runner.check_authorization(value, plan, head, ci_run, now=now)


def run(args):
    package = Package(args.package)
    package.verify()
    value = read(Path(args.package) / 'plan.json')
    plan = value['preparation_plan']
    head = verify_public_ci(args.ci_run)
    authorization = read(args.authorization)
    check_authorization(authorization, plan, head, args.ci_run)
    require_unchanged_checkout(head)
    directory = ROOT / 'data/runs/model_comparison' / plan['run_id']
    if directory.exists():
        raise ValueError('sampling_run_already_exists')
    with CodexReadOnlyClient(args.codex_executable) as client:
        preflight = verify_native_principals(client, plan)
        event_source = CodexHostReviewEventSource(client, plan)
        require_execution_event_source(plan, event_source)
        directory.mkdir(parents=True, exist_ok=False)
        write_new_json(directory / 'plan.json', dict(preparation_plan=plan, plan_sha256=value['plan_sha256'],
            execution_head=head, ci_run=args.ci_run))
        write_new_json(directory / 'authorization.json', authorization)
        write_new_json(directory / 'execution-preflight.json', preflight)
        _, rows = prepare(root_thread_id=plan['root_thread_id'],
            independent_thread_id=plan['review_principals']['independent']['principal_id'])
        _, settings = load_role_settings(args.env_file)
        provider = transport.SemanticProvider(settings)
        def before_send():
            require_unchanged_checkout(head)
            check_authorization(authorization, plan, head, args.ci_run)
            verify_native_principals(client, plan)
        with route_environment('direct'):
            return runner.observe(directory, plan, rows, provider, event_source, before_send=before_send)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify', 'run', 'material', 'submit', 'abort', 'replay', 'seal'))
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--codex-executable', type=Path)
    parser.add_argument('--root-thread-id')
    parser.add_argument('--independent-thread-id')
    parser.add_argument('--key')
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--reason', choices=('reviewer_unavailable', 'routing_failure', 'operator_stop'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    required = {'prepare': ('directory', 'root_thread_id', 'independent_thread_id'),
        'verify': ('directory',), 'run': ('package', 'authorization', 'ci_run', 'env_file', 'codex_executable'),
        'material': ('directory', 'key'), 'abort': ('directory', 'key', 'reason'),
        'submit': ('directory', 'key', 'notes', 'event_id', 'checkpoint', 'checkpoint_sha', 'codex_executable'),
        'replay': ('directory', 'codex_executable'), 'seal': ('directory', 'output', 'codex_executable')}[args.action]
    if any(not getattr(args, name) for name in required):
        parser.error('missing required arguments: ' + ','.join(required))
    if args.action == 'prepare':
        Package(args.directory).write(root_thread_id=args.root_thread_id,
            independent_thread_id=args.independent_thread_id)
        result = {'prepared': True, 'directory': str(args.directory)}
    elif args.action == 'verify':
        result = Package(args.directory).verify()
    elif args.action == 'run':
        result = run(args)
    elif args.action == 'material':
        value, cell_data, material, _, _, _, stage, bound, folder = reconstruct(args.directory, args.key)
        result = dict(binding=bound, stage=stage, material=material, task=json.loads(task_for(args.directory, args.key)),
            checkpoint_path=str(folder / 'task-checkpoint.json'), checkpoint_sha256=checkpoint.digest((folder / 'task-checkpoint.json').read_bytes()))
    elif args.action == 'abort':
        result = runner.abort(args.directory, args.key, args.reason)
    else:
        value, _ = plan_for(args.directory)
        with CodexReadOnlyClient(args.codex_executable) as client:
            source = CodexHostReviewEventSource(client, value['preparation_plan'])
            if args.action == 'submit':
                result = runner.submit(args.directory, args.key, read(args.notes), args.event_id,
                    source, args.checkpoint, args.checkpoint_sha)
            elif args.action == 'replay':
                result = runner.replay(args.directory, event_source=source)
            elif args.action == 'seal':
                result = runner.seal(args.directory, args.output, event_source=source)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.action == 'run' and not result['scan_completed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
