"""Bounded original-set review/edit controls for the current role candidate.

Preview is offline. This completed batch is closed before any execution IO.
Its original execution required the prepared hash, clean exact-HEAD CI,
and existing spending authorization. Host checks every completed business
stage before further IO. Two controls cannot admit the original fifteen or
the product. Raw receipts and run directories are create-only.
"""
import argparse
from dataclasses import replace
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
    ROOT, frozen_cases, read_role_calls, replay_legacy_note_case as replay_case,
)
from app.harness.steps import EvaluationVerdict, RevisionRequest
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
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
CLOSED_EVIDENCE = ROOT / 'data/evaluation/results/golden_role_note_qualification_pair_result_v1.json'


def prepare():
    """Reconstruct the closed batch, never rebind it to current manifests."""
    raw_evidence = CLOSED_EVIDENCE.read_bytes()
    # The public projection sorted dictionary keys. Its reserialized plan hash
    # is not the original insertion-ordered compact JSON hash. Bind the whole
    # unchanged export, including its original hash, rather than rewriting it.
    if hashlib.sha256(raw_evidence).hexdigest() != '700eacc1d70d5c8b651c8f1adcfe23ca2ccc906c3906fd8309805a7fe6b0f673':
        raise ValueError('role_pair_frozen_evidence_changed')
    evidence = json.loads(raw_evidence)
    saved = evidence['public_json_contents']['plan.json']
    plan = saved['preparation_plan']
    sources = {f['key']: source for f, source in frozen_cases()[0]}
    requests = {}
    if [row['key'] for row in plan['cases']] != list(KEYS):
        raise ValueError('role_pair_frozen_cases_changed')
    for row in plan['cases']:
        key = row['key']
        inputs = RoleNoteReviewWorkflow.build_inputs(sources[key])
        request = RoleNoteReviewWorkflow.make_request(inputs)
        raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        original = evidence['original_file_sha256'][key.replace(':', '-') + '-prepared-request.json']
        if hashlib.sha256(raw).hexdigest() != row['request_sha256'] or row['request_sha256'] != original:
            raise ValueError('role_pair_frozen_request_changed')
        requests[key] = raw
    return plan, requests


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe(factory, directory, plan, *, adjudicate=terminal_adjudication,
            clock=time.monotonic, before_send=lambda: None,
            workflow_type=RoleNoteReviewWorkflow, replay=replay_case,
            success_field='pair_accepted'):
    """Run frozen workflows, retaining per-stage host gates outside model input."""
    started = clock()
    sources = {f['key']: (f, source) for f, source in frozen_cases()[0]}
    outcomes = []
    result = dict(experiment=plan.get('experiment', EXPERIMENT), production_admitted=False,
        review_controls_qualified=False, actual_product_task_qualified=False)
    result[success_field] = False
    try:
        for row, budget in zip(plan['cases'], plan['case_budgets'], strict=True):
            key = row['key']
            case_id = key.replace(':', '-')
            arm = directory / case_id
            arm.mkdir(exist_ok=False)
            frozen, source = sources[key]
            outcome = dict(key=key, status='failed', stages=[])
            outcomes.append(outcome)
            write_new_json(arm / 'source.json', dict(input_json=workflow_type.build_inputs(source).data_json,
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
                available = remaining()
                if available <= 0:
                    raise ValueError('role_pair_execution_limit')
                return sender(replace(request, timeout_s=min(request.timeout_s, available)))

            workflow = workflow_type(send)

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
            replayed = replay(frozen, source, calls)
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
        result[success_field] = True
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
                result[success_field] = False
        result.update(cases=outcomes, elapsed_seconds=round(clock() - started, 3))
        write_new_json(directory / 'result.json', result)
    return result


def run(args):
    if args.execute:
        raise ValueError('role_pair_batch_closed')
    plan, requests = prepare()
    plan_sha = digest(compact(plan))
    if not args.execute:
        summary = dict(preparation_plan_sha256=plan_sha, plan=plan, provider_requests=0,
            batch_status='closed', plan_representation='public_projection_not_original_plan_bytes')
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
