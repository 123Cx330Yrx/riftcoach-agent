"""Two prospective reassessments using existing protocol, never original15 credit.

No wording intervention, editor, automatic retry or product registration. The
historical opinion is supplied as untrusted context. Source judgments concern
the new assessment; they never certify that the still-incorrect report is fixed.
"""
import argparse
from contextlib import contextmanager
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import time

from pydantic import ValidationError

from app.evaluation import review_bound_qualification as backend
from app.evaluation.golden_stream_bridge import REQUEST
from scripts import prepare_scope_resolution_probe as probe
from scripts import run_coarse_edit_diagnostic as base

EXPERIMENT = 'scope-resolution-diagnostic-20261008'
KEYS = ('actual-mixed', 'explicit-middle-counterfactual')
SOURCE_FILES = ('scripts/run_scope_resolution_diagnostic.py',
    'scripts/scope_resolution_handoff.py',
    'scripts/prepare_scope_resolution_probe.py', 'scripts/run_coarse_edit_diagnostic.py',
    'app/evaluation/review_bound_qualification.py', 'app/evaluation/golden_role_boundary_examples.py',
    'app/evaluation/golden_role_correction_scope.py', 'app/evaluation/golden_role_clarity.py',
    'app/evaluation/golden_native_issues_review.py', 'app/evaluation/golden_semantic_review.py',
    'app/runtime/reviewer_roles.py', 'app/runtime/coach_budget.py',
    'app/runtime/review_sender.py', 'app/evaluation/golden_stream_bridge.py',
    'scripts/review_independence_contract.py', 'scripts/codex_review_event_source.py',
    'scripts/role_development_host_clock.py')


