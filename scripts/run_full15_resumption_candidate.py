"""Candidate full15 initial/edit/fresh entrypoint.

The runner reuses the existing role transport, host-review contract and
strict result closure.  It is deliberately unadmitted: without an explicit
execution authorization it can only prepare a plan.  A later execution must
pin this plan, CI, native reviewers and a new run directory before any model
request is sent.
"""
from dataclasses import replace
from decimal import Decimal
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from pydantic import ValidationError

from app.evaluation import document_review_qualification as qualification
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, RESPONSE, validate_request
from app.evaluation.role_task_outcome import ReportAssessment, StageAssessment, stage_identity
from app.harness.steps import RevisionRequest
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts import report_contrast_review as candidate
from scripts.review_independence_contract import (
    FINAL_POLICY, MODE_V2, freeze_v2_identity, require_execution_event_source,
    required_binding, validate_independent_event, validate_primary_attestation,
)
from scripts.role_development_host_clock import DevelopmentHostClock
from scripts.run_boundary_examples_v2 import verify_native_principals
from scripts.run_golden_inference_development import verify_public_ci
from scripts.run_role_coach_development import load_role_settings, require_unchanged_checkout
from scripts.diagnose_block_review_route import route_environment
from scripts.diagnose_role_context import canonical_sha
from scripts.host_review_task_checkpoint import publish as publish_checkpoint
from scripts.host_review_task_checkpoint import read as read_checkpoint
from scripts.document_review_host_task import with_policies
from scripts.export_partitioned_review import public_response
from scripts.run_scope_resolution_diagnostic import close_result
from scripts.codex_review_event_source import (
    CodexHostReviewEventSource, CodexReadOnlyClient, review_task,
)

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 'document-full15-resumption-candidate-20261009'
STAGES = ('initial', 'revision', 'final')
VERSION = 'full15-resumption-candidate-runner-v1'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bytes_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def controls(root=ROOT):
    """Build candidate requests from public frozen cases and verify baselines."""
    rows, variants = [], []
    frozen, _ = qualification.frozen_cases(root=root)
    for cell, source in frozen:
        inputs = candidate.DocumentReviewWorkflow.build_inputs(source)
        original = candidate.DocumentReviewWorkflow.make_request(inputs)
        request = candidate.ContrastDocumentWorkflow.make_request(inputs)
        if candidate.baseline_request(request) != original:
            raise ValueError('full15_candidate_baseline_changed')
        rows.append(dict(cell, candidate_request_sha256=_bytes_sha(
            validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID))))
        variants.append((cell, source, inputs, request))
    if len(variants) != 15:
        raise ValueError('full15_candidate_inventory')
    return rows, variants


class CandidateLimits:
    """Instance overlay; no global contract registration or product adoption."""
    grounded = True

    def __init__(self, budget):
        self.budget = budget

    def __getattr__(self, name):
        return getattr(DOCUMENT_REVIEW_COACH_CONTRACT, name)

    @staticmethod
    def request_identity(request):
        return candidate.request_identity(request)

    def descriptor(self):
        value = DOCUMENT_REVIEW_COACH_CONTRACT.descriptor()
        value.update(max_calls=self.budget['max_calls'],
                     total_tokens=self.budget['max_tokens'],
                     execution_timeout_s=self.budget['max_active_seconds'])
        return value

    def require_provider(self, provider):
        candidate.ContrastDiagnosticLimits().require_provider(provider)


class CandidateProviderFactory(RunScopedRoleReceiptedProviderFactory):
    router_type = candidate.ContrastDiagnosticRouter

    def __init__(self, **kwargs):
        kwargs.setdefault('source_projection', DOCUMENT_REVIEW_COACH_CONTRACT.descriptor()['source_projection'])
        super().__init__(**kwargs)


