"""Three complete initial reviews in an isolated, exact-request diagnostic route.

Reuses real role stream receipts, shared budget, native review proof and closing
rules. Default product routing remains unchanged; no editor or reassessment.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

from pydantic import ValidationError
from app.evaluation import review_bound_qualification as backend
from app.evaluation.golden_integrated_runtime import Exchange
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatResponse
from app.runtime.reviewer_roles import require_role_provider
from scripts import prepare_document_review_probe as probe
from scripts import report_document_workflow as workflow
from scripts import run_scope_resolution_diagnostic as shared

base = shared.base
EXPERIMENT = 'document-initial-review-diagnostic-20261008'
KEYS = ('actual-mixed', 'explicit-middle-error', 'correct-context')
SOURCE_FILES = tuple(dict.fromkeys((*shared.SOURCE_FILES, *backend.SOURCE_FILES,
    *probe.SOURCE_FILES, 'scripts/run_document_review_diagnostic.py',
    'scripts/document_review_handoff.py', 'scripts/report_document_workflow.py',
    'app/runtime/coach_contract.py', 'app/runtime/runtime.py',
    'app/runtime/receipted_provider_factory.py', 'app/evaluation/golden_integrated_runtime.py',
    'app/providers/zhipu_profiles.py', 'app/providers/models.py', 'app/evaluation/role_qualification.py',
    'app/evaluation/role_task_outcome.py', 'app/evaluation/golden_inference_scope_v5.py',
    'app/model_runtime.py', 'app/providers/zhipu.py', 'app/providers/errors.py',
    'app/providers/stream_adapter_contract.py', 'app/evaluation/golden_stream_diagnostic.py',
    'app/evaluation/golden_http_diagnostics.py', 'app/agent/context.py',
    'app/evaluation/glm53_bounded_revision_budget_reachability.py',
    'app/evaluation/golden_explicit_source_projection.py', 'app/evaluation/golden_native_issues_review.py',
    'app/evaluation/golden_native_tool_review.py', 'app/evaluation/golden_journal.py',
    'app/evaluation/golden_review_experiment.py', 'app/evaluation/golden_role_coarse.py',
    'app/evaluation/golden_native_business_policy.py',
    'scripts/run_boundary_examples_v2.py', 'scripts/run_golden_inference_development.py',
    'scripts/run_role_coach_development.py', 'scripts/diagnose_block_review_route.py',
    'scripts/diagnose_role_context.py', 'scripts/export_partitioned_review.py')))


def controls():
    manifest, artifacts = probe.prepare()
    sources = {row['key']: source for row, source in probe.frozen_cases()[0]}
    variants = []
    for cell in manifest['cells']:
        source = sources[cell['original_key']]
        if cell['synthetic_report']:
            source = replace(source, report=source.report.replace(probe.ANCHOR, probe.EXPLICIT, 1))
        inputs = probe.view.Current.build_inputs(source)
        request = probe.view.project(inputs)
        if probe.encoded(request) != artifacts[cell['key'] + '/document-request.json']:
            raise ValueError('document_diagnostic_control_changed')
        variants.append((cell, inputs, request))
    if tuple(c[0]['key'] for c in variants) != KEYS:
        raise ValueError('document_diagnostic_inventory')
    return manifest, variants


def prepare(*, root_thread_id, independent_thread_id):
    material, _ = controls()
    budget = dict(material['budget_proposal'], per_request_output=32768, per_request_seconds=300)
    return base.freeze_v2_identity(dict(experiment=EXPERIMENT, cells=material['cells'],
        preparation_sha256=base.canonical_sha(material),
        source_seal=material['source_seal'], source_seal_sha256=material['source_seal_sha256'],
        source_sha256={p: base.digest((base.ROOT/p).read_text(encoding='utf-8')) for p in SOURCE_FILES},
        baseline_provenance_identity=backend.candidate_identity(),
        report_presentation=probe.view.VERSION, diagnostic_route='exact-document-initial-only-v1',
        host_review_submission_mode=base.MODE_V2, host_review_evidence_policy=base.FINAL_POLICY,
        max_host_seconds=86400, budget=budget, sequence=list(KEYS),
        role_calls={'glm-5.3': 3, 'glm-5.3-flash': 0}, sdk_retries=0,
        execution_authorized=False, product_admitted=False, original15_qualified=False,
        model=material['model'], stop_rule=material['stop_rule'],
        limitations=material['limitations'], decisions=material['decision'],
        acceptance='Both real full-source reviews accept each entire assessment. No false findings, missed true errors, unsupported corrections or presentation-induced errors. Correct control pass>=85. Report assessment is null.'),
        root_thread_id=root_thread_id, primary_id=root_thread_id, independent_id=independent_thread_id)


class DocumentDiagnosticRoute:
    """Whitelist exact controls; normalize only timeout/budget metadata for identity.

    Baseline restoration is for source/role validation ONLY. Transport receives
    the actual document request and binds its actual bytes, never the baseline.
    """
    def __init__(self, variants):
        self.variants = variants

    def baseline(self, request):
        metadata = dict(request.metadata)
        marker = metadata.pop('coach_budget_contract', None)
        if marker not in (None, 'coach-bounded-review-v2'):
            raise ValueError('document_diagnostic_budget_marker')
        for _, inputs, prepared in self.variants:
            if (0 < request.timeout_s <= prepared.timeout_s and
                replace(request, timeout_s=prepared.timeout_s, metadata=metadata) == prepared):
                return probe.view.restore(prepared, inputs)
        raise ValueError('document_diagnostic_request_not_frozen')

    def request_identity(self, request):
        return base.CONTRACT.request_identity(self.baseline(request))


class DocumentDiagnosticProvider:
    """Use existing trusted role endpoints with a strict diagnostic-only selector."""
    def __init__(self, router, route):
        base.CONTRACT.require_provider(router)
        self.route, self.reviewer = route, router.reviewer
        for attr in ('provider_name', 'model_name', 'thinking_profile_id', 'sdk_max_retries',
                     'runtime_profile', 'source_projection', 'capabilities'):
            setattr(self, attr, getattr(router, attr))
        self.last_exchange, self.attempts, self._calls, self._failed = None, [], 0, False

    def chat(self, request):
        self.last_exchange = None
        if self._failed:
            raise ProviderResponseError(provider='zhipu', code='document_diagnostic_stopped')
        response = attempt = None
        try:
            expected = self.route.request_identity(request)
            require_role_provider(self.reviewer, 'review')
            raw = base.validate_request(request, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)
            previous = getattr(self.reviewer, 'last_exchange', None)
            self._calls += 1
            attempt = dict(ordinal=self._calls, role='review', model=expected[1],
                profile=self.reviewer.thinking_profile_id, transport_id=base.REVIEW_MODEL_TRANSPORT_ID,
                request_sha256=hashlib.sha256(raw).hexdigest(), status='started')
            self.attempts.append(attempt)
            send = getattr(self.reviewer, 'chat_at_ordinal', None)
            response = (send(request, ordinal=self._calls, role='review') if callable(send)
                        else self.reviewer.chat(request))
            if not isinstance(response, ChatResponse) or (response.provider, response.model) != expected:
                raise ProviderResponseError(provider='zhipu', code='document_diagnostic_response_identity')
            attempt.update(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens)
            exchange = getattr(self.reviewer, 'last_exchange', None)
            if (not isinstance(exchange, Exchange) or exchange is previous or exchange.response is not response
                or exchange.receipt_request_sha256 != attempt['request_sha256']
                or probe.sha(base.validate_request(exchange.issued_request,
                    transport_id=base.REVIEW_MODEL_TRANSPORT_ID)) != attempt['request_sha256']):
                raise ProviderResponseError(provider='zhipu', code='document_diagnostic_receipt')
            self.last_exchange, attempt['status'] = exchange, 'completed'
            return response
        except BaseException as error:
            self._failed = True
            if attempt is not None:
                attempt.update(status='failed', error=getattr(error, 'code', type(error).__name__))
            if isinstance(response, ChatResponse) and isinstance(error, ProviderResponseError):
                error.observed_response = response
                error.observed_usage = response.usage
            raise


class DiagnosticLimits:
    """Instance-scoped narrower limits; no product contract registration."""
    def __init__(self, route, budget):
        self.route, self.budget = route, budget
        self.grounded = True

    def descriptor(self):
        return dict(base.CONTRACT.descriptor(), max_calls=self.budget['max_calls'],
            total_tokens=self.budget['max_tokens'], execution_timeout_s=self.budget['max_active_seconds'])

    def request_identity(self, request):
        return self.route.request_identity(request)


def observe(factory, directory, plan, *, event_source, adjudicate=base.wait_reviews,
            before_send=lambda: None):
    base.require_execution_event_source(plan, event_source)
    material, variants = controls()
    if (plan['cells'] != material['cells'] or plan['sequence'] != list(KEYS)
        or plan['preparation_sha256'] != base.canonical_sha(material)
        or plan['role_calls'] != {'glm-5.3': 3, 'glm-5.3-flash': 0}):
        raise ValueError('document_diagnostic_frozen_controls')
    clock = base.DevelopmentHostClock(directory, max_host_seconds=plan['max_host_seconds'])
    route = DocumentDiagnosticRoute(variants)
    router = DocumentDiagnosticProvider(factory('diagnostic'), route)
    budget = base._ReceiptForwardingCoachBudgetedProvider(router, coach_contract=base.CONTRACT, clock=clock)
    # The known product contract validates endpoint composition at construction.
    # This isolated run then installs stricter limits and exact-request identity.
    budget.contract = DiagnosticLimits(route, plan['budget'])
    send = base.SharedBudgetReviewSender(budget)
    result = dict(experiment=EXPERIMENT, diagnostic_accepted=False, stages=[],
        product_admitted=False, original15_qualified=False)
    try:
        for cell, inputs, prepared in variants:
            clock.before_send()
            before_send()
            remaining = plan['budget']['max_active_seconds'] - clock()
            if (remaining <= 0 or budget.calls >= plan['budget']['max_calls']
                or budget.tokens + budget.reserved_tokens + base.size(prepared) + prepared.max_tokens > plan['budget']['max_tokens']):
                raise ValueError('document_diagnostic_budget')
            arm = Path(directory)/cell['key']
            arm.mkdir(exist_ok=False)
            base.write_new_json(arm/'source.json', dict(input_json=inputs.data_json,
                report=inputs.source.report, synthetic_report=cell['synthetic_report']))
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
                stage_sha256=base.stage_identity(stage), scope='Judge every claim in the assessment against complete report and sources under whole-context standard. Include presentation-induced errors. Report assessment must be null.'))
            submitted = clock.adjudicate(arm/'review-required.json',
                plan['budget']['max_active_seconds'] - clock(), adjudicate)
            base.write_new_json(arm/'host-reviews.json', submitted)
            accepted = shared.validate_reviews(submitted, stage, bound, plan, event_source)
            result['stages'].append(dict(key=cell['key'], binding=bound, host_accepted=accepted,
                verdict=wire.verdict, score=wire.score))
            if not accepted:
                raise ValueError('document_diagnostic_host_rejected')
            # Minimal protocol guard only. Full-source Host judgment decides
            # semantics, never an exact expected block set or fixed wording.
            if (cell['key'] == 'correct-context' and (wire.verdict != 'pass' or wire.score < 85)
                or cell['key'] != 'correct-context' and wire.verdict != 'needs_revision'):
                raise ValueError('document_diagnostic_unexpected_verdict')
            if clock() >= plan['budget']['max_active_seconds']:
                raise ValueError('document_diagnostic_budget')
            before_send()
        result['diagnostic_accepted'] = True
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(error, ValidationError):
            code = 'document_diagnostic_schema_validation'
            result['validation_errors'] = error.errors(include_input=False, include_context=False, include_url=False)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,100}', code):
            result['error_code'] = code
    finally:
        result.update(calls=budget.calls, known_tokens=budget.tokens,
            unknown_reserved_tokens=budget.reserved_tokens, attempts=router.attempts, timing=clock.summary())
        shared.close_result(directory, result)
    return result


def read_calls(directory):
    from app.evaluation.role_qualification import read_role_calls
    route = DocumentDiagnosticRoute(controls()[1])
    def role(request):
        if route.request_identity(request) != ('zhipu', 'glm-5.3'):
            raise ValueError('document_diagnostic_role')
        return 'review'
    return read_role_calls(directory, request_role=role)


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
