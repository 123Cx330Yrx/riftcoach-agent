"""Two full-review controls for ADR0116; isolated transport, no product admission."""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from pydantic import ValidationError

from app.evaluation import review_bound_qualification as backend
from app.providers.models import ChatResponse
from app.runtime.reviewer_roles import require_role_provider
from app.runtime.reviewer_roles import role_descriptor
from app.evaluation.golden_stream_bridge import REQUEST
from scripts import scope_competition_prototype as prototype
from scripts import run_scope_resolution_diagnostic as previous

base = previous.base
EXPERIMENT = 'scope-competition-diagnostic-20261008'
KEYS = ('actual-mixed', 'explicit-middle-counterfactual')
OMITTED = '早期死亡在胜败样本间几乎相同'
EXPLICIT = '中单早期死亡在中单胜败样本间几乎相同'
SOURCE_FILES = (*previous.SOURCE_FILES, 'scripts/scope_competition_prototype.py',
    'scripts/run_scope_competition_diagnostic.py', 'scripts/scope_competition_handoff.py',
    'app/runtime/receipted_provider_factory.py', 'app/providers/zhipu_profiles.py')


def controls():
    # Verify the immutable source seal; do not supply the old model's opinion.
    seal = base.ROOT / previous.probe.SEAL
    if base.sha(seal) != previous.probe.SEAL_SHA:
        raise ValueError('competition_source_seal_changed')
    saved = json.loads(seal.read_bytes())['public_json_contents']['claim-scope-3/source.json']
    original = next(s for f, s in backend.frozen_cases()[0] if f['key'] == 'claim-scope:3')
    if original.report != saved['report'] or original.report.count(OMITTED) != 1:
        raise ValueError('competition_source_changed')
    result = []
    for key, source in zip(KEYS, (original, replace(original,
            report=original.report.replace(OMITTED, EXPLICIT, 1)))):
        inputs = backend.Workflow.build_inputs(source)
        request = prototype.review_request(inputs)
        if key == KEYS[0] and inputs.data_json != saved['input_json']:
            raise ValueError('competition_complete_input_changed')
        cell = dict(key=key, synthetic_report=key != KEYS[0],
            report_sha256=base.digest(source.report), input_sha256=base.digest(inputs.data_json),
            request_sha256=hashlib.sha256(base.validate_request(request,
                transport_id=base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest(),
            input_ceiling=base.size(request),
            host_only_expected_issue_blocks=[6] if key == KEYS[0] else [4, 6],
            host_only_scope_audit_required=key == KEYS[0])
        result.append((cell, inputs, request))
    return result


def prepare(*, root_thread_id, independent_thread_id):
    prices = base.CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    cost = 2 * (Decimal(64000) * prices.input_cost_per_million
        + Decimal(32768) * prices.output_cost_per_million) / 1_000_000
    plan = dict(experiment=EXPERIMENT, cells=[c for c, *_ in controls()],
        source_seal=previous.probe.SEAL, source_seal_sha256=previous.probe.SEAL_SHA,
        prototype=prototype.VERSION,
        source_sha256={p: base.digest((base.ROOT / p).read_text(encoding='utf-8'))
                       for p in SOURCE_FILES},
        host_review_submission_mode=base.MODE_V2, host_review_evidence_policy=base.FINAL_POLICY,
        max_host_seconds=86400, budget=dict(max_calls=2, max_tokens=193536,
            max_active_seconds=600, per_request_output=32768, per_request_seconds=300,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        role_calls={'glm-5.3': 2, 'glm-5.3-flash': 0}, sdk_retries=0,
        model='glm-5.3', reasoning_effort='high', temperature=1, top_p=.95,
        labels_sent_to_model=False, historical_initial_inputs=0,
        execution_authorized=False, product_admitted=False, original15_qualified=False,
        sequence=list(KEYS),
        routing='Exact frozen request -> isolated GLM/high receipted transport. No production router/schema registration.',
        acceptance='Full source-based dual review of every issue, correction, marker and scope audit. Actual mixed must keep the CS error without the early-death false issue and explicitly resolve that competition. Explicit MIDDLE must keep both true errors; a redundant scope audit is not required for the explicit claim.',
        stop_rule='First semantic, host, protocol, source, identity, transport or budget failure stops. No retry, reassessment, editing, batch restart or unused-budget transfer.',
        success_scope='Two selected development controls only. Not stability, blind holdout, natural task, original15 or product qualification.',
        failure_decision='Reject sufficiency of the competing-scope audit on these controls; retain omissions and wrong rationales, do not silently filter or add synonym prompts.',
        success_decision='Only permits considering an opt-in integrated identity and broader controls; the current production router still rejects the new schema.',
        natural_path=dict(generation_slots=2, review_edit_fresh_slots=3,
            implemented_product_path=False, live_budget_verified=False,
            product_limits_unchanged=True))
    return base.freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id)


class DiagnosticSender:
    """Own only this frozen two-call experiment's ledger, never product routing.

    Reuse the real ordinal/receipt transport. Reserve before IO; identity-matching
    complete usage can settle even when receipt validation subsequently fails.
    Unknown usage remains reserved. No retry and no callback chooses a model.
    """
    def __init__(self, provider, plan, clock):
        require_role_provider(provider, 'review')
        self.provider, self.plan, self.clock = provider, plan, clock
        self.calls = self.tokens = self.reserved_tokens = 0
        self.stopped = False
        self.attempts = []

    def __call__(self, prepared):
        if self.stopped:
            raise ValueError('competition_sender_stopped')
        self.clock.before_send()
        limits = self.plan['budget']
        remaining = limits['max_active_seconds'] - self.clock()
        ceiling = base.size(prepared)
        raw = base.validate_request(prepared, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)
        if (self.calls >= limits['max_calls'] or self.calls >= len(self.plan['cells'])
                or hashlib.sha256(raw).hexdigest() != self.plan['cells'][self.calls]['request_sha256']
                or remaining <= 0 or ceiling > 64000
                or prepared.max_tokens != limits['per_request_output']
                or prepared.timeout_s != limits['per_request_seconds']
                or self.tokens + self.reserved_tokens + ceiling + prepared.max_tokens > limits['max_tokens']):
            self.stopped = True
            raise ValueError('competition_budget_or_request')
        issued = replace(prepared, timeout_s=min(prepared.timeout_s, remaining),
            metadata={**prepared.metadata, 'competition_diagnostic': EXPERIMENT})
        sha = hashlib.sha256(base.validate_request(issued,
            transport_id=base.REVIEW_MODEL_TRANSPORT_ID)).hexdigest()
        reservation = ceiling + prepared.max_tokens
        self.calls += 1
        self.reserved_tokens += reservation
        attempt = dict(ordinal=self.calls, role='review', model='glm-5.3',
            request_sha256=sha, status='started')
        self.attempts.append(attempt)
        response = None
        old = self.provider.last_exchange
        try:
            require_role_provider(self.provider, 'review')
            response = self.provider.chat_at_ordinal(issued, ordinal=self.calls, role='review')
            exchange = self.provider.last_exchange
            if (exchange is None or exchange is old or exchange.response is not response
                    or exchange.issued_request != issued or exchange.receipt_request_sha256 != sha
                    or not isinstance(response, ChatResponse)
                    or (response.provider, response.model) != ('zhipu', 'glm-5.3')):
                raise ValueError('competition_fresh_receipt_required')
            if (response.usage.input_tokens > ceiling or response.usage.output_tokens > issued.max_tokens
                    or self.clock() >= limits['max_active_seconds']):
                raise ValueError('competition_response_budget')
            attempt['status'] = 'completed'
            return exchange
        except BaseException as error:
            self.stopped = True
            attempt['status'] = 'failed'
            if response is None:
                response = getattr(error, 'observed_response', None)
            raise
        finally:
            if isinstance(response, ChatResponse) and (response.provider, response.model) == ('zhipu', 'glm-5.3'):
                self.tokens += response.usage.input_tokens + response.usage.output_tokens
                self.reserved_tokens -= reservation
                attempt.update(input_tokens=response.usage.input_tokens,
                               output_tokens=response.usage.output_tokens)


def expected_findings(wire, cell, inputs):
    # Test labels never enter the request or change the returned review.
    if wire.verdict != 'needs_revision' or sorted(i.block for i in wire.issues) != cell['host_only_expected_issue_blocks']:
        raise ValueError('competition_unexpected_findings')
    if cell['host_only_scope_audit_required']:
        text = inputs.source.blocks[3][1]
        start = text.index(OMITTED)
        end = start + len(OMITTED)
        # Accept a unique anchored subspan or a broader claim; do not force
        # this test's exact phrase segmentation into the model's audit grammar.
        matching = [c for c in wire.scope_checks if c.claim.block == 4
                    and text.index(c.claim.exact_text) < end
                    and text.index(c.claim.exact_text) + len(c.claim.exact_text) > start]
        if not matching or any(c.resolution.cohort != 'selected' for c in matching):
            raise ValueError('competition_missing_or_wrong_audit')
        # Semantic relationships still require both full-source host judgments.


def read_completed_calls(directory):
    """Reconstruct completed experiment receipts; never a product role replay.

    Incomplete receipts remain on disk and in result accounting, but cannot
    produce a handoff. Exact frozen requests substitute for a product schema ID.
    """
    directory = Path(directory).resolve()
    files = sorted(p for p in directory.glob('call-*.json') if not p.name.startswith('call-result-'))
    variants = controls()
    if len(files) > len(variants):
        raise ValueError('competition_receipt_inventory')
    def read(path):
        resolved = path.resolve()
        if not resolved.is_relative_to(directory):
            raise ValueError('competition_receipt_path')
        return resolved.read_bytes()
    result = []
    identity = role_descriptor()['review']
    for n, path in enumerate(files, 1):
        binding = json.loads(read(path))
        if (path.name != f'call-{n:03d}.json' or type(binding.get('ordinal')) is not int
                or binding['ordinal'] != n or binding.get('role') != 'review'
                or binding.get('raw_directory') != 'review' or binding.get('state') != 'reserved_before_io'
                or any(binding.get(k) != identity[k] for k in ('provider', 'model', 'thinking_profile_id', 'transport_id'))):
            raise ValueError('competition_receipt_identity')
        model = directory / 'review'
        raw = read(model / f'request-{n:03d}.json')
        numeric = json.loads(raw)
        request = REQUEST.validate_json(raw, strict=True)
        request = replace(request, **{k: numeric[k] for k in ('temperature', 'timeout_s', 'top_p')})
        prepared = variants[n - 1][2]
        metadata = dict(request.metadata)
        if (metadata.pop('competition_diagnostic', None) != EXPERIMENT
                or not 0 < request.timeout_s <= prepared.timeout_s
                or replace(request, metadata=metadata, timeout_s=prepared.timeout_s) != prepared
                or base.validate_request(request, transport_id=base.REVIEW_MODEL_TRANSPORT_ID) != raw
                or hashlib.sha256(raw).hexdigest() != binding['request_sha256']):
            raise ValueError('competition_receipt_request')
        stream = model / f'stream-{n:03d}'
        reserved = json.loads(read(stream / 'reservation.json'))
        terminal = json.loads(read(stream / 'result.json'))
        response_raw = read(model / f'response-{n:03d}.json')
        response = base.RESPONSE.validate_json(response_raw)
        ended = json.loads(read(directory / f'call-result-{n:03d}.json'))
        if (type(reserved.get('ordinal')) is not int or reserved['ordinal'] != n
                or reserved.get('state') != 'reserved_before_io'
                or reserved.get('stream_tool_arguments') is not True
                or any(reserved.get(k) != binding[k] for k in ('request_sha256', 'transport_id', 'model', 'thinking_profile_id'))
                or terminal.get('state') != 'complete' or terminal.get('transport_id') != binding['transport_id']
                or (response.provider, response.model) != ('zhipu', 'glm-5.3')
                or ended.get('state') != 'complete'
                or any(ended.get(k) != v for k, v in binding.items() if k != 'state')
                or ended.get('response_sha256') != hashlib.sha256(response_raw).hexdigest()
                or any(type(ended.get(k)) is not int or ended[k] != getattr(response.usage, k)
                       for k in ('input_tokens', 'output_tokens'))):
            raise ValueError('competition_receipt_completion')
        result.append(dict(binding=binding, request=request, response=response, completed=True))
    expected = {f'call-result-{n:03d}.json' for n in range(1, len(files) + 1)}
    if {p.name for p in directory.glob('call-result-*.json')} != expected:
        raise ValueError('competition_receipt_orphan')
    return result


def observe(factory, directory, plan, *, event_source, adjudicate=base.wait_reviews,
            before_send=lambda: None):
    base.require_execution_event_source(plan, event_source)
    variants = controls()
    if (plan['sequence'] != list(KEYS) or plan['cells'] != [c for c, *_ in variants]
            or plan['role_calls'] != {'glm-5.3': 2, 'glm-5.3-flash': 0}):
        raise ValueError('competition_frozen_controls')
    clock = base.DevelopmentHostClock(directory, max_host_seconds=plan['max_host_seconds'])
    send = DiagnosticSender(factory('diagnostic').reviewer, plan, clock)
    result = dict(experiment=EXPERIMENT, diagnostic_accepted=False, stages=[],
        product_admitted=False, original15_qualified=False, historical_initial_inputs=0)
    try:
        for cell, inputs, prepared in variants:
            before_send()
            arm = Path(directory) / cell['key']
            arm.mkdir(exist_ok=False)
            base.write_new_json(arm / 'source.json', dict(input_json=inputs.data_json,
                report=inputs.source.report, synthetic_report=cell['synthetic_report']))
            exchange = send(prepared)
            base.write_new_json(arm / 'request.json', json.loads(base.validate_request(
                exchange.issued_request, transport_id=base.REVIEW_MODEL_TRANSPORT_ID)))
            base.write_new_json(arm / 'response.json', base.public_response(json.loads(base.RESPONSE.dump_json(exchange.response))))
            raw = base.tool_result(exchange.issued_request, exchange)
            _, wire, journal = prototype.validate(raw, inputs)
            stage = dict(stage='initial', report=inputs.source.report, journal=journal)
            base.write_new_json(arm / 'stage.json', stage)
            bound = dict(plan_sha256=base.canonical_sha(plan), key=cell['key'], stage='initial',
                response_sha256=base.sha(arm / 'response.json'), report_sha256=base.digest(stage['report']),
                request_sha256=exchange.receipt_request_sha256)
            base.write_new_json(arm / 'review-required.json', dict(binding=bound,
                stage_sha256=base.stage_identity(stage), scope='Judge the complete full review, every correction and scope audit against all sources. Reject missing/incorrect scope coverage in a disputed claim. The report is unrepaired; report_assessment must be null.'))
            submitted = clock.adjudicate(arm / 'review-required.json',
                plan['budget']['max_active_seconds'] - clock(), adjudicate)
            base.write_new_json(arm / 'host-reviews.json', submitted)
            accepted = previous.validate_reviews(submitted, stage, bound, plan, event_source)
            result['stages'].append(dict(key=cell['key'], binding=bound, host_accepted=accepted,
                verdict=wire.verdict, score=wire.score))
            if not accepted:
                raise ValueError('competition_host_rejected')
            expected_findings(wire, cell, inputs)
            if clock() >= plan['budget']['max_active_seconds']:
                raise ValueError('competition_active_deadline')
            before_send()
        result['diagnostic_accepted'] = True
    except BaseException as error:
        result['error_type'] = type(error).__name__
        code = getattr(error, 'code', None) or (str(error) if isinstance(error, ValueError) else None)
        if isinstance(error, ValidationError):
            code = 'competition_schema_validation'
            result['validation_errors'] = error.errors(include_input=False, include_context=False, include_url=False)
        if isinstance(code, str) and re.fullmatch('[a-z_]{1,100}', code):
            result['error_code'] = code
    finally:
        result.update(calls=send.calls, known_tokens=send.tokens,
            unknown_reserved_tokens=send.reserved_tokens, attempts=send.attempts, timing=clock.summary())
        previous.close_result(directory, result)
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