def prepare(*, root_thread_id, independent_thread_id, root=ROOT):
    rows, variants = controls(root)
    price = DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles
    # Every case may need initial + fresh review and one Flash edit. This is a
    # worst-case envelope, not a prediction and not permission to spend it.
    role_calls = {'glm-5.3': 30, 'glm-5.3-flash': 15}
    calls = sum(role_calls.values())
    cost = sum(n * (Decimal(64000) * price['zhipu', model].input_cost_per_million
        + Decimal(32768) * price['zhipu', model].output_cost_per_million) / 1_000_000
        for model, n in role_calls.items())
    source_files = tuple(dict.fromkeys((*qualification.SOURCE_FILES,
        'scripts/report_block_keyed_editor.py', 'scripts/report_contrast_review.py',
        'scripts/run_full15_resumption_candidate.py',
        'scripts/full15_resumption_evidence.py',
        'scripts/host_review_task_checkpoint.py',
        'scripts/document_review_host_task.py',
        'scripts/review_independence_contract.py',
        'scripts/codex_review_event_source.py',
        'scripts/export_partitioned_review.py',
        'scripts/role_development_host_clock.py',
        'scripts/run_scope_resolution_diagnostic.py',
        'scripts/run_boundary_examples_v2.py',
        'scripts/run_role_coach_development.py',
        'scripts/run_golden_inference_development.py',
        'app/evaluation/role_qualification.py',
        'app/runtime/runtime.py', 'app/runtime/review_sender.py')))
    plan = dict(kind=VERSION, run_id=RUN_ID, cells=rows,
        sequence=[r['key'] for r in rows], source_sha256={p: _sha(root / p)
            for p in source_files}, candidate_policy=candidate.VERSION,
        candidate_editor=candidate.editor.VERSION, host_review_submission_mode=MODE_V2,
        host_review_evidence_policy=FINAL_POLICY, max_host_seconds=86400,
        budget=dict(max_calls=calls, role_calls=role_calls, max_tokens=calls * 96768,
            max_active_seconds=calls * 300, max_host_seconds=86400,
            per_request_output=32768, per_request_seconds=300,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        sdk_retries=0, execution_authorized=False, paid_plan_frozen=False,
        product_admitted=False, original15_qualified=False, new_qualification=0,
        historical_reviews_reused=False,
        acceptance='Real full-source native primary and independent review for every '
            'completed stage. Initial assesses the opinion with report_assessment=null; '
            'accepted revision/final stages require four true ReportAssessment flags; '
            'fresh requires pass>=85 without material false or missed findings.',
        semantic_failure_rule='A semantic rejection ends that case dependency and the '
            'next independent case may continue. Identity/source/native/checkpoint/protocol/'
            'transport/budget/availability failure stops the batch.',
        stop_rule='No retry, reassessment, restart, old-review reuse, or qualification credit.',
        limitations=['Candidate policy and keyed editor are unproven teaching hypotheses.',
            'Preparation and local tests are not model or product evidence.'])
    return freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id)


def _validate_reviews(submission, stage, bound, plan, event_source, *, initial=False):
    if set(submission) != {'primary', 'independent', 'checkpoint_evidence'}:
        raise ValueError('full15_submission_fields')
    accepted = []
    for role in ('primary', 'independent'):
        review = submission[role]
        if review.get('binding') != required_binding(bound):
            raise ValueError('full15_host_binding')
        assessment = StageAssessment.model_validate(review['stage_assessment'])
        report_raw = review['report_assessment']
        if initial:
            if report_raw is not None:
                raise ValueError('full15_initial_report_scope')
        else:
            report = ReportAssessment.model_validate(report_raw)
            if report.report_sha256 != bound['report_sha256'] or report.reviewer != plan['review_principals'][role]['principal_id']:
                raise ValueError('full15_report_binding')
            if assessment.accepted and not all((report.facts_and_sources_correct,
                    report.correct_content_preserved, report.identity_and_goal_preserved,
                    report.true_errors_fixed)):
                raise ValueError('full15_report_contradiction')
        if (assessment.stage != stage['stage'] or assessment.stage_sha256 != stage_identity(stage)
                or assessment.reviewer != plan['review_principals'][role]['principal_id']):
            raise ValueError('full15_stage_binding')
        if role == 'primary':
            validate_primary_attestation(review, plan=plan, bound=bound)
        else:
            validate_independent_event(review, plan=plan, bound=bound, event_source=event_source)
        accepted.append(assessment.accepted)
    return all(accepted)


