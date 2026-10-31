"""New development report pair, teaching-only initial comparisons. No retries."""
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import json
import subprocess
import sys

from scripts.document_sampling_screening import load_private
from scripts.host_review_workspace import HostReviewWorkspace, VERSION as WORKSPACE_VERSION

ROOT = Path(__file__).resolve().parents[1]
diagnostic = load_private(ROOT / 'scripts/document_full_report_diagnostic.py', 'scripts._relation_full_report')
base = diagnostic.base
identity = load_private(ROOT / 'scripts/document_relation_request.py', 'scripts._relation_identity')
VERSION = 'document-relation-initial-diagnostic-v1'
CALIBRATION = 'data/evaluation/fixtures/host_relation_material_calibration_20261012/materials.json'
CALIBRATION_SHA = '53bea63165bc5eebfdbd8793c56e801b741f852b5f6738fea9b34a7fb6025f85'
CALIBRATION_TASK = 'data/evaluation/fixtures/host_relation_material_calibration_20261012/task.txt'
CALIBRATION_TASK_SHA = '61affed961e66a6543e890020fcd4fd4819b4490837fd5c3d650980a7c1290ab'
CALIBRATION_AUDIT = 'data/evaluation/results/host_relation_material_calibration_20261012/close-audit.json'
CALIBRATION_AUDIT_SHA = '9fc5ce547889deb7208b4a4a4b6260e3b400bac0e500e61ba40d706b9e7fb670'
base.VERSION = base.runner.VERSION = VERSION
base.AUTH_VERSION = base.runner.AUTH_VERSION = 'document-relation-initial-authorization-v1'
base.RUN_ID = 'document-relation-initial-20261012'
base.ADAPTER_SOURCE = 'scripts/document_relation_diagnostic.py'
base.REQUEST_SOURCE = 'scripts/document_relation_request.py'
base.IDENTITY = 'scripts.document_relation_request'
base.OPERATOR_ROOT = Path('C:/Users/33502/Documents/Agent/outputs/riftcoach-relation-initial-20261012')
base.identity = base.runner.identity = base.host.identity = base.transport.identity = identity
runner, transport = base.runner, base.transport

OVERVIEW = ('这份观摩只描述DK ShowMaker#KR1的五局历史排位：2胜3负；观摩对象不是阅读者。'
    '中单四局2胜2负，另有一局辅助负场。中单胜局的经济和伤害均值较高，补刀均值则略低。'
    '混合位置的补刀、经济和伤害均值受到辅助局较低数值的影响；视野和早死不沿用这个方向概括。'
    '下面把全部五局与仅中单的比较分开，不把样本观察当成胜负原因或阅读者的训练基线。[K2][K5]')
CORRECT_COMPARISON = ('全部五局15分钟前死亡的胜组均值为2.50次，负组约2.67次。仅中单时，'
    '胜场逐局为3、2次，负场为0、1次，均值分别2.50与0.50；每个中单胜场的值都高于每个中单负场。'
    '较少早死出现在本次中单负场，不等于数值未区分这四个观测，也不能据此确定早死对胜负的因果作用。[K1][K5]\n\n'
    '中单补刀/分钟的胜场为8.95、8.66，负场为9.64、8.38；胜负均值为8.805、9.01。'
    '两组取值区间重叠，不能说每个胜场都高于每个负场。全样本补刀差距受辅助局明显影响；'
    '伤害差距则在中单内部已存在，不能主要归因于辅助局。均值方向、逐行比较和胜负原因分别核对。')
WRONG_COMPARISON = CORRECT_COMPARISON.replace(
    '每个中单胜场的值都高于每个中单负场。', '这些数值说明中单早死的胜负组均值相同。').replace(
    '两组取值区间重叠，不能说每个胜场都高于每个负场。', '这些补刀数值说明每个中单胜场都高于每个中单负场。')


def calibration():
    for path, expected in ((CALIBRATION, CALIBRATION_SHA), (CALIBRATION_TASK, CALIBRATION_TASK_SHA),
                           (CALIBRATION_AUDIT, CALIBRATION_AUDIT_SHA)):
        if base.sha((ROOT / path).read_bytes()) != expected:
            raise ValueError('relation_calibration_changed')
    audit = base.read(ROOT / CALIBRATION_AUDIT)
    for name, expected in audit['files'].items():
        if base.sha((ROOT / CALIBRATION_AUDIT).with_name(name).read_bytes()) != expected:
            raise ValueError('relation_calibration_evidence_changed')
    return base.read(ROOT / CALIBRATION)


def reports():
    source = next(s for c, s in base.qualification.frozen_cases()[0] if c['key'] == 'claim-scope:1')
    inputs = base.TimedDocumentWorkflow.build_inputs(source)
    overview = inputs.source.blocks[3][1]
    comparison = next(text for _, text in inputs.source.blocks if text.startswith('全样本口径下早期死亡'))
    if source.report.count(overview) != 1 or source.report.count(comparison) != 1:
        raise ValueError('relation_report_projection')
    for key, text, expected in (('R4', CORRECT_COMPARISON, 'accept'), ('T9', WRONG_COMPARISON, 'reject')):
        report = source.report.replace(overview, OVERVIEW, 1).replace(comparison, text, 1)
        yield key, report, expected


