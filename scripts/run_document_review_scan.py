"""Independent initial-only scan of the eleven previously unexecuted controls.

Semantic rejection is data, not permission to retry. All evidence/transport/
identity/protocol/budget errors stop. This ledger cannot grant qualification.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import re

from pydantic import ValidationError
from app.evaluation import document_review_qualification as qualification
from scripts import run_document_review_diagnostic as diagnostic

base = diagnostic.base
shared = diagnostic.shared
workflow = diagnostic.workflow
EXPERIMENT = 'document-initial-remaining11-scan-20261009'
SEAL = 'data/evaluation/results/golden_document_original15_result_20261008.json'
SEAL_SHA = 'd225f75e39e850e62c7af2cefab1ec823d837e6c46fd65606e93da373d2ed4c5'
HISTORICAL = ('claim-scope:1', 'claim-scope:4', 'claim-scope:3', 'attribution:1')
KEYS = ('scope:4', 'scope:3', 'claim-scope:2', 'claim-scope:5', 'claim-scope:6',
        'claim-scope:7', 'observed:1', 'observed:2', 'observed:3', 'observed:4', 'observed:5')
SOURCE_FILES = tuple(dict.fromkeys((*diagnostic.SOURCE_FILES, *qualification.SOURCE_FILES,
    'scripts/run_document_review_scan.py', 'scripts/document_review_scan_handoff.py',
    'scripts/seal_document_review_scan.py')))


def arm_name(key):
    if key not in KEYS:
        raise ValueError('document_scan_key')
    return key.replace(':', '-')


def controls():
    if base.sha(base.ROOT / SEAL) != SEAL_SHA:
        raise ValueError('document_scan_historical_seal_changed')
    sealed = json.loads((base.ROOT / SEAL).read_bytes())
    prior = sealed['public_json_contents']['plan.json']['preparation_plan']
    material, requests = qualification.prepare_qualification()
    if (material['identity'] != prior['identity'] or material['cases'] != prior['cases']
            or tuple(r['key'] for r in sealed['execution_result']['cases']) != HISTORICAL):
        raise ValueError('document_scan_business_identity_changed')
    sources = {r['key']: s for r, s in qualification.frozen_cases()[0]}
    variants = []
    for row in material['cases']:
        if row['key'] in HISTORICAL:
            continue
        inputs = qualification.Workflow.build_inputs(sources[row['key']])
        request = qualification.Workflow.make_request(inputs)
        if (base.validate_request(request, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)
                != requests[row['key']] or base.size(request) > 64000):
            raise ValueError('document_scan_request_changed')
        variants.append((dict(row, synthetic_report=False), inputs, request))
    if tuple(c['key'] for c, *_ in variants) != KEYS:
        raise ValueError('document_scan_inventory')
    return material, variants


def prepare(*, root_thread_id, independent_thread_id):
    material, variants = controls()
    price = base.CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    cost = len(KEYS) * (Decimal(64000) * price.input_cost_per_million
        + Decimal(32768) * price.output_cost_per_million) / 1_000_000
    return base.freeze_v2_identity(dict(experiment=EXPERIMENT,
        cells=[c for c, *_ in variants], sequence=list(KEYS), historical_keys=list(HISTORICAL),
        historical_evidence=SEAL, historical_evidence_sha256=SEAL_SHA,
        preparation_sha256=base.canonical_sha(material), identity=material['identity'],
        source_sha256={p: base.digest((base.ROOT/p).read_text(encoding='utf-8')) for p in SOURCE_FILES},
        host_review_submission_mode=base.MODE_V2, host_review_evidence_policy=base.FINAL_POLICY,
        max_host_seconds=86400, budget=dict(max_calls=11, max_tokens=1064448,
            max_active_seconds=3300, per_request_output=32768, per_request_seconds=300,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        role_calls={'glm-5.3': 11, 'glm-5.3-flash': 0}, sdk_retries=0,
        model='glm-5.3', reasoning_effort='high', labels_sent_to_model=False,
        execution_authorized=False, product_admitted=False, original15_qualified=False,
        semantic_failure_rule='Record full-source rejection, disagreement or wrong verdict; continue to the next independent initial request. Never retry, edit or reassess.',
        stop_rule='First source, identity, native event, protocol, transport, budget or availability error stops. Closed batches cannot restart.',
        success_scope='Eleven initial assessments only; four separate historical cases are not contemporary controls or qualification credit.',
        decisions='Classify all observed failures and correct controls before selecting one common fix. If the candidate remains unsound, do not rerun original15 unchanged. Full same-version original15 remains first-failure-stop.'),
        root_thread_id=root_thread_id, primary_id=root_thread_id, independent_id=independent_thread_id)


def classify(cell, wire, submitted, bound):
    opinions = {role: submitted[role]['stage_assessment']['accepted']
                for role in ('primary', 'independent')}
    verdict_valid = ((wire.verdict == 'pass' and wire.score >= 85)
        if cell['expected_initial'] == 'accept' else wire.verdict == 'needs_revision')
    failures = []
    if not all(opinions.values()):
        failures.append('reviewer_disagreement' if opinions['primary'] != opinions['independent']
                        else 'dual_semantic_rejection')
    if not verdict_valid:
        failures.append('unexpected_verdict_or_score')
    return dict(key=cell['key'], binding=bound, host_accepted=all(opinions.values()),
        primary_accepted=opinions['primary'], independent_accepted=opinions['independent'],
        verdict=wire.verdict, score=wire.score, verdict_valid=verdict_valid,
        semantic_accepted=not failures, semantic_failures=failures)


class RecordedDiagnosticProvider(diagnostic.DocumentDiagnosticProvider):
    """Preserve actual budgeted request even if transport identity fails pre-I/O.

