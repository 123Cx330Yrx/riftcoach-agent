"""Bounded original-set review/edit controls for the current role candidate.

Preview is offline. Execute requires the prepared hash, clean exact-HEAD CI,
and existing spending authorization. Host checks every completed business
stage before further IO. Two controls cannot admit the original fifteen or
the product. Raw receipts and run directories are create-only.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import time

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_notes import RoleNoteReviewWorkflow
from app.evaluation.golden_stream_bridge import RESPONSE, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import (
    ROOT, ASSETS, frozen_cases, prepare_qualification, read_role_calls, replay_case,
)
from app.harness.steps import EvaluationVerdict, RevisionRequest
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider
from scripts.run_golden_inference_development import verify_public_ci
from scripts.export_partitioned_review import public_response
from scripts.run_review_model_comparison import terminal_adjudication
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout, summarize_calls

EXPERIMENT = 'role-qualification-notes-pair-v1'
KEYS = ('attribution:1', 'claim-scope:1')
RUN_DIRECTORY = ROOT / 'data/runs/role_qualification' / EXPERIMENT


def prepare():
    # Load real assets/fingerprints, not merely the identity copied in a manifest.
    RuntimeCompositionRoot.from_directories(skills_root=ROOT / ASSETS / 'skills',
        prompt_programs_root=ROOT / ASSETS / 'prompt_programs', coach_contract=ROLE_COACH_CONTRACT)
    qualification, requests = prepare_qualification()
    rows = {row['key']: row for row in qualification['cases']}
    selected = [rows[key] for key in KEYS]
    limits = ROLE_COACH_CONTRACT.descriptor()
    if (limits['max_calls'], limits['total_tokens'], limits['execution_timeout_s'],
            limits['max_revisions'], limits['max_output_tokens'], limits['request_timeout_s']) != (
            5, 401920, 900, 1, 32768, 300):
        raise ValueError('role_pair_budget_changed')
    # Review-only controls permit at most 2 GLM calls; the edit case permits
    # 4 GLM + 1 Flash calls including both legal reassessments. Allocate the
    # shared token envelope to the most expensive categories first.
    prices = ROLE_COACH_CONTRACT.pricing_profiles
    glm, flash = [prices['zhipu', model] for model in ('glm-5.3', 'glm-5.3-flash')]
    cost, case_budgets = Decimal(0), []
    for row in selected:
        editing = row['expected_initial'] == 'reject'
        reviews, edits = (4, 1) if editing else (2, 0)
        cap = min(limits['total_tokens'], (reviews + edits) * (
            limits['max_input_tokens'] + limits['max_output_tokens']))
        remaining, subtotal = cap, Decimal(0)
        for count, rate in ((reviews * limits['max_output_tokens'], glm.output_cost_per_million),
                (reviews * limits['max_input_tokens'], glm.input_cost_per_million),
                (edits * limits['max_output_tokens'], flash.output_cost_per_million),
                (edits * limits['max_input_tokens'], flash.input_cost_per_million)):
            reserved = min(remaining, count)
            subtotal += Decimal(reserved) * rate / 1_000_000
            remaining -= reserved
        cost += subtotal
        case_budgets.append(dict(key=row['key'], max_calls=reviews + edits, max_tokens=cap,
            max_seconds=900 if editing else 600, estimated_uncached_cny=str(subtotal)))
    plan = dict(experiment=EXPERIMENT, qualification_version=qualification['qualification_version'],
        qualification_plan_sha256=digest(compact(qualification)), identity=qualification['identity'],
        cases=selected, per_case_budget=qualification['per_case_budget'], case_budgets=case_budgets,
        batch_budget=dict(max_calls=sum(b['max_calls'] for b in case_budgets),
            max_tokens=sum(b['max_tokens'] for b in case_budgets),
            max_seconds=sum(b['max_seconds'] for b in case_budgets),
            estimated_uncached_cny=str(cost), hard_billing_cap=False,
            price_snapshot='ADR0108/2026-09-22'),
        stop_rule='Stop at the first protocol, source, semantic or editing failure. No automatic new batch.',
        host_checks='All issues, notes, resolutions and changed/retained text; host time counts toward deadlines.',
        labels_sent_to_model=False, review_controls_qualified=False,
        actual_product_task_qualified=False, production_admitted=False)
    return plan, {key: requests[key] for key in KEYS}


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe(factory, directory, plan, *, adjudicate=terminal_adjudication,
            clock=time.monotonic, before_send=lambda: None):
    """Run frozen workflows, retaining per-stage host gates outside model input."""
    started = clock()
    sources = {f['key']: (f, source) for f, source in frozen_cases()[0]}
    outcomes = []
    result = dict(experiment=EXPERIMENT, pair_accepted=False, production_admitted=False,
        review_controls_qualified=False, actual_product_task_qualified=False)
    try:
        for row, budget in zip(plan['cases'], plan['case_budgets'], strict=True):
            key = row['key']
            case_id = key.replace(':', '-')
            arm = directory / case_id
            arm.mkdir(exist_ok=False)
            frozen, source = sources[key]
            outcome = dict(key=key, status='failed', stages=[])
            outcomes.append(outcome)
            write_new_json(arm / 'source.json', dict(input_json=RoleNoteReviewWorkflow.build_inputs(source).data_json,
                report=source.report, input_sha256=frozen['input_sha256'], report_sha256=frozen['report_sha256']))
            case_started = clock()
            provider = factory(case_id)
            wrapped = _ReceiptForwardingCoachBudgetedProvider(provider, clock=clock, coach_contract=ROLE_COACH_CONTRACT)
            sender = SharedBudgetReviewSender(wrapped)
            journals = []
            current_report = source.report

            def remaining():
                return min(budget['max_seconds'] - (clock() - case_started),
                    plan['batch_budget']['max_seconds'] - (clock() - started))

            def send(request):
                if remaining() <= 0 or wrapped.calls >= budget['max_calls']:
                    raise ValueError('role_pair_execution_limit')
                if wrapped.calls == 0 and hashlib.sha256(validate_request(
                        request, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest() != row['request_sha256']:
                    raise ValueError('role_pair_first_request_changed')
                if request.metadata.get('review_phase') == 'native_business_reassessment':
                    # A recovery is a new business judgment. Inspect the full
                    # bad response before paying for it, never strip its fields.
                    inspect(f'reassessment-before-{wrapped.calls + 1}', current_report,
                        dict(previous_response=public_response(json.loads(RESPONSE.dump_json(
                            provider.last_exchange.response))),
                            recovery_input=request.messages[1].content))
                before_send()
                return sender(replace(request, timeout_s=min(request.timeout_s, remaining())))

            workflow = RoleNoteReviewWorkflow(send)

            def inspect(stage, report, journal=None):
                path = arm / (stage + '.json')
                write_new_json(path, dict(stage=stage, key=key, report=report,
                    report_sha256=digest(report), journal=journal))
                outcome['stages'].append(stage)
                if remaining() <= 0:
                    raise ValueError('role_pair_execution_limit')
                decision = adjudicate(path, remaining())
                if (type(decision.get('accepted')) is not bool
                        or decision.get('response_sha256') != _hash(path)):
                    raise ValueError('role_pair_host_binding_invalid')
                write_new_json(arm / (stage + '-host.json'), decision)
                if not decision['accepted']:
                    raise ValueError('role_pair_host_rejected')
                if remaining() <= 0:
                    raise ValueError('role_pair_execution_limit')

            initial = workflow.evaluate(source)
            journals.append(workflow.last_journal)
            outcome.update(initial_verdict=initial.verdict.value, initial_score=initial.score)
            expected = EvaluationVerdict.PASS if frozen['expected_initial'] == 'accept' else EvaluationVerdict.NEEDS_REVISION
            # Preserve a valid but wrong judgment even when no host gate is needed.
            write_new_json(arm / 'initial-journal.json', workflow.last_journal)
            if initial.verdict is not expected or (initial.verdict is EvaluationVerdict.PASS
                    and initial.score < ROLE_COACH_CONTRACT.descriptor()['minimum_score']):
                raise ValueError('role_pair_initial_semantics_failed')
            inspect('initial', source.report, workflow.last_journal)
            final_report = source.report
            if initial.verdict is EvaluationVerdict.NEEDS_REVISION:
                draft = workflow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
                    source.knowledge, source.report, initial))
                final_report = draft.report
                current_report = final_report
                inspect('revision', final_report)
                final = workflow.evaluate(replace(source, report=final_report))
                journals.append(workflow.last_journal)
                outcome.update(final_verdict=final.verdict.value, final_score=final.score)
                write_new_json(arm / 'final-journal.json', workflow.last_journal)
                if (final.verdict is not EvaluationVerdict.PASS
                        or final.score < ROLE_COACH_CONTRACT.descriptor()['minimum_score']):
                    raise ValueError('role_pair_final_review_failed')
                inspect('final', final_report, workflow.last_journal)
            calls = read_role_calls(directory / 'transport' / case_id)
            if (not calls or len(calls) > budget['max_calls']
                    or not all(call['completed'] for call in calls)):
                raise ValueError('role_pair_incomplete_receipts')
            if sum(call['usage']['input_tokens'] + call['usage']['output_tokens']
                    for call in calls) > budget['max_tokens']:
                raise ValueError('role_pair_execution_limit')
            replayed = replay_case(frozen, source, calls)
            if (replayed['final_report_sha256'] != digest(final_report)
                    or replayed['journals_sha256'] != [digest(compact(j)) for j in journals]):
                raise ValueError('role_pair_replay_mismatch')
            host_path = arm / 'host-review.json'
            write_new_json(host_path, dict(candidate_sha256=digest(compact(plan['identity'])),
                input_sha256=frozen['input_sha256'], initial_request_sha256=calls[0]['binding']['request_sha256'],
                **replayed, semantic_acceptance=True, reviewer='Codex host full-context stage review',
                source_review='Every completed stage was explicitly checked against full sources and report; see stage host receipts.'))
            outcome.update(status='host_accepted', final_report_sha256=digest(final_report),
                qualification_row={**row, 'status': 'host_accepted',
                    'transport_directory': f'transport/{case_id}',
                    'host_review_file': f'{case_id}/host-review.json', 'host_review_sha256': _hash(host_path)})
        result['pair_accepted'] = True
    except BaseException as error:
        result.update(error_type=type(error).__name__)
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,100}', code):
            result['error_code'] = code
    finally:
        # Receipts, including unknown usage, are the accounting authority.
        for outcome in outcomes:
            try:
                outcome['accounting'] = summarize_calls(directory / 'transport' / outcome['key'].replace(':', '-'))
            except (ValueError, OSError, KeyError, TypeError):
                outcome['accounting'] = dict(accounting_status='invalid_receipts', reserved_calls=None,
                    completed_calls=None, unknown_usage_calls=None, total_estimated_uncached_cny=None)
                result['pair_accepted'] = False
        result.update(cases=outcomes, elapsed_seconds=round(clock() - started, 3))
        write_new_json(directory / 'result.json', result)
    return result


def run(args):
    plan, requests = prepare()
    plan_sha = digest(compact(plan))
    if not args.execute:
        summary = dict(preparation_plan_sha256=plan_sha, plan=plan, provider_requests=0)
        print(compact(summary), flush=True)
        return summary
    if not args.env_file or not args.ci_run or args.approval_plan_sha != plan_sha:
        raise ValueError('role_pair_preparation_required')
    if RUN_DIRECTORY.exists():
        raise ValueError('role_pair_batch_exists')
    head = verify_public_ci(args.ci_run)
    RUN_DIRECTORY.mkdir(parents=True, exist_ok=False)
    write_new_json(RUN_DIRECTORY / 'plan.json', dict(preparation_plan=plan,
        preparation_plan_sha256=plan_sha, head_sha=head, ci_run=args.ci_run))
    for key, raw in requests.items():
        (RUN_DIRECTORY / (key.replace(':', '-') + '-prepared-request.json')).write_bytes(raw)
    settings = load_role_settings(args.env_file)
    factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings[0],
        reviewer_settings=settings[1], transport_root=RUN_DIRECTORY / 'transport')
    result = observe(factory, RUN_DIRECTORY, plan, before_send=lambda: require_unchanged_checkout(head))
    print(compact(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--approval-plan-sha', default='')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    result = run(args)
    if args.execute and not result['pair_accepted']:
        raise SystemExit(1)