def _task(plan, arm, stage, value, bound, request_raw, *, initial_raw=None):
    principal = plan['review_principals']['independent']['principal_id']
    report_rule = ('Set report_assessment=null.' if stage == 'initial' else
        'report_assessment contains report_sha256=' + bound['report_sha256'] + ', reviewer, source_review, '
        'facts_and_sources_correct, correct_content_preserved, identity_and_goal_preserved, true_errors_fixed. '
        'All four flags must be true for an accepted stage.')
    task = review_task(bound, (
        f'Read {arm}/source.json and {arm}/{stage}/issued-request.json, '
        f'{arm}/{stage}/response.json, {arm}/{stage}/stage.json and '
        f'{arm}/{stage}/review-required.json; inspect the complete report, source, citations, '
        'journal, editor operations, retained content and policy. Return only the '
        'binding + review JSON envelope. Both outer binding and review.binding must '
        'equal the exact six task binding fields. review contains binding, stage_assessment and '
        f'report_assessment. stage_assessment contains stage={stage}, '
        f'stage_sha256={stage_identity(value)}, reviewer={principal}, source_review, '
        'accepted boolean, and defects [{kind, detail}]. Defect kinds: missed_error, '
        'false_positive, unsupported_explanation, wrong_correction, unsupported_source, '
        'internal_contradiction, wrong_final_report, correct_content_lost, identity_or_goal_changed. '
        + report_rule + ' Do not read host-reviews.json, '
        'review-submission.json, primary notes or other Host opinions. '
        'Judge the actual stage, never infer a verdict '
        'from the expected case label. accepted=true requires empty defects. '
        'For revision/final also fill all four ReportAssessment booleans.'))
    return with_policies(task,
        request_raw, initial_raw=initial_raw,
        initial_sha256=_bytes_sha(initial_raw) if initial_raw else None)


def wait_reviews(path, remaining):
    """Publish the exact checkpoint, then wait for a reviewer submission."""
    path = Path(path)
    required = json.loads((path.parent / 'review-required.json').read_bytes())
    stage = required['binding']['stage']
    arm = path.parent.parent
    plan = json.loads((path.parents[2] / 'plan.json').read_bytes())['preparation_plan']
    from scripts import full15_resumption_evidence as evidence
    task_raw = evidence.task(path.parents[2], required['binding']['key'], stage)
    task_path = path.parent / 'independent-task.json'
    with task_path.open('x', encoding='utf-8') as stream:
        stream.write(task_raw + '\n')
    checkpoint_path = path.parent / 'task-checkpoint.json'
    checkpoint_sha = publish_checkpoint(checkpoint_path, task_path,
        plan['review_principals']['independent']['principal_id'])
    from scripts.host_review_task_checkpoint import dispatch
    with (path.parent / 'dispatch.txt').open('x', encoding='utf-8') as stream:
        stream.write(dispatch(checkpoint_path, checkpoint_sha) + '\n')
    submission = path.parent / 'review-submission.json'
    deadline = time.monotonic() + remaining
    while time.monotonic() < deadline:
        abort = path.parent / 'operator-abort.json'
        if abort.exists():
            validate_abort(strict_json(abort.read_text(encoding='utf-8')), required['binding'])
            raise ValueError('full15_operator_abort')
        if submission.exists():
            read_checkpoint(checkpoint_path, checkpoint_sha)
            value = strict_json(submission.read_text(encoding='utf-8'))
            evidence.validate_checkpoint(path.parent, value, json.loads(task_raw), plan, required['binding'])
            return value
        time.sleep(0.25)
    raise ValueError('full15_host_deadline')


def validate_abort(marker, bound):
    if (set(marker) != {'kind', 'binding', 'reason'} or marker['kind'] != 'full15-operator-abort-v1'
            or marker['binding'] != required_binding(bound)
            or marker['reason'] not in ('reviewer_unavailable', 'routing_failure', 'operator_stop')):
        raise ValueError('full15_abort_invalid')