@contextmanager
def submission_close_gate(directory):
    """Short OS lock shared by decision publication and terminal-result write.

    Native event reads occur outside this gate. The OS releases the lock on
    process exit; the one-byte file remains evidence, not a stale lock marker.
    """
    with (Path(directory) / 'submission-close.lock').open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'\0')
            handle.flush()
        deadline = time.monotonic() + 10
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError('scope_resolution_close_gate_timeout')
                time.sleep(.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def close_result(directory, result):
    with submission_close_gate(directory):
        base.write_new_json(Path(directory) / 'result.json', result)


def controls():
    evidence = probe.prepare()
    original = next(s for f, s in backend.frozen_cases()[0] if f['key'] == 'claim-scope:3')
    result = []
    for cell in evidence['cells']:
        source = original if not cell['synthetic_report'] else replace(original,
            report=original.report.replace('早期死亡在胜败样本间几乎相同',
                                           '中单早期死亡在中单胜败样本间几乎相同', 1))
        inputs = backend.Workflow.build_inputs(source)
        request = REQUEST.validate_json(json.dumps(cell['request']), strict=True)
        text = request.messages[1].content
        data = json.loads(text.split('\n', 1)[1].rsplit('\n', 1)[0])
        # Reuse the exact historical raw string, not a reordered serialization.
        seal = json.loads((base.ROOT / probe.SEAL).read_bytes())
        previous_raw = seal['public_json_contents']['claim-scope-3/initial-journal.json']['raw']
        rebuilt = backend.Workflow.make_request(inputs, previous_raw=previous_raw)
        if (request != rebuilt or base.digest(inputs.data_json) != cell['input_sha256']
                or data['previous_review'] != json.loads(previous_raw)):
            raise ValueError('scope_resolution_control_changed')
        result.append((cell, inputs, request, previous_raw))
    if tuple(c[0]['key'] for c in result) != KEYS:
        raise ValueError('scope_resolution_inventory')
    return result


def prepare(*, root_thread_id, independent_thread_id):
    rows = [{k: v for k, v in cell.items() if k != 'request'} for cell, *_ in controls()]
    prices = base.CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    cost = 2 * (Decimal(64000) * prices.input_cost_per_million
                + Decimal(32768) * prices.output_cost_per_million) / 1_000_000
    plan = dict(experiment=EXPERIMENT, cells=rows, source_seal=probe.SEAL,
        source_seal_sha256=probe.SEAL_SHA, candidate_identity=backend.candidate_identity(),
        source_sha256={p: base.digest((base.ROOT / p).read_text(encoding='utf-8')) for p in SOURCE_FILES},
        host_review_submission_mode=base.MODE_V2, host_review_evidence_policy=base.FINAL_POLICY,
        max_host_seconds=86400, budget=dict(max_calls=2, max_tokens=193536,
            max_active_seconds=600, per_request_output=32768, per_request_seconds=300,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        role_calls={'glm-5.3': 2, 'glm-5.3-flash': 0}, sdk_retries=0,
        historical_initial_inputs=2, historical_initial_distinct_opinions=1,
        model='glm-5.3', reasoning_effort='high', temperature=1, top_p=.95,
        labels_sent_to_model=False, execution_authorized=False,
        product_admitted=False, original15_qualified=False,
        intervention='Existing full reassessment with an untrusted historical opinion; no new policy or schema.',
        sequence=list(KEYS),
        acceptance='Both genuine source reviews accept each assessment. Actual mixed: withdraw old issue1, keep issue2. Explicit MIDDLE counterfactual: keep both. No additional false findings or unsupported corrections.',
        stop_rule='First semantic, host, protocol, source, identity, transport or budget failure stops. No retries, editor, batch restart or remaining-budget transfer.',
        success_scope='Two historical-opinion-conditioned diagnostic controls only; not blind holdout, reliability rate, original15, or product qualification.',
        product_path_constraint=dict(current_max_calls=5,
            natural_generate_review_reassess_edit_fresh_calls=6,
            automatic_insertion_feasible_under_current_budget=False,
            evidence='tests/test_review_boundary_examples.py::test_actual_application_initial_edit_fresh_and_shared_budget',
            diagnostic_does_not_change_budget=True),
        success_decision='Reassessment capability only. Natural generation plus initial/reassessment/edit/fresh requires six calls versus the unchanged five-call product cap. Resolve trigger and whole-task budget/strategy before considering adoption; no automatic insertion.',
        failure_decision='Preserve the first divergence; reject sufficiency of existing full reassessment for these controls. No automatic prompt variation.')
    return base.freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id)


def validate_reviews(submission, stage, bound, plan, event_source):
    accepted = []
    for role in ('primary', 'independent'):
        review = submission[role]
        if review.get('binding') != base.required_binding(bound):
            raise ValueError('scope_resolution_host_binding')
        judgment = base.StageAssessment.model_validate(review['stage_assessment'])
        if (judgment.stage != stage['stage'] or judgment.stage_sha256 != base.stage_identity(stage)
                or judgment.reviewer != plan['review_principals'][role]['principal_id']
                or 'report_assessment' not in review or review['report_assessment'] is not None):
            raise ValueError('scope_resolution_host_scope')
        if role == 'primary':
            base.validate_primary_attestation(review, plan=plan, bound=bound)
        else:
            base.validate_independent_event(review, plan=plan, bound=bound, event_source=event_source)
        accepted.append(judgment.accepted)
    return all(accepted)


def expected_mapping(wire, cell):
    """Diagnostic labels are a stop check after source review, never a repair."""
    resolutions = sorted(wire.issue_resolutions, key=lambda r: r.previous_id)
    if (wire.verdict != 'needs_revision'
            or sorted(i.block for i in wire.issues) != cell['host_only_expected_issue_blocks']
            or [r.disposition for r in resolutions] != cell['host_only_expected_dispositions']):
        raise ValueError('scope_resolution_unexpected_judgment')
    for resolution, block in zip(resolutions, (4, 6)):
        if resolution.disposition == 'replaced' and wire.issues[resolution.final_issue - 1].block != block:
            raise ValueError('scope_resolution_wrong_issue_mapping')


def observe(factory, directory, plan, *, event_source, adjudicate=base.wait_reviews,
            before_send=lambda: None):
    base.require_execution_event_source(plan, event_source)
    if plan['sequence'] != list(KEYS) or plan['role_calls'] != {'glm-5.3': 2, 'glm-5.3-flash': 0}:
        raise ValueError('scope_resolution_plan')
    variants = controls()
    if plan['cells'] != [{k: v for k, v in c.items() if k != 'request'} for c, *_ in variants]:
        raise ValueError('scope_resolution_frozen_controls')
    clock = base.DevelopmentHostClock(directory, max_host_seconds=plan['max_host_seconds'])
    router = factory('diagnostic')
    budget = base._ReceiptForwardingCoachBudgetedProvider(router, coach_contract=base.CONTRACT, clock=clock)
    send = base.SharedBudgetReviewSender(budget)
    result = dict(experiment=EXPERIMENT, diagnostic_accepted=False, stages=[],
        product_admitted=False, original15_qualified=False, historical_initial_inputs=2)
    try:
        for cell, inputs, prepared, previous_raw in variants:
            clock.before_send()
            before_send()
            remaining = plan['budget']['max_active_seconds'] - clock()
            if (remaining <= 0 or budget.calls >= plan['budget']['max_calls']
                    or budget.tokens + budget.reserved_tokens + base.size(prepared) + prepared.max_tokens > plan['budget']['max_tokens']):
                raise ValueError('scope_resolution_budget')
            arm = Path(directory) / cell['key']
            arm.mkdir(exist_ok=False)
            base.write_new_json(arm / 'source.json', dict(input_json=inputs.data_json,
                report=inputs.source.report, previous_raw=previous_raw, synthetic_report=cell['synthetic_report']))
            exchange = send(replace(prepared, timeout_s=min(prepared.timeout_s, remaining)))
            base.write_new_json(arm / 'request.json', json.loads(base.validate_request(
                exchange.issued_request, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)))
            base.write_new_json(arm / 'response.json', base.public_response(json.loads(base.RESPONSE.dump_json(exchange.response))))
            raw = base.tool_result(prepared, exchange)
            _, wire, journal = backend.Workflow.validate_review(raw, inputs, previous_raw=previous_raw)
            stage = dict(stage='initial', report=inputs.source.report, journal=journal)
            base.write_new_json(arm / 'stage.json', stage)
            bound = dict(plan_sha256=base.canonical_sha(plan), key=cell['key'], stage='initial',
                response_sha256=base.sha(arm / 'response.json'), report_sha256=base.digest(stage['report']),
                request_sha256=exchange.receipt_request_sha256)
            base.write_new_json(arm / 'review-required.json', dict(binding=bound,
                stage_sha256=base.stage_identity(stage), scope='Judge the reassessment and every resolution against the complete report and sources. The report is intentionally not repaired. report_assessment must be null; do not certify it as correct.'))
            submitted = clock.adjudicate(arm / 'review-required.json',
                plan['budget']['max_active_seconds'] - clock(), adjudicate)
            base.write_new_json(arm / 'host-reviews.json', submitted)
            accepted = validate_reviews(submitted, stage, bound, plan, event_source)
            result['stages'].append(dict(key=cell['key'], binding=bound, host_accepted=accepted,
                verdict=wire.verdict, score=wire.score))
            if not accepted:
                raise ValueError('scope_resolution_host_rejected')
            expected_mapping(wire, cell)
            if clock() >= plan['budget']['max_active_seconds']:
                raise ValueError('scope_resolution_budget')
            before_send()
        result['diagnostic_accepted'] = True
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(error, ValidationError):
            code = 'scope_resolution_schema_validation'
            result['validation_errors'] = error.errors(include_input=False, include_context=False, include_url=False)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,100}', code):
            result['error_code'] = code
    finally:
        result.update(calls=budget.calls, known_tokens=budget.tokens,
            unknown_reserved_tokens=budget.reserved_tokens, attempts=router.attempts, timing=clock.summary())
        close_result(directory, result)
    return result


def run(args):
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
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--plan-sha')
    parser.add_argument('--ci-run')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--codex-executable', type=Path)
    result = run(parser.parse_args())
    print(base.compact(result), flush=True)
    if 'diagnostic_accepted' in result and not result['diagnostic_accepted']:
        raise SystemExit(1)