This is a local attempt artifact, never a substitute for a transport receipt.
"""
    def __init__(self, router, route, arm):
        super().__init__(router, route)
        self.arm = Path(arm)

    def chat(self, request):
        raw = base.validate_request(request, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)
        with (self.arm/'issued-request.json').open('xb') as stream:
            stream.write(raw)
        try:
            return super().chat(request)
        except BaseException as error:
            if not self.attempts:
                # Parent route/role checks can fail before its transport
                # attempt is appended. Keep an explicitly local attempt too.
                self.attempts.append(dict(ordinal=1, role='review', model='glm-5.3',
                    profile=self.reviewer.thinking_profile_id, transport_id=base.REVIEW_MODEL_TRANSPORT_ID,
                    request_sha256=base.sha(self.arm/'issued-request.json'), status='failed',
                    local_pre_transport=True, error=getattr(error,'code',type(error).__name__)))
            raise


def observe(factory, directory, plan, *, event_source, adjudicate=base.wait_reviews,
            before_send=lambda: None):
    base.require_execution_event_source(plan, event_source)
    material, variants = controls()
    if (plan['cells'] != [c for c, *_ in variants] or plan['sequence'] != list(KEYS)
        or plan['preparation_sha256'] != base.canonical_sha(material)
        or plan['role_calls'] != {'glm-5.3': 11, 'glm-5.3-flash': 0}):
        raise ValueError('document_scan_frozen_controls')
    clock = base.DevelopmentHostClock(directory, max_host_seconds=plan['max_host_seconds'])
    route = diagnostic.DocumentDiagnosticRoute(variants)
    router = RecordedDiagnosticProvider(factory(arm_name(KEYS[0])),
        diagnostic.DocumentDiagnosticRoute(variants[:1]), Path(directory)/arm_name(KEYS[0]))
    routers = [router]
    budget = base._ReceiptForwardingCoachBudgetedProvider(router, coach_contract=base.CONTRACT, clock=clock)
    budget.contract = diagnostic.DiagnosticLimits(route, plan['budget'])
    send = base.SharedBudgetReviewSender(budget)
    result = dict(experiment=EXPERIMENT, scan_completed=False, diagnostic_accepted=False,
        stages=[], product_admitted=False, original15_qualified=False, historical_credit=0)
    try:
        for index, (cell, inputs, prepared) in enumerate(variants):
            clock.before_send()
            before_send()
            remaining = plan['budget']['max_active_seconds'] - clock()
            if (remaining <= 0 or budget.calls >= plan['budget']['max_calls']
                or budget.tokens + budget.reserved_tokens + base.size(prepared)
                    + prepared.max_tokens > plan['budget']['max_tokens']):
                raise ValueError('document_scan_budget')
            if index:
                # Each independent task owns its receipt ordinal (1). The
                # shared budget is retained across all eleven tasks; product
                # transport's per-task nine-call guard remains unchanged.
                router = RecordedDiagnosticProvider(factory(arm_name(cell['key'])),
                    diagnostic.DocumentDiagnosticRoute([variants[index]]), Path(directory)/arm_name(cell['key']))
                routers.append(router)
                budget.provider = router
            arm = Path(directory)/arm_name(cell['key'])
            arm.mkdir(exist_ok=False)
            base.write_new_json(arm/'source.json', dict(input_json=inputs.data_json,
                report=inputs.source.report, synthetic_report=False))
            exchange = send(replace(prepared, timeout_s=min(prepared.timeout_s, remaining)))
            base.write_new_json(arm/'request.json', json.loads(base.validate_request(
                exchange.issued_request, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)))
            base.write_new_json(arm/'response.json', base.public_response(json.loads(base.RESPONSE.dump_json(exchange.response))))
            raw = base.tool_result(prepared, exchange)
            _, wire, journal = workflow.DocumentReviewWorkflow.validate_review(raw, inputs)
            stage = dict(stage='initial', report=inputs.source.report, journal=journal)
            base.write_new_json(arm/'stage.json', stage)
            bound = dict(plan_sha256=base.canonical_sha(plan), key=cell['key'], stage='initial',
                response_sha256=base.sha(arm/'response.json'), report_sha256=base.digest(stage['report']),
                request_sha256=exchange.receipt_request_sha256)
            base.write_new_json(arm/'review-required.json', dict(binding=bound,
                stage_sha256=base.stage_identity(stage),
                scope='Judge every finding, explanation, correction and advisory against complete report and sources under whole-context standard. Report assessment must be null.'))
            submitted = clock.adjudicate(arm/'review-required.json',
                plan['budget']['max_active_seconds'] - clock(), adjudicate)
            base.write_new_json(arm/'host-reviews.json', submitted)
            # False returns are semantic observations. Exceptions are never
            # reclassified as semantics and never authorize further requests.
            shared.validate_reviews(submitted, stage, bound, plan, event_source)
            result['stages'].append(classify(cell, wire, submitted, bound))
            if clock() >= plan['budget']['max_active_seconds']:
                raise ValueError('document_scan_budget')
            before_send()
        result['scan_completed'] = True
        result['diagnostic_accepted'] = all(s['semantic_accepted'] for s in result['stages'])
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(error, ValidationError):
            code = 'document_scan_schema_validation'
            result['validation_errors'] = error.errors(include_input=False, include_context=False, include_url=False)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,100}', code):
            result['error_code'] = code
    finally:
        attempts = [dict(a, ordinal=index+1, transport_ordinal=a['ordinal'])
            for index, r in enumerate(routers) for a in r.attempts]
        result.update(calls=budget.calls, known_tokens=budget.tokens,
            unknown_reserved_tokens=budget.reserved_tokens, attempts=attempts, timing=clock.summary(),
            unexecuted_keys=[k for k in KEYS if k not in [s['key'] for s in result['stages']]
                and k not in [KEYS[a['ordinal']-1] for a in attempts]],
            unadjudicated_keys=[KEYS[a['ordinal']-1] for a in attempts
                if KEYS[a['ordinal']-1] not in [s['key'] for s in result['stages']]])
        shared.close_result(directory, result)
    return result


def read_calls(directory):
    from app.evaluation.role_qualification import read_role_calls
    route = diagnostic.DocumentDiagnosticRoute(controls()[1])
    def role(request):
        if route.request_identity(request) != ('zhipu', 'glm-5.3'):
            raise ValueError('document_scan_role')
        return 'review'
    directory = Path(directory)
    actual = {p.name for p in directory.iterdir() if p.is_dir()} if directory.exists() else set()
    expected = [arm_name(k) for k in KEYS]
    if actual != set(expected[:len(actual)]):
        raise ValueError('document_scan_transport_inventory')
    calls = []
    for name in expected:
        attempt_path = directory.parent/name/'issued-request.json'
        rows = read_role_calls(directory/name, request_role=role) if (directory/name).exists() else []
        if not attempt_path.exists():
            if rows or any(p.is_file() for p in (directory/name).rglob('*')):
                raise ValueError('document_scan_task_call_inventory')
            if any((directory.parent/n/'issued-request.json').exists() for n in expected[len(calls)+1:]):
                raise ValueError('document_scan_attempt_prefix')
            break
        raw = attempt_path.read_bytes()
        data = json.loads(raw)
        issued = shared.REQUEST.validate_json(raw, strict=True)
        issued = replace(issued, **{k:data[k] for k in ('temperature','timeout_s','top_p')})
        role(issued)
        if base.validate_request(issued, transport_id=base.REVIEW_MODEL_TRANSPORT_ID) != raw:
            raise ValueError('document_scan_attempt_request_changed')
        if not rows:
            if len(calls) != len([n for n in expected if (directory.parent/n/'issued-request.json').exists()])-1:
                raise ValueError('document_scan_missing_receipt_not_tail')
            # Explicitly unknown local attempt, NOT a fabricated call receipt.
            rows = [dict(binding=dict(ordinal=1, role='review', provider='zhipu', model='glm-5.3',
                request_sha256=base.sha(attempt_path)), request=issued, response=None,
                completed=False, usage=None, receipt_missing=True,
                artifact_sha256={'local_pre_transport_attempt_only':base.sha(attempt_path)})]
        if len(rows) != 1 or rows[0]['binding']['request_sha256'] != base.sha(attempt_path):
            raise ValueError('document_scan_task_call_inventory')
        # Per-case exact route additionally prevents another control's valid
        # request from being moved into this task's receipt directory.
        prepared = controls()[1][len(calls)][2]
        issued = rows[0]['request']
        metadata = dict(issued.metadata)
        metadata.pop('coach_budget_contract', None)
        if replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared:
            raise ValueError('document_scan_transport_case_changed')
        calls.extend(rows)
    return calls


def run(args):
    plan = prepare(root_thread_id=args.root_thread_id, independent_thread_id=args.independent_thread_id)
    if not args.execute:
        if args.output:
            base.write_new_json(args.output, plan)
        return dict(plan_sha256=base.canonical_sha(plan), budget=plan['budget'], provider_calls=0)
    return base.execute_plan(args, plan, observer=observe)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-thread-id', required=True)
    parser.add_argument('--independent-thread-id', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--codex-executable', type=Path)
    result = run(parser.parse_args())
    print(base.compact(result), flush=True)
    if 'scan_completed' in result and not result['scan_completed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