class RecordedProvider:
    """Record the actual budgeted attempt before transport; never make a receipt."""
    def __init__(self, provider, arm):
        self.provider, self.arm, self.stage = provider, Path(arm), None

    def __getattr__(self, name):
        return getattr(self.provider, name)

    def chat(self, request):
        folder = self.arm / self.stage
        transport = CAPACITY_TRANSPORT_ID if self.stage == 'revision' else REVIEW_MODEL_TRANSPORT_ID
        with (folder / 'issued-request.json').open('xb') as stream:
            stream.write(validate_request(request, transport_id=transport))
        try:
            response = self.provider.chat(request)
        except BaseException as error:
            response = getattr(error, 'observed_response', None)
            if response is not None:
                _write_json(folder / 'response.json', public_response(json.loads(RESPONSE.dump_json(response))))
            raise
        _write_json(folder / 'response.json', public_response(json.loads(RESPONSE.dump_json(response))))
        return response


def _write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def observe(factory, directory, plan, *, event_source, adjudicate, before_send=lambda: None):
    require_execution_event_source(plan, event_source)
    rows, variants = controls()
    if plan['cells'] != rows or plan['sequence'] != [r['key'] for r in rows]:
        raise ValueError('full15_controls_changed')
    directory = Path(directory)
    clock = DevelopmentHostClock(directory, max_host_seconds=plan['max_host_seconds'])
    budget = None
    result = dict(experiment=RUN_ID, cases=[], scan_completed=False,
        diagnostic_accepted=False, provider_calls=0, new_qualification=0,
        original15_qualified=False, product_admitted=False)
    try:
        for cell, source, inputs, prepared_initial in variants:
            key, arm = cell['key'], directory / cell['key'].replace(':', '-')
            arm.mkdir(exist_ok=False)
            outcome = dict(key=key, stages=[], semantic_accepted=False)
            result['cases'].append(outcome)
            directory.joinpath('transport').mkdir(exist_ok=True)
            _write_json(arm / 'source.json', dict(input_json=inputs.data_json, report=source.report))
            router = RecordedProvider(factory(cell['key'].replace(':', '-')), arm)
            if budget is None:
                budget = _ReceiptForwardingCoachBudgetedProvider(router,
                    coach_contract=DOCUMENT_REVIEW_COACH_CONTRACT, clock=clock)
                budget.contract = CandidateLimits(plan['budget'])
            else:
                budget.provider = router
            sender = SharedBudgetReviewSender(budget)
            exchanges = []
            def send(request):
                if router.stage in sent_stages:
                    raise ValueError('full15_reassessment_forbidden')
                clock.before_send()
                before_send()
                (arm / router.stage).mkdir(exist_ok=False)
                sent_stages.append(router.stage)
                exchange = sender(request)
                exchanges.append(exchange)
                return exchange
            flow = candidate.ContrastDocumentWorkflow(send)
            sent_stages = []
            try:
                router.stage = 'initial'
                first = flow.evaluate(source)
                _write_stage(arm, 'initial', source.report, flow.last_journal, exchanges[-1], plan, key, source, inputs,
                             initial=True)
                initial_submission = clock.adjudicate(arm / 'initial' / 'review-required.json',
                    plan['budget']['max_active_seconds'] - clock(), adjudicate)
                _write_submission(arm / 'initial', initial_submission)
                initial_value = json.loads((arm / 'initial' / 'stage.json').read_bytes())
                initial_bound = json.loads((arm / 'initial' / 'review-required.json').read_bytes())['binding']
                accepted = _validate_reviews(initial_submission, initial_value, initial_bound, plan, event_source, initial=True)
                _finalize_stage(outcome, 'initial', initial_bound, accepted)
                outcome.update(initial_verdict=first.verdict.value, initial_score=first.score)
                if not accepted:
                    outcome['semantic_failure'] = 'initial_host_rejected'
                elif not initial_verdict_valid(cell, first.verdict.value, first.score):
                    outcome['semantic_failure'] = 'initial_unexpected_verdict'
                elif first.verdict.value == 'pass' and first.score >= 85:
                    outcome['semantic_accepted'] = True
                else:
                    router.stage = 'revision'
                    revision = flow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
                        source.knowledge, source.report, first))
                    _write_stage(arm, 'revision', revision.report, flow.last_edit_journal, exchanges[-1], plan, key, source, inputs)
                    revision_submission = clock.adjudicate(arm / 'revision' / 'review-required.json',
                        plan['budget']['max_active_seconds'] - clock(), adjudicate)
                    _write_submission(arm / 'revision', revision_submission)
                    revision_value = json.loads((arm / 'revision' / 'stage.json').read_bytes())
                    revision_bound = json.loads((arm / 'revision' / 'review-required.json').read_bytes())['binding']
                    accepted = _validate_reviews(revision_submission, revision_value, revision_bound, plan, event_source)
                    _finalize_stage(outcome, 'revision', revision_bound, accepted)
                    if not accepted:
                        outcome['semantic_failure'] = 'revision_host_rejected'
                    else:
                        router.stage = 'final'
                        fresh = flow.evaluate(replace(source, report=revision.report))
                        _write_stage(arm, 'final', revision.report, flow.last_journal, exchanges[-1], plan, key, source, inputs)
                        final_submission = clock.adjudicate(arm / 'final' / 'review-required.json',
                            plan['budget']['max_active_seconds'] - clock(), adjudicate)
                        _write_submission(arm / 'final', final_submission)
                        final_value = json.loads((arm / 'final' / 'stage.json').read_bytes())
                        final_bound = json.loads((arm / 'final' / 'review-required.json').read_bytes())['binding']
                        accepted = _validate_reviews(final_submission, final_value, final_bound, plan, event_source)
                        _finalize_stage(outcome, 'final', final_bound, accepted)
                        outcome.update(final_verdict=fresh.verdict.value, final_score=fresh.score)
                        if not accepted:
                            outcome['semantic_failure'] = 'fresh_host_rejected'
                        elif fresh.verdict.value != 'pass' or fresh.score < 85:
                            outcome['semantic_failure'] = 'fresh_not_pass'
                        else:
                            outcome['semantic_accepted'] = True
            except BaseException:
                raise
            _write_terminal(arm, outcome)
            if clock() >= plan['budget']['max_active_seconds']:
                raise ValueError('full15_active_deadline')
        result['scan_completed'] = True
        result['diagnostic_accepted'] = all(c['semantic_accepted'] for c in result['cases'])
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(error, ValidationError):
            code = 'full15_schema_validation'
            result['validation_errors'] = error.errors(include_input=False, include_context=False, include_url=False)
        if isinstance(code, str) and re.fullmatch('[a-z][a-z0-9_]{0,99}', code):
            result['error_code'] = code
    finally:
        result.update(provider_calls=budget.calls if budget else 0,
            known_tokens=budget.tokens if budget else 0,
            unknown_reserved_tokens=budget.reserved_tokens if budget else 0,
            timing=clock.summary(), unexecuted_keys=plan['sequence'][len(result['cases']):],
            unfinished_keys=[c['key'] for c in result['cases']
                if not (directory / c['key'].replace(':', '-') / 'case-result.json').exists()])
        result.update(budget_known_tokens=result['known_tokens'],
            budget_unknown_reserved_tokens=result['unknown_reserved_tokens'])
        try:
            from scripts.full15_resumption_evidence import calls_for
            calls = [call for row in result['cases'] for call in calls_for(directory, row['key'])]
            result['known_tokens'] = sum(sum(c['usage'].values()) for c in calls if c['usage'] is not None)
            result['unknown_reserved_tokens'] = sum(qualification.size(c['request']) + c['request'].max_tokens
                for c in calls if c['usage'] is None)
        except Exception as error:
            # Corrupt receipts remain raw evidence and prevent strict sealing;
            # failure to read them never erases the live budget reservation.
            result['accounting_error_type'] = type(error).__name__
        close_result(directory, result)
    return result


