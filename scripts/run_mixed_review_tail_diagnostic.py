"""Proposed mixed-error tail observation; explicit exception approval required.

The rejected historical initial opinion is never certified, repaired or counted
as new IO. Current editor and full fresh review run unchanged. This experiment
does not amend ADR0111 or grant original15/product qualification.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from pydantic import ValidationError

from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_integrated_runtime import Exchange
from app.harness.steps import RevisionRequest
from scripts import run_coarse_edit_diagnostic as base
from scripts import prepare_scope_resolution_probe as source_seal
from scripts.run_scope_resolution_diagnostic import close_result

EXPERIMENT = 'mixed-review-tail-diagnostic-20261008'
EXCEPTION = 'diagnostic-only-mixed-false-and-true-initial-v1'
SOURCE_FILES = tuple(dict.fromkeys((*base.SOURCE_FILES,
    __file__, editor.__file__, source_seal.SEAL,
    'scripts/prepare_scope_resolution_probe.py',
    'scripts/mixed_review_tail_handoff.py',
    'scripts/run_scope_resolution_diagnostic.py',
    'app/evaluation/review_bound_qualification.py',
    'app/runtime/receipted_provider_factory.py', 'app/providers/zhipu_profiles.py',
    'app/harness/steps.py', 'app/evaluation/golden_integrated_runtime.py',
    'app/evaluation/role_qualification.py', 'app/evaluation/golden_stream_bridge.py',
    'scripts/run_boundary_examples_v2.py', 'scripts/run_role_coach_development.py',
    'scripts/run_golden_inference_development.py', 'scripts/diagnose_block_review_route.py')))


def prepared_source():
    seal = base.ROOT/source_seal.SEAL
    if base.sha(seal) != source_seal.SEAL_SHA:
        raise ValueError('mixed_tail_seal_changed')
    saved = json.loads(seal.read_bytes())
    public = saved['public_json_contents']
    source = next(s for row, s in base.frozen_cases()[0] if row['key'] == 'claim-scope:3')
    inputs = editor.Current.build_inputs(source)
    archived = public['claim-scope-3/source.json']
    if source.report != archived['report'] or inputs.data_json != archived['input_json']:
        raise ValueError('mixed_tail_source_changed')
    initial = editor.Current.make_request(inputs)
    initial_sha = hashlib.sha256(base.validate_request(initial,
        transport_id=base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest()
    if initial_sha != saved['original_file_sha256']['claim-scope-3-prepared-request.json']:
        raise ValueError('mixed_tail_initial_request_changed')
    # Reconstruct the exact archived issued bytes, not an Exchange that binds
    # the historical response to today's unbudgeted prepared-request hash.
    issued = replace(initial, metadata={**initial.metadata,
        'coach_budget_contract': 'coach-bounded-review-v2'})
    issued_bytes = base.validate_request(issued, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)
    issued_sha = hashlib.sha256(issued_bytes).hexdigest()
    transport = 'transport/claim-scope-3/review/'
    if (json.loads(issued_bytes) != public[transport+'request-001.json']
            or issued_sha != saved['original_file_sha256'][transport+'request-001.json']
            or issued_sha != public[transport+'stream-001/reservation.json']['request_sha256']):
        raise ValueError('mixed_tail_historical_transport_changed')
    raw = public['claim-scope-3/initial-journal.json']['raw']
    response = base.RESPONSE.validate_json(base.compact(public[
        'transport/claim-scope-3/review/response-001.json']), strict=True)
    if (len(response.tool_calls) != 1 or dict(response.tool_calls[0].arguments) != json.loads(raw)
            or response.model != 'glm-5.3'):
        raise ValueError('mixed_tail_initial_response_changed')
    _, accepted, journal = editor.Current.validate_review(raw, inputs)
    if journal != public['claim-scope-3/initial-journal.json']:
        raise ValueError('mixed_tail_initial_journal_changed')
    if accepted.verdict != 'needs_revision' or [i.block for i in accepted.issues] != [4, 6]:
        raise ValueError('mixed_tail_initial_findings_changed')
    return source, inputs, Exchange(issued, response, issued_sha), initial, initial_sha, editor.edit_request(inputs, accepted)


def prepare(*, root_thread_id, independent_thread_id):
    source, inputs, historical, initial, initial_sha, edit = prepared_source()
    prices = [base.CONTRACT.pricing_profiles['zhipu', m] for m in ('glm-5.3-flash', 'glm-5.3')]
    cost = sum((Decimal(64000)*p.input_cost_per_million + Decimal(32768)*p.output_cost_per_million)
               / Decimal(1_000_000) for p in prices)
    plan = dict(experiment=EXPERIMENT, required_exception=EXCEPTION,
        execution_authorized=False, initial_review_accepted=False,
        historical_initial_inputs=1, historical_initial_is_new_call=False,
        labels_sent_to_model=False, original15_qualified=False, product_admitted=False,
        source_seal=source_seal.SEAL, source_seal_sha256=source_seal.SEAL_SHA,
        report_sha256=base.digest(source.report), input_sha256=base.digest(inputs.data_json),
        initial_request_sha256=initial_sha,
        historical_issued_request_sha256=historical.receipt_request_sha256,
        initial_public_response_sha256=base.digest(base.RESPONSE.dump_json(historical.response).decode()),
        edit_request_sha256=hashlib.sha256(base.validate_request(edit,
            transport_id=base.CAPACITY_TRANSPORT_ID)).hexdigest(),
        edit_input_ceiling=base.size(edit),
        sequence=['necessary-edit', 'conditional-fresh'],
        source_sha256={Path(p).resolve().relative_to(base.ROOT).as_posix() if Path(p).is_absolute() else p:
            base.digest((Path(p) if Path(p).is_absolute() else base.ROOT/p).read_text(encoding='utf-8'))
            for p in SOURCE_FILES},
        host_review_submission_mode=base.MODE_V2, host_review_evidence_policy=base.FINAL_POLICY,
        max_host_seconds=86400,
        budget=dict(max_calls=2, max_tokens=193536, max_active_seconds=600,
            per_request_output=32768, per_request_seconds=300,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        role_calls={'glm-5.3-flash': 1, 'glm-5.3': 1}, sdk_retries=0,
        acceptance='Both real source reviewers accept the exact edited report and full fresh review. '
            'Preserve correct block4; repair true block6 pooled-CS error; no other unsupported change. '
            'Fresh pass >=85 without false or missed findings. Labels never enter model requests.',
        stop_rule='First rejected edit/fresh, protocol, source, identity, transport or budget failure stops. '
            'No retries, reassessment, rewriting the initial opinion or leftover-budget transfer.',
        success_scope='One historical-opinion-conditioned task-outcome observation only. '
            'Initial reviewer quality remains failed; original15 remains2/15. No natural five-call or production qualification.',
        success_decision='Consider a separately approved task-outcome evaluation design; never silently replace initial-review gates.',
        failure_decision='Reject sufficiency of this unchanged editor/fresh tail on the exact failure; '
            'do not retry with synonyms or change the original report to obtain a pass.')
    return base.freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id)


def observe(factory, directory, plan, *, event_source, adjudicate=base.wait_reviews,
            before_send=lambda: None):
    base.require_execution_event_source(plan, event_source)
    source, inputs, historical, initial, initial_sha, edit = prepared_source()
    if (plan['required_exception'] != EXCEPTION or plan['initial_review_accepted'] is not False
            or plan['sequence'] != ['necessary-edit', 'conditional-fresh']
            or plan['edit_request_sha256'] != hashlib.sha256(base.validate_request(
                edit, transport_id=base.CAPACITY_TRANSPORT_ID)).hexdigest()):
        raise ValueError('mixed_tail_plan_changed')
    clock = base.DevelopmentHostClock(directory, max_host_seconds=plan['max_host_seconds'])
    router = factory('diagnostic')
    budget = base._ReceiptForwardingCoachBudgetedProvider(router, coach_contract=base.CONTRACT, clock=clock)
    sender = base.SharedBudgetReviewSender(budget)
    ledger, exchanges = [], {}
    injected = False
    result = dict(experiment=EXPERIMENT, diagnostic_accepted=False, initial_review_accepted=False,
        offline_initial_injections=0, product_admitted=False, original15_qualified=False)

    def send(request):
        nonlocal injected
        if not injected:
            if request != initial:
                raise ValueError('mixed_tail_initial_injection_changed')
            injected = True
            result['offline_initial_injections'] = 1
            return historical
        expected = edit if budget.calls == 0 else editor.Current.make_request(flow._expected_recheck)
        if request != expected or request.metadata['review_phase'] == 'native_business_reassessment':
            raise ValueError('mixed_tail_request_changed')
        clock.before_send()
        before_send()
        remaining = plan['budget']['max_active_seconds'] - clock()
        if (remaining <= 0 or budget.calls >= plan['budget']['max_calls']
                or budget.tokens + budget.reserved_tokens + base.size(request) + request.max_tokens > plan['budget']['max_tokens']):
            raise ValueError('mixed_tail_budget')
        return sender(replace(request, timeout_s=min(request.timeout_s, remaining)))

    def record(phase, exchange):
        if phase == 'native_business_review' and budget.calls == 0:
            return  # Historical input has no new transport or usage.
        name = 'necessary-edit' if phase == 'native_business_revision' else 'conditional-fresh'
        arm = Path(directory)/name
        arm.mkdir(exist_ok=False)
        transport = base.CAPACITY_TRANSPORT_ID if name == 'necessary-edit' else base.REVIEW_MODEL_TRANSPORT_ID
        base.write_new_json(arm/'request.json', json.loads(base.validate_request(exchange.issued_request, transport_id=transport)))
        base.write_new_json(arm/'response.json', base.public_response(json.loads(base.RESPONSE.dump_json(exchange.response))))
        exchanges[name] = exchange

    def inspect(name, stage_name, report, journal):
        arm = Path(directory)/name
        stage = dict(stage=stage_name, report=report, journal=journal)
        base.write_new_json(arm/'stage.json', stage)
        bound = dict(plan_sha256=base.canonical_sha(plan), key='claim-scope:3', stage=stage_name,
            response_sha256=base.sha(arm/'response.json'), report_sha256=base.digest(report),
            request_sha256=exchanges[name].receipt_request_sha256)
        base.write_new_json(arm/'review-required.json', dict(binding=bound,
            stage_sha256=base.stage_identity(stage), scope=plan['acceptance']))
        submission = clock.adjudicate(arm/'review-required.json',
            plan['budget']['max_active_seconds']-clock(), adjudicate)
        base.write_new_json(arm/'host-reviews.json', submission)
        accepted = base.validate_reviews(submission, stage, bound, plan, event_source)
        ledger.append(dict(name=name, binding=bound, host_accepted=accepted))
        if not accepted:
            raise ValueError('mixed_tail_host_rejected')
        if clock() >= plan['budget']['max_active_seconds']:
            raise ValueError('mixed_tail_budget')
        before_send()

    flow = editor.ReviewBoundRevisionWorkflow(send, record=record)
    try:
        base.write_new_json(Path(directory)/'source.json', dict(report=source.report, input_json=inputs.data_json))
        first = flow.evaluate(source)
        base.write_new_json(Path(directory)/'injected-initial-journal.json', dict(flow.last_journal,
            fixture_only=True, initial_review_accepted=False, new_provider_call=False))
        draft = flow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
            source.knowledge, source.report, first))
        inspect('necessary-edit', 'revision', draft.report, flow.last_edit_journal)
        final = flow.evaluate(replace(source, report=draft.report))
        # Preserve the valid final response/journal even if it rejects the report.
        base.write_new_json(Path(directory)/'final-journal.json', flow.last_journal)
        if final.verdict.value != 'pass' or final.score < 85:
            raise ValueError('mixed_tail_fresh_not_pass')
        inspect('conditional-fresh', 'final', draft.report, flow.last_journal)
        result['diagnostic_accepted'] = True
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(error, ValidationError):
            code = 'mixed_tail_schema_validation'
            result['validation_errors'] = error.errors(include_input=False, include_context=False, include_url=False)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,100}', code):
            result['error_code'] = code
    finally:
        result.update(stages=ledger, calls=budget.calls, known_tokens=budget.tokens,
            unknown_reserved_tokens=budget.reserved_tokens, attempts=router.attempts, timing=clock.summary())
        close_result(directory, result)
    return result


def run(args):
    # A plan/CI approval alone is not approval to change the diagnostic stop boundary.
    if args.execute and not getattr(args, 'allow_mixed_initial_diagnostic', False):
        raise ValueError('mixed_tail_explicit_exception_approval_required')
    plan = prepare(root_thread_id=args.root_thread_id, independent_thread_id=args.independent_thread_id)
    if not args.execute:
        if args.output:
            base.write_new_json(args.output, plan)
        return dict(plan_sha256=base.canonical_sha(plan), budget=plan['budget'], provider_calls=0)
    return base.execute_plan(args, plan, observer=observe)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root-thread-id', required=True)
    parser.add_argument('--independent-thread-id', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--allow-mixed-initial-diagnostic', action='store_true')
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--codex-executable', type=Path)
    result = run(parser.parse_args())
    print(base.compact(result), flush=True)
    if 'diagnostic_accepted' in result and not result['diagnostic_accepted']:
        raise SystemExit(1)