def controls():
    fixed = calibration()
    calibrated = {case['case_id']: case for case in fixed['cases']}
    rows = []
    for key, report, expected in reports():
        inputs = diagnostic.source_inputs(report)
        original = base.TimedDocumentWorkflow.make_request(inputs)
        original = replace(original, metadata={**original.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
        case = calibrated[key]
        if (list(inputs.source.blocks) != [(b['block'], b['text']) for b in case['report']]
                or inputs.data_json != case['current_input_json']
                or original.messages[0].content != fixed['full_policy_text']
                or original.messages[2].content != case['source_message']
                or original.messages[3].content != case['deterministic_source_message']):
            raise ValueError('relation_calibrated_material_changed')
        for variant in identity.VARIANTS:
            request = identity.prepare_request(original, variant)
            if identity.projection(request) != original:
                raise ValueError('relation_pair_changed')
            material = dict(report_origin='New author-developed report on familiar public sources; not independent holdout.',
                source_key=key, source_stage='initial', report=report, current_input_json=inputs.data_json,
                source_message=request.messages[2].content, deterministic_source_message=request.messages[3].content,
                full_policy_text=request.messages[0].content,
                provenance='Derived from frozen claim-scope:1, replacing overview and comparison. No historical Provider stage for this report.')
            cell = dict(key=f'{key}-{variant}:initial', variant=variant, source_key=key, source_stage='initial',
                stage='initial', expected_verdict=expected, request_sha256=identity.request_sha(request),
                report_sha256=base.sha(report.encode()), material_sha256=base.sha(base.options.canonical(material)),
                policy_sha256=base.sha(request.messages[0].content.encode()), temperature=request.temperature)
            rows.append((cell, material, request))
    return rows


def prepare(*, root_thread_id, independent_thread_id):
    # Use generic preparation, not the earlier three-report calibration plan.
    plan, rows = diagnostic._prepare(root_thread_id=root_thread_id, independent_thread_id=independent_thread_id)
    from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
    price = DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    count = len(rows)
    for path in ('scripts/document_full_report_diagnostic.py', 'scripts/document_sampling_screening.py',
                 'scripts/report_relation_contrast.py', 'scripts/host_review_workspace.py',
                 'tests/test_document_relation_diagnostic.py', CALIBRATION, CALIBRATION_TASK, CALIBRATION_AUDIT):
        plan['source_sha256'][path] = base.sha((ROOT / path).read_bytes())
    plan.update(source_seal_sha256={}, runner_contract=VERSION, transport_id=identity.TRANSPORT,
        calibration_material_sha256=CALIBRATION_SHA, calibration_audit_sha256=CALIBRATION_AUDIT_SHA,
        host_workspace_contract=WORKSPACE_VERSION, candidate_marker=identity.VERSION,
        pair_policy='For each NEW development report, baseline then teaching candidate; all other request fields and complete sources identical.',
        scope='Two new familiar-source development reports, four initial requests only. No generation/edit/fresh/retry/qualification.',
        prior_exposure='Sources and failure mechanisms are known development material; the reused independent reviewer has calibrated both reports. Not a blind holdout. Old H5/V2/S8 are not reopened.',
        report_projection='Full Coach report with original sections and unchanged source facts; author-written overview/comparison.',
        budget=dict(max_calls=count, role_calls={'glm-5.3': count, 'glm-5.3-flash': 0}, max_tokens=count*96768,
            max_active_seconds=count*600, max_host_seconds=86400, per_request_seconds=600, per_request_output=32768,
            estimated_uncached_cny=str(count*(Decimal(64000)*price.input_cost_per_million+
                Decimal(32768)*price.output_cost_per_million)/1_000_000), hard_billing_cap=False))
    plan['execution_checks'] += ['absolute-cwd-python-startup', 'author-answer-outside-run-inventory']
    return plan, rows


base.controls = controls
base.prepare = prepare
Package = base.Package
workspace = HostReviewWorkspace(cwd=ROOT, python=sys.executable,
    answers=base.OPERATOR_ROOT / 'author-answers', evidence_roots=(ROOT / 'data/runs',))
workspace.install(runner)


def execution_paths_preflight():
    """Prove the exact dispatch interpreter can start the checkpoint helper."""
    workspace.validate_paths()
    probe = subprocess.run([str(workspace.python), '-c',
        'import json,sys; from pathlib import Path; '
        'from scripts import host_review_task_checkpoint; '
        'print(json.dumps(dict(cwd=str(Path.cwd().resolve()),python=str(Path(sys.executable).resolve()))))'],
        cwd=workspace.cwd, capture_output=True, text=True, timeout=30, check=True)
    value = json.loads(probe.stdout)
    if (Path(value['cwd']) != ROOT.resolve(strict=True)
            or Path(value['python']) != workspace.python.resolve(strict=True)):
        raise ValueError('relation_execution_tuple_mismatch')
    return value


_run = base.run


def run(args):
    # Before native startup, run creation, credential access or Provider IO.
    execution_paths_preflight()
    return _run(args)


base.run = run

if __name__ == '__main__':
    base.main()