def _write_submission(folder, submission):
    from scripts import full15_resumption_evidence as evidence
    folder = Path(folder)
    directory = folder.parents[1]
    plan = json.loads((directory / 'plan.json').read_bytes())['preparation_plan']
    bound = json.loads((folder / 'review-required.json').read_bytes())['binding']
    expected_task = json.loads(evidence.task(directory, bound['key'], bound['stage'], closed=True))
    evidence.validate_checkpoint(folder, submission, expected_task, plan, bound)
    with (Path(folder) / 'host-reviews.json').open('x', encoding='utf-8') as stream:
        json.dump(submission, stream, ensure_ascii=False, indent=2)


def _write_stage(arm, stage, report, journal, exchange, plan, key, source, inputs, *, initial=False):
    folder = Path(arm) / stage
    response = public_response(json.loads(RESPONSE.dump_json(exchange.response)))
    transport = CAPACITY_TRANSPORT_ID if stage == 'revision' else REVIEW_MODEL_TRANSPORT_ID
    request_raw = validate_request(exchange.issued_request, transport_id=transport)
    if ((folder / 'issued-request.json').read_bytes() != request_raw
            or json.loads((folder / 'response.json').read_bytes()) != response
            or _bytes_sha(request_raw) != exchange.receipt_request_sha256):
        raise ValueError('full15_recorded_exchange_changed')
    value = dict(stage=stage, report=report, journal=journal)
    with (folder / 'stage.json').open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    bound = dict(plan_sha256=canonical_sha(plan), key=key, stage=stage,
        response_sha256=_sha(folder / 'response.json'), report_sha256=digest(report),
        request_sha256=_bytes_sha(request_raw))
    with (folder / 'review-required.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(binding=bound, stage_sha256=stage_identity(value), scope=plan['acceptance']), stream, ensure_ascii=False, indent=2)


def initial_verdict_valid(cell, verdict, score):
    return (verdict == 'pass' and score >= 85 if cell['expected_initial'] == 'accept'
            else verdict == 'needs_revision')


def _finalize_stage(outcome, stage, bound, accepted):
    outcome['stages'].append(dict(stage=stage, binding=bound, host_accepted=accepted))


def _write_terminal(arm, outcome):
    with (Path(arm) / 'case-result.json').open('x', encoding='utf-8') as stream:
        json.dump(outcome, stream, ensure_ascii=False, indent=2)


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
    args = parser.parse_args()
    plan = prepare(root_thread_id=args.root_thread_id, independent_thread_id=args.independent_thread_id)
    if not args.execute:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            _write_json(args.output, plan)
        print(compact(dict(plan_sha256=canonical_sha(plan), provider_calls=0,
            execution_ready=False, budget=plan['budget'])))
        return
    if not all((args.preparation, args.plan_sha, args.ci_run, args.env_file, args.codex_executable)):
        raise SystemExit('full15 execution requires preparation, plan-sha, ci-run, env-file and codex-executable')
    if args.plan_sha != canonical_sha(plan) or json.loads(args.preparation.read_bytes()) != plan:
        raise SystemExit('full15_frozen_preparation_required')
    directory = ROOT / 'data/runs/model_comparison' / RUN_ID
    if directory.exists():
        raise SystemExit('full15_run_already_exists')
    head = verify_public_ci(args.ci_run)
    require_unchanged_checkout(head)
    with CodexReadOnlyClient(args.codex_executable) as client:
        verify_native_principals(client, plan)
        event_source = CodexHostReviewEventSource(client, plan)
        require_execution_event_source(plan, event_source)
        generator, reviewer = load_role_settings(args.env_file)
        factory = CandidateProviderFactory(generator_settings=generator,
            reviewer_settings=reviewer, transport_root=directory / 'transport')
        directory.mkdir(parents=True, exist_ok=False)
        (directory / 'plan.json').write_text(json.dumps(dict(
            preparation_plan=plan, plan_sha256=canonical_sha(plan), execution_head=head,
            ci_run=args.ci_run), ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        with route_environment('direct'):
            result = observe(factory, directory, plan, event_source=event_source,
                adjudicate=wait_reviews, before_send=lambda: require_unchanged_checkout(head))
    print(compact(result), flush=True)
    if not result['scan_completed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
