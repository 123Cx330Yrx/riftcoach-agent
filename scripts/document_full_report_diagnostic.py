"""Three prospective initial reviews over the calibrated full reports.

Reuse the private screening runner and its baseline transport, not its paired
sampling experiment. No historical response, verdict or journal is invented.
"""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'scripts._full_report_screening_base', ROOT / 'scripts/document_sampling_screening.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

VERSION = 'document-full-report-initial-diagnostic-v1'
FIXTURE = 'data/evaluation/fixtures/host_full_report_calibration_20261012/materials.json'
FIXTURE_SHA = 'd3930389e748dfe4fb326f19b335242fe95587203890802b9e18b5a7650ab39b'
AUDIT = 'data/evaluation/results/host_full_report_calibration_20261012/close-audit.json'
AUDIT_SHA = '6ac2e8e0c8962f6268269d37a9c6ee930c325047da91dc4d730a900ffe78042b'
# Operator-only expectations; never included in material, task or SDK payload.
CASES = (('V2', 'accept'), ('H5', 'reject'), ('S8', 'reject'))
base.VERSION = base.runner.VERSION = VERSION
base.AUTH_VERSION = base.runner.AUTH_VERSION = 'document-full-report-initial-authorization-v1'
base.RUN_ID = 'document-full-report-initial-20261012'
base.ADAPTER_SOURCE = 'scripts/document_full_report_diagnostic.py'
base.OPERATOR_ROOT = Path(
    'C:/Users/33502/Documents/Agent/outputs/riftcoach-full-report-initial-20261012')
base.SAMPLES = ()


def fixture():
    raw = (ROOT / FIXTURE).read_bytes()
    if base.sha(raw) != FIXTURE_SHA:
        raise ValueError('full_report_fixture_changed')
    return base.read(ROOT / FIXTURE)


def report_text(case):
    blocks = case['report']
    if [b['block'] for b in blocks] != list(range(1, 17)):
        raise ValueError('full_report_fixture_blocks')
    # Preserve every calibrated block byte, including the table separators.
    # The existing production parser splits two heading/table groups, yielding
    # 18 request blocks. Do not force its indices to the calibration's 16.
    return '\n\n'.join(b['text'] for b in blocks)


def source_inputs(report):
    source = next(s for c, s in base.qualification.frozen_cases()[0]
                  if c['key'] == 'claim-scope:1')
    return base.TimedDocumentWorkflow.build_inputs(replace(source, report=report))


def source_payload(text):
    prefix = '[UNTRUSTED DATA]\n'
    suffix = '\n[END UNTRUSTED DATA]'
    if not text.startswith(prefix) or not text.endswith(suffix):
        raise ValueError('full_report_source_envelope')
    return base.strict_json(text[len(prefix):-len(suffix)])


def source_facts(payload):
    value = deepcopy(payload)
    # These three digests bind the new report as well as its unchanged facts.
    # Only those bindings may differ from the calibrated source message.
    del value['source_index']['source_digest']
    del value['computed_evidence']['source_digest']
    del value['source_roots']['catalog_sha256']
    return value


def controls():
    fixed = fixture()
    cases = {c['case_id']: c for c in fixed['cases']}
    rows = []
    for case_id, expected in CASES:
        case = cases[case_id]
        report = report_text(case)
        inputs = source_inputs(report)
        request = base.TimedDocumentWorkflow.make_request(inputs)
        if (request.messages[0].content != fixed['full_policy_text']
                or request.messages[3].content != fixed['deterministic_source_message']
                or source_facts(source_payload(request.messages[2].content)) !=
                   source_facts(source_payload(fixed['source_message']))):
            raise ValueError('full_report_calibrated_source_changed')
        request = replace(request, metadata={**request.metadata,
            'coach_budget_contract': 'coach-bounded-review-v2'})
        request = base.identity.prepare_request(request, base.identity.BASELINE)
        material = dict(report_origin=fixed['report_origin'],
            source_key=case_id, source_stage='initial', report=report,
            calibrated_blocks=case['report'], current_input_json=inputs.data_json,
            source_message=request.messages[2].content,
            deterministic_source_message=request.messages[3].content,
            full_policy_text=request.messages[0].content,
            fixture_path=FIXTURE, fixture_sha256=FIXTURE_SHA,
            provenance='New authored report over retained public source. No prior Provider stage exists for this report.')
        raw = base.identity.request_bytes(request)
        row = dict(key=f'report-{case_id}:initial', variant=base.identity.BASELINE,
            source_key=case_id, source_stage='initial', stage='initial',
            expected_verdict=expected, request_sha256=base.sha(raw),
            report_sha256=base.sha(report.encode()), material_sha256=base.sha(base.options.canonical(material)),
            policy_sha256=base.sha(request.messages[0].content.encode()),
            temperature=request.temperature)
        rows.append((row, material, request))
    return rows


