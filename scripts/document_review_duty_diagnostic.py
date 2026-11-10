"""Six authorized-input full/facts initial reviews, isolated from product gates."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

from scripts.document_sampling_screening import load_private
from scripts import document_review_duty_request as identity
from scripts import prepare_review_duty_probe as proposal
from scripts.host_review_workspace import HostReviewWorkspace, VERSION as WORKSPACE_VERSION

ROOT = Path(__file__).resolve().parents[1]
base = load_private(ROOT / 'scripts/document_sampling_screening.py', 'scripts._duty_screening')
runner, transport = base.runner, base.transport
VERSION = 'document-review-duty-diagnostic-v1'
PROPOSAL = 'data/evaluation/fixtures/review_duty_probe_20261014'
base.VERSION = runner.VERSION = VERSION
base.AUTH_VERSION = runner.AUTH_VERSION = 'document-review-duty-authorization-v1'
base.RUN_ID = 'document-review-duty-20261014'
base.ADAPTER_SOURCE = 'scripts/document_review_duty_diagnostic.py'
base.REQUEST_SOURCE = 'scripts/document_review_duty_request.py'
base.IDENTITY = 'scripts.document_review_duty_request'
base.OPERATOR_ROOT = identity.OBSERVATION_ROOT.parent
base.identity = runner.identity = base.host.identity = transport.identity = identity
base.SAMPLES = ()


def controls():
    prepared = proposal.prepare()
    folder = ROOT / PROPOSAL
    if {p.name for p in folder.iterdir()} != set(prepared):
        raise ValueError('duty_proposal_inventory_changed')
    for name, raw in prepared.items():
        if (folder / name).read_bytes() != raw:
            raise ValueError('duty_authorized_input_changed')
    public = base.read(ROOT / proposal.SEAL)['public_json_contents']
    rows = []
    for index, (key, historical_stage) in enumerate(proposal.CASES, 1):
        report = public[key.replace(':', '-') + '/' + historical_stage + '/stage.json']['report']
        source = next(s for c, s in base.qualification.frozen_cases()[0] if c['key'] == key)
        inputs = base.TimedDocumentWorkflow.build_inputs(replace(source, report=report))
        rebuilt = base.TimedDocumentWorkflow.make_request(inputs)
        rebuilt = replace(rebuilt, timeout_s=600,
            metadata={**rebuilt.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
        for variant in identity.VARIANTS:
            original = base.read_request(prepared[f'{index:02d}-{variant}.json'])
            request = identity.prepare_request(original, variant)
            if identity.projection(request) != rebuilt:
                raise ValueError('duty_complete_source_changed')
            material = dict(source_key=key, source_stage=historical_stage,
                report=report, current_input_json=inputs.data_json,
                source_message=request.messages[2].content,
                deterministic_source_message=request.messages[3].content,
                full_policy_text=request.messages[0].content,
                provenance='Complete historical report snapshot on familiar sources, reviewed as a new initial opinion. No earlier Provider opinion or Host judgment is supplied.')
            cell = dict(key=f'duty-{index}-{variant}:initial', variant=variant,
                source_key=key, source_stage=historical_stage, stage='initial',
                expected_verdict='accept' if index == 2 else 'reject',
                request_sha256=identity.request_sha(request),
                report_sha256=base.sha(report.encode('utf-8')),
                material_sha256=base.sha(base.options.canonical(material)),
                policy_sha256=base.sha(request.messages[0].content.encode('utf-8')),
                temperature=request.temperature)
            rows.append((cell, material, request))
    return rows


_prepare = base.prepare


def prepare(*, root_thread_id, independent_thread_id):
    plan, rows = _prepare(root_thread_id=root_thread_id, independent_thread_id=independent_thread_id)
    for path in ('scripts/document_sampling_screening.py', 'scripts/document_semantic_comparison.py',
                 'scripts/prepare_review_duty_probe.py', 'scripts/audit_full15_repair_readiness.py',
                 'scripts/document_review_duty_identity.py', 'scripts/stream_observation.py',
                 'scripts/host_review_workspace.py', 'tests/test_document_review_duty_diagnostic.py',
                 *[f'{PROPOSAL}/{name}' for name in proposal.prepare()]):
        plan['source_sha256'][path] = base.sha((ROOT / path).read_bytes())
    plan.update(source_seal_sha256={proposal.SEAL: proposal.SEAL_SHA},
        runner_contract=VERSION, transport_id=identity.TRANSPORT,
        host_workspace_contract=WORKSPACE_VERSION, candidate_marker=identity.VERSION,
        pair_policy='For each unchanged historical request: full then facts; system duty only, explicit development metadata. All six stages are new initial snapshots.',
        scope='Three historical contexts, six initial requests. No generation, edit, fresh, retries, replacement or qualification.',
        prior_exposure='Familiar development sources and reports, not holdout; single observations do not establish stability.',
        interpretation='Any substantive facts-arm defect rejects this candidate. Both pass or baseline non-reproduction gives no improvement evidence. Positive differences only support further development.',
        observation_contract=identity.VERSION, observation_root=str(identity.OBSERVATION_ROOT.absolute()),
        observation_required=True, route_contract='direct/open.bigmodel.cn/process-proxies-cleared/NO_PROXY-exact',
        budget=dict(max_calls=6, role_calls={'glm-5.3': 6, 'glm-5.3-flash': 0},
            max_tokens=580608, max_active_seconds=3600, max_host_seconds=86400,
            per_request_seconds=600, per_request_output=32768,
            estimated_uncached_cny=plan['budget']['estimated_uncached_cny'], hard_billing_cap=False))
    plan['execution_checks'] += ['absolute-cwd-python-startup', 'author-answer-outside-run-inventory',
                                'authorization-file-unchanged', 'complete-body-free-observations']
    return plan, rows


_host_task = base.host.task


def host_task(*args, **kwargs):
    value = json.loads(_host_task(*args, **kwargs))
    text = value['instructions']
    text = text.replace('original source, historical initial journal/request and all source citations.',
        'complete source messages, actual current policy and all source citations.')
    text = text.replace('Historical Provider stages are context, never the new verdict or Host opinion.',
        'No historical Provider opinion is supplied. This is a new initial opinion over a fixed report snapshot, not an edit or fresh stage. Do not search historical runs or batch code.')
    text = text.replace('the exact current policy.',
        'the exact current policy. Respect its actual duty boundary; do not demand excluded task-completion checks, and do not exempt factual claims, advice, cited support or correction coverage. A partial-duty pass cannot publish or qualify a product report.')
    value['instructions'] = text
    return json.dumps(value, ensure_ascii=False)


base.controls, base.prepare, base.host.task = controls, prepare, host_task
Package = base.Package
workspace = HostReviewWorkspace(cwd=ROOT, python=sys.executable,
    answers=base.OPERATOR_ROOT / 'author-answers', evidence_roots=(ROOT / 'data/runs',))
workspace.install(runner)


def audit_observations(directory):
    directory = Path(directory)
    plan = base.read(directory / 'plan.json')['preparation_plan']
    if (plan['observation_contract'] != identity.VERSION or plan['observation_required'] is not True
            or plan['observation_root'] != str(identity.OBSERVATION_ROOT.absolute())):
        raise ValueError('duty_observation_plan_changed')
    result = []
    for cell in plan['cells']:
        folder = directory / cell['key'].replace(':', '-') / 'transport'
        issued = folder / 'issued-request.json'
        if issued.exists():
            result.append(identity.verify_observation(folder / 'stream-001', issued.read_bytes(),
                complete_required=(folder / 'raw-response.json').exists()))
    return result


_validate, _observe, _replay = runner.validate_submission, runner.observe, runner.replay


def validate_submission(directory, key, submission, event_source):
    audit_observations(directory)
    return _validate(directory, key, submission, event_source)


def observe(directory, plan, rows, provider, event_source, **kwargs):
    before = kwargs.pop('before_send', lambda: None)
    def checked():
        audit_observations(directory)
        before()
    return _observe(directory, plan, rows, provider, event_source, before_send=checked, **kwargs)


def replay(directory, *, event_source):
    observations = audit_observations(directory)
    value = _replay(directory, event_source=event_source)
    value['body_free_observations'] = observations
    return value


runner.validate_submission, runner.observe, runner.replay = validate_submission, observe, replay


def execution_paths_preflight():
    workspace.validate_paths()
    probe = subprocess.run([str(workspace.python), '-c',
        'import json,sys; from pathlib import Path; from scripts import host_review_task_checkpoint; '
        'print(json.dumps(dict(cwd=str(Path.cwd().resolve()),python=str(Path(sys.executable).resolve()))))'],
        cwd=workspace.cwd, capture_output=True, text=True, timeout=30, check=True)
    value = json.loads(probe.stdout)
    if (Path(value['cwd']) != ROOT.resolve(strict=True)
            or Path(value['python']) != workspace.python.resolve(strict=True)):
        raise ValueError('duty_execution_tuple_mismatch')
    return value


_run, _check = base.run, base.check_authorization


def run(args):
    execution_paths_preflight()
    original = Path(args.authorization).read_bytes()
    def checked(*a, **kw):
        if Path(args.authorization).read_bytes() != original:
            raise ValueError('duty_authorization_file_changed')
        return _check(*a, **kw)
    base.check_authorization = checked
    try:
        return _run(args)
    finally:
        base.check_authorization = _check


base.run = run

if __name__ == '__main__':
    base.main()
