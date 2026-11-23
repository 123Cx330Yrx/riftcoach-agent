"""Six isolated accepted-opinion edit/fresh diagnostics, never qualification.

Historical inputs are sealed, accepted whole-source initial opinions. A semantic
rejection ends that case, while all protocol/source/identity/transport failures
stop the batch. Every new completed stage receives a real native dual review.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from pydantic import ValidationError
from app.evaluation import document_review_qualification as backend
from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_integrated_runtime import Exchange
from app.harness.steps import RevisionRequest
from scripts import run_coarse_edit_diagnostic as base
from scripts import run_document_review_scan as scan
from scripts.run_scope_resolution_diagnostic import close_result

EXPERIMENT = 'document-accepted-tails-20261009'
SEAL = 'data/evaluation/results/golden_document_remaining11_scan_result_20261009.json'
SEAL_SHA = '8adfa5cea9b56c063ffb0340b726c55d4c3effbfe86c54738d492f48b00c6baa'
HISTORICAL_RUN = base.ROOT/'data/runs/model_comparison'/scan.EXPERIMENT
KEYS = ('scope:4', 'claim-scope:6', 'observed:2', 'observed:3', 'observed:4', 'observed:5')
STAGES = ('revision', 'final')
SOURCE_FILES = tuple(dict.fromkeys((*scan.SOURCE_FILES, *backend.SOURCE_FILES,
    'scripts/run_document_accepted_tails.py', 'scripts/document_accepted_tail_handoff.py',
    'scripts/document_review_host_task.py', 'scripts/seal_document_accepted_tails.py',
    'scripts/run_coarse_edit_diagnostic.py', 'scripts/run_scope_resolution_diagnostic.py',
    'scripts/review_independence_contract.py', 'scripts/codex_review_event_source.py',
    'scripts/role_development_host_clock.py', 'scripts/role_host_identity.py')))


def controls():
    """Bind accepted historical inputs to their exact raw receipts and sources."""
    if base.sha(base.ROOT/SEAL) != SEAL_SHA:
        raise ValueError('accepted_tail_seal_changed')
    seal = json.loads((base.ROOT/SEAL).read_bytes())
    def original(rel):
        raw = (HISTORICAL_RUN/rel).read_bytes()
        if hashlib.sha256(raw).hexdigest() != seal['original_file_sha256'][rel]:
            raise ValueError('accepted_tail_historical_original_changed')
        if rel in seal['public_json_contents'] and json.loads(raw) != seal['public_json_contents'][rel]:
            raise ValueError('accepted_tail_historical_public_changed')
        return raw
    saved = json.loads(original('plan.json'))
    plan = saved['preparation_plan']
    if (plan != scan.prepare(root_thread_id=plan['root_thread_id'],
            independent_thread_id=plan['review_principals']['independent']['principal_id'])
            or saved['plan_sha256'] != base.canonical_sha(plan)):
        raise ValueError('accepted_tail_historical_plan_changed')
    original('result.json')
    variants = {c['key']:(c, inputs, request) for c,inputs,request in scan.controls()[1]}
    sources = {c['key']: source for c,source in backend.frozen_cases()[0]}
    result = []
    for key in KEYS:
        cell, inputs, initial = variants[key]
        arm = scan.arm_name(key)
        recorded = next(r for r in seal['stages'] if r['key'] == key)
        if (cell['expected_initial'] != 'reject' or not recorded['semantic_accepted']
                or not recorded['primary_accepted'] or not recorded['independent_accepted']):
            raise ValueError('accepted_tail_initial_not_accepted')
        calls = backend.read_calls(HISTORICAL_RUN/'transport'/arm)
        if len(calls) != 1 or not calls[0]['completed']:
            raise ValueError('accepted_tail_historical_receipt_inventory')
        call = calls[0]
        metadata = dict(call['request'].metadata)
        if (metadata.pop('coach_budget_contract',None) != 'coach-bounded-review-v2'
                or not 0 < call['request'].timeout_s <= initial.timeout_s
                or replace(call['request'],timeout_s=initial.timeout_s,metadata=metadata) != initial):
            raise ValueError('accepted_tail_historical_request_changed')
        stage = json.loads(original(arm+'/stage.json'))
        bound = dict(plan_sha256=saved['plan_sha256'],key=key,stage='initial',
            response_sha256=base.sha(HISTORICAL_RUN/arm/'response.json'),
            report_sha256=base.digest(inputs.source.report),request_sha256=call['binding']['request_sha256'])
        required = json.loads(original(arm+'/review-required.json'))
        if required['binding'] != bound or required['stage_sha256'] != base.stage_identity(stage):
            raise ValueError('accepted_tail_historical_required_changed')
        # Whole sealed export binds native original digests. Require its formal
        # native-backed accepted submission, not a new locally authored opinion.
        submission = json.loads(original(arm+'/review-submission.json'))
        if json.loads(original(arm+'/host-reviews.json')) != submission:
            raise ValueError('accepted_tail_historical_submission_changed')
        for role in ('primary', 'independent'):
            review = submission[role]
            if (review['binding'] != bound or not review['stage_assessment']['accepted']
                    or review['stage_assessment']['defects'] or review['report_assessment'] is not None):
                raise ValueError('accepted_tail_historical_review_changed')
        event = submission['independent']['independent_source_event']
        if (event['binding'] != bound or event['state'] != 'completed'
                or event['host_review_evidence_policy'] != base.FINAL_POLICY
                or event['author_principal_id'] != plan['review_principals']['independent']['principal_id']):
            raise ValueError('accepted_tail_historical_native_changed')
        raw = original(arm+'/issued-request.json')
        if hashlib.sha256(raw).hexdigest() != call['binding']['request_sha256']:
            raise ValueError('accepted_tail_historical_request_changed')
        if json.loads(original(arm+'/source.json')) != dict(input_json=inputs.data_json,
                report=inputs.source.report,synthetic_report=False):
            raise ValueError('accepted_tail_historical_source_changed')
        if (json.loads(original(arm+'/response.json')) != base.public_response(json.loads(base.RESPONSE.dump_json(call['response'])))
                or json.loads(original(arm+'/request.json')) != json.loads(raw)):
            raise ValueError('accepted_tail_historical_public_receipt_changed')
        historical = Exchange(call['request'], call['response'], bound['request_sha256'])
        _, wire, journal = backend.Workflow.validate_review(base.tool_result(initial, historical), inputs)
        if (wire.verdict != 'needs_revision' or stage != dict(stage='initial',report=inputs.source.report,journal=journal)
                or scan.classify(cell, wire, submission, bound) != recorded):
            raise ValueError('accepted_tail_historical_semantics_changed')
        edit = editor.edit_request(inputs, wire)
        row = dict(key=key, input_sha256=base.digest(inputs.data_json),
            report_sha256=base.digest(sources[key].report),
            historical_binding=bound, historical_raw_request_sha256=hashlib.sha256(raw).hexdigest(),
            historical_raw_policy_sha256=base.digest(json.loads(raw)['messages'][0]['content']),
            historical_journal_sha256=base.canonical_sha(journal),
            edit_request_sha256=hashlib.sha256(base.validate_request(edit,
                transport_id=base.CAPACITY_TRANSPORT_ID)).hexdigest(), edit_input_ceiling=base.size(edit))
        result.append((row, sources[key], inputs, initial, historical, edit))
    return result


def prepare(*, root_thread_id, independent_thread_id):
    roles = {'glm-5.3-flash':6, 'glm-5.3':6}
    prices = backend.CONTRACT.pricing_profiles
    cost = sum(count*(Decimal(64000)*prices['zhipu',model].input_cost_per_million
        + Decimal(32768)*prices['zhipu',model].output_cost_per_million)/1_000_000
        for model,count in roles.items())
    plan = dict(experiment=EXPERIMENT, cells=[r for r,*_ in controls()], sequence=list(KEYS),
        historical_seal=SEAL, historical_seal_sha256=SEAL_SHA,
        historical_initial_inputs=6, historical_inputs_are_new_calls=False,
        identity=backend.candidate_identity(),
        source_sha256={p:base.digest((base.ROOT/p).read_text(encoding='utf-8')) for p in SOURCE_FILES},
        host_review_submission_mode=base.MODE_V2, host_review_evidence_policy=base.FINAL_POLICY,
        host_task_delivery='document-host-policy-delivery-v1', max_host_seconds=86400,
        budget=dict(max_calls=12, max_tokens=1161216, max_active_seconds=3600,
            per_request_output=32768, per_request_seconds=300, estimated_uncached_cny=str(cost),
            hard_billing_cap=False), role_calls=roles, sdk_retries=0,
        execution_authorized=False, labels_sent_to_model=False,
        product_admitted=False, original15_qualified=False, review_controls_qualified=False,
        stop_rule='A valid whole-source edit/fresh semantic rejection stops only its case. '
            'Any identity/source/native/protocol/transport/budget/availability failure stops the batch. '
            'No retry, reassessment, restart or rejected initial input.',
        acceptance='Both real full-source reviewers accept every changed and retained statement, '
            'editor reason, citation and fresh opinion. All four report flags true when accepted. '
            'Fresh pass with score>=85 and no material false or missed finding.',
        success_scope='Six historical-accepted-opinion-conditioned tails only, not a natural full '
            'task or same-batch original15. Disputed attribution:1 and scope:3 remain unresolved.',
        result_decision='Expose remaining edit/fresh failures together; select common repairs before '
            'same-version original15. Passing these tails alone cannot trigger full15.')
    return base.freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id)


class Limits:
    grounded = True
    def __init__(self, budget):
        self.budget = budget
    def descriptor(self):
        return dict(backend.CONTRACT.descriptor(), max_calls=self.budget['max_calls'],
            total_tokens=self.budget['max_tokens'], execution_timeout_s=self.budget['max_active_seconds'])
    def request_identity(self, request):
        return backend.CONTRACT.request_identity(request)


def observe(factory, directory, plan, *, event_source, adjudicate=base.wait_reviews,
            before_send=lambda:None):
    base.require_execution_event_source(plan, event_source)
    variants = controls()
    if plan['cells'] != [r for r,*_ in variants] or plan['sequence'] != list(KEYS):
        raise ValueError('accepted_tail_controls_changed')
    directory = Path(directory)
    clock = base.DevelopmentHostClock(directory, max_host_seconds=plan['max_host_seconds'])
    budget = routers = None
    routers = []
    result = dict(experiment=EXPERIMENT, scan_completed=False, diagnostic_accepted=False,
        cases=[], historical_initial_inputs=0, product_admitted=False, original15_qualified=False,
        review_controls_qualified=False)
    try:
        for row,source,inputs,initial,historical,edit in variants:
            key = row['key']
            arm = directory/key.replace(':','-')
            arm.mkdir(exist_ok=False)
            base.write_new_json(arm/'source.json', dict(input_json=inputs.data_json, report=source.report))
            router = factory(key.replace(':','-'))
            routers.append((key,router))
            if budget is None:
                budget = base._ReceiptForwardingCoachBudgetedProvider(router, coach_contract=backend.CONTRACT, clock=clock)
                budget.contract = Limits(plan['budget'])
            else:
                budget.provider = router
            sender = base.SharedBudgetReviewSender(budget)
            outcome = dict(key=key, stages=[], semantic_accepted=False)
            result['cases'].append(outcome)
            injected = False
            def send(request):
                nonlocal injected
                if not injected:
                    if request != initial:
                        raise ValueError('accepted_tail_injection_changed')
                    injected = True
                    result['historical_initial_inputs'] += 1
                    return historical
                expected = edit if flow.evaluations == 1 else flow.make_request(flow._expected_recheck)
                if request != expected or request.metadata['review_phase'] == 'native_business_reassessment':
                    raise ValueError('accepted_tail_request_changed')
                clock.before_send()
                before_send()
                remaining = plan['budget']['max_active_seconds']-clock()
                if (remaining <= 0 or budget.calls >= plan['budget']['max_calls']
                        or budget.tokens+budget.reserved_tokens+base.size(request)+request.max_tokens > plan['budget']['max_tokens']):
                    raise ValueError('accepted_tail_budget')
                stage = 'revision' if flow.evaluations == 1 else 'final'
                folder = arm/stage
                folder.mkdir(exist_ok=False)
                issued = replace(request, timeout_s=min(request.timeout_s,remaining),
                    metadata={**request.metadata,'coach_budget_contract':'coach-bounded-review-v2'})
                raw = base.validate_request(issued, transport_id=base.CAPACITY_TRANSPORT_ID
                    if stage == 'revision' else base.REVIEW_MODEL_TRANSPORT_ID)
                (folder/'issued-request.json').write_bytes(raw)
                return sender(replace(request, timeout_s=min(request.timeout_s,remaining)))
            def record(phase, exchange):
                if phase == 'native_business_review' and flow.evaluations == 1:
                    return
                stage = 'revision' if phase == 'native_business_revision' else 'final'
                folder = arm/stage
                base.write_new_json(folder/'response.json', base.public_response(json.loads(base.RESPONSE.dump_json(exchange.response))))
                if base.sha(folder/'issued-request.json') != exchange.receipt_request_sha256:
                    raise ValueError('accepted_tail_issued_request_changed')
            def inspect(stage, report, journal):
                folder = arm/stage
                value = dict(stage=stage, report=report, journal=journal)
                base.write_new_json(folder/'stage.json', value)
                bound = dict(plan_sha256=base.canonical_sha(plan),key=key,stage=stage,
                    response_sha256=base.sha(folder/'response.json'),report_sha256=base.digest(report),
                    request_sha256=base.sha(folder/'issued-request.json'))
                base.write_new_json(folder/'review-required.json', dict(binding=bound,
                    stage_sha256=base.stage_identity(value),scope=plan['acceptance']))
                submission = clock.adjudicate(folder/'review-required.json',
                    plan['budget']['max_active_seconds']-clock(), adjudicate)
                base.write_new_json(folder/'host-reviews.json',submission)
                accepted = base.validate_reviews(submission,value,bound,plan,event_source)
                outcome['stages'].append(dict(stage=stage,binding=bound,host_accepted=accepted))
                if clock() >= plan['budget']['max_active_seconds']:
                    raise ValueError('accepted_tail_budget')
                before_send()
                return accepted
            flow = backend.Workflow(send,record=record)
            first = flow.evaluate(source)
            base.write_new_json(arm/'historical-initial-journal.json',dict(flow.last_journal,
                historical_input=True,initial_review_accepted=True,new_provider_call=False))
            draft = flow.revise(RevisionRequest(source.player_summary,source.deterministic_report,
                source.knowledge,source.report,first))
            if not inspect('revision',draft.report,flow.last_edit_journal):
                outcome['semantic_failure'] = 'revision_host_rejected'
            else:
                final = flow.evaluate(replace(source,report=draft.report))
                accepted = inspect('final',draft.report,flow.last_journal)
                outcome.update(final_verdict=final.verdict.value,final_score=final.score)
                if not accepted:
                    outcome['semantic_failure'] = 'fresh_host_rejected'
                elif final.verdict.value != 'pass' or final.score < 85:
                    outcome['semantic_failure'] = 'fresh_not_pass'
                else:
                    outcome['semantic_accepted'] = True
            # A per-case terminal receipt also prevents late stage submissions.
            base.write_new_json(arm/'case-result.json',outcome)
        result['scan_completed'] = True
        result['diagnostic_accepted'] = all(c['semantic_accepted'] for c in result['cases'])
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error,'code',None) or (str(error) if isinstance(error,ValueError) else None)
        if isinstance(error,ValidationError):
            code = 'accepted_tail_schema_validation'
        if isinstance(code,str) and re.fullmatch('[a-z_]{1,100}',code):
            result['error_code'] = code
    finally:
        result.update(calls=budget.calls if budget else 0,known_tokens=budget.tokens if budget else 0,
            unknown_reserved_tokens=budget.reserved_tokens if budget else 0,
            attempts=[dict(a,key=k,transport_ordinal=a['ordinal']) for k,r in routers for a in r.attempts],
            timing=clock.summary(),unexecuted_keys=[k for k in KEYS if k not in [c['key'] for c in result['cases']]])
        close_result(directory,result)
    return result


def execute(args, plan):
    directory = base.ROOT/'data/runs/model_comparison'/EXPERIMENT
    if directory.exists():
        raise ValueError('accepted_tail_closed_or_exists')
    if (not args.preparation or not args.env_file or not args.codex_executable
            or args.plan_sha != base.canonical_sha(plan) or plan != json.loads(args.preparation.read_bytes())):
        raise ValueError('accepted_tail_frozen_preparation_required')
    head = base.verify_public_ci(args.ci_run)
    base.require_unchanged_checkout(head)
    with base.CodexReadOnlyClient(args.codex_executable) as client:
        base.verify_native_principals(client,plan)
        event_source = base.CodexHostReviewEventSource(client,plan)
        base.require_execution_event_source(plan,event_source)
        generator,reviewer = base.load_role_settings(args.env_file)
        factory = backend.ProviderFactory(generator_settings=generator,reviewer_settings=reviewer,
            transport_root=directory/'transport')
        directory.mkdir(parents=True,exist_ok=False)
        base.write_new_json(directory/'plan.json',dict(preparation_plan=plan,plan_sha256=base.canonical_sha(plan),
            execution_head_sha=head,ci_run=args.ci_run))
        with base.route_environment('direct'):
            return observe(factory,directory,plan,event_source=event_source,
                before_send=lambda:base.require_unchanged_checkout(head))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-thread-id',required=True)
    parser.add_argument('--independent-thread-id',required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--execute',action='store_true')
    for name in ('preparation','env-file','codex-executable'):
        parser.add_argument('--'+name,type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    args = parser.parse_args()
    plan = prepare(root_thread_id=args.root_thread_id,independent_thread_id=args.independent_thread_id)
    if args.execute:
        result = execute(args,plan)
    else:
        if args.output:base.write_new_json(args.output,plan)
        result = dict(plan_sha256=base.canonical_sha(plan),budget=plan['budget'],provider_calls=0)
    print(base.compact(result),flush=True)
    if args.execute and not result['scan_completed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