_prepare = base.prepare


def prepare(*, root_thread_id, independent_thread_id):
    plan, rows = _prepare(root_thread_id=root_thread_id, independent_thread_id=independent_thread_id)
    if base.sha((ROOT / AUDIT).read_bytes()) != AUDIT_SHA:
        raise ValueError('full_report_calibration_audit_changed')
    from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
    price = DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    count = len(rows)
    cost = count * (Decimal(64000) * price.input_cost_per_million +
                    Decimal(32768) * price.output_cost_per_million) / 1_000_000
    for path in (FIXTURE, AUDIT, 'scripts/document_sampling_screening.py',
                 'tests/test_document_full_report_diagnostic.py'):
        plan['source_sha256'][path] = base.sha((ROOT / path).read_bytes())
    plan.pop('candidate_marker')
    plan.pop('pair_policy')
    plan.update(source_seal_sha256={}, calibration_audit_sha256=AUDIT_SHA,
        runner_contract=VERSION, transport_id=base.identity.TRANSPORT,
        scope='Three newly authored full reports; one baseline initial review each. No edits, fresh, retries or product qualification.',
        report_projection='Join 16 calibrated text blocks with two newlines; unchanged parser yields 18 report blocks.',
        prior_exposure='Independent reviewer previously reviewed these authored reports; this is a familiar-source development diagnostic, not a blind holdout.',
        limitations=['Preparation and calibration do not establish Provider semantics.',
                     'Three single observations do not establish stability or causality.',
                     'No old batch is reopened, recertified or assigned qualification.'],
        budget=dict(max_calls=count, role_calls={'glm-5.3': count, 'glm-5.3-flash': 0},
            max_tokens=count * 96768, max_active_seconds=count * 600, max_host_seconds=86400,
            per_request_seconds=600, per_request_output=32768,
            estimated_uncached_cny=str(cost), hard_billing_cap=False))
    return plan, rows


def inputs_for(cell, material):
    inputs = source_inputs(material['report'])
    if inputs.data_json != material['current_input_json']:
        raise ValueError('full_report_inputs_changed')
    return inputs


_host_task = base.host.task


def host_task(*args, **kwargs):
    # Retain the complete established binding and policy validation. Replace
    # only the historical-context wording, which is false for new reports.
    value = json.loads(_host_task(*args, **kwargs))
    replacements = {
        'original source, historical initial journal/request and all source citations. ':
        'complete source messages, calibrated report text and all source citations. '
        'This is a new authored report with no historical Provider stage or initial journal. ',
        'Historical Provider stages are context, never the new verdict or Host opinion. ':
        'Judge the actual new Provider response independently; prior calibration is not its verdict. ',
        'Do not read primary notes, host-reviews, other variants or expected case labels. ':
        'Do not read primary notes, calibration results, batch code/plan, other tasks or expected labels. '
        'Use only this checkpoint and the exact local task artifacts; use the supplied standalone '
        'artifact verifier for hashes, never a batch builder. ',
    }
    for old, new in replacements.items():
        if value['instructions'].count(old) != 1:
            raise ValueError('full_report_host_task_template_changed')
        value['instructions'] = value['instructions'].replace(old, new)
    return json.dumps(value, ensure_ascii=False)


base.controls = controls
base.prepare = prepare
base.inputs_for = base.runner.inputs_for = inputs_for
base.host.task = host_task
# The private module's original entrypoints resolve these overrides at call
# time; no shared module, historical plan or default product route is changed.
Package = base.Package
runner = base.runner
identity = base.identity
transport = base.transport


if __name__ == '__main__':
    base.main()
