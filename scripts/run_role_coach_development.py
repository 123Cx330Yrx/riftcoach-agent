"""One bounded real role-application DEVELOPMENT run; no product admission.

Default preview uses frozen local sources without credentials, network or run
writes. --execute requires clean exact-HEAD public CI and a fresh run ID. It
records development evidence only; run_native_coach_product stays closed.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
from datetime import datetime
import hashlib
from pathlib import Path
import subprocess
from types import SimpleNamespace

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import candidate_identity, summarize_role_calls
from app.harness.run_ids import normalize_run_id
from app.product.native_coach_composition import build_role_coach_application
from app.providers.errors import ProviderResponseError
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from scripts.native_coach_preparation import ROOT, prepare_frozen_application
from scripts.prepare_role_qualification import bounded_product_estimate
from scripts.run_golden_inference_development import verify_public_ci


LIMITS = dict(max_calls=5, total_tokens=401920, execution_timeout_s=900, max_revisions=1)
NON_QUALIFICATION = dict(production_admitted=False, semantic_approval=False,
    original_15_qualified=False, actual_product_task_qualified=False)


def load_role_settings(env_file):
    from dotenv import dotenv_values
    from app.providers.config import load_zhipu_settings
    settings = load_zhipu_settings(dotenv_values(env_file))
    # Preserve credentials, base URL and timeout; only the model roles differ.
    return replace(settings, model='glm-5.3-flash'), replace(settings, model='glm-5.3')


def require_unchanged_checkout(head):
    current = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip()
    if current != head or dirty:
        raise ValueError('role_development_checkout_changed_after_ci')


class FirstRequestBoundFactory:
    """Reject content drift before the first real transport can reserve/send."""
    def __init__(self, delegate):
        self.delegate, self.descriptor = delegate, delegate.descriptor
        self.expected = None
        self.matched = False
        self._used = False

    def __call__(self, run_id):
        if self._used or self.expected is None:
            raise ValueError('role_development_prepared_request_required')
        self._used = True
        outer = self
        delegate = self.delegate(run_id)

        class BoundProvider:
            def __getattr__(self, name):
                return getattr(delegate, name)

            def chat(self, request):
                if not outer.matched:
                    metadata = dict(request.metadata)
                    budget = metadata.pop('coach_budget_contract', None)
                    if (budget != 'coach-bounded-review-v2'
                            or request.timeout_s > outer.expected.timeout_s
                            or replace(request, timeout_s=outer.expected.timeout_s, metadata=metadata) != outer.expected):
                        raise ProviderResponseError(provider='zhipu', code='role_development_first_request_changed')
                    outer.matched = True
                return delegate.chat(request)

        return BoundProvider()


def preview_settings():
    return tuple(SimpleNamespace(model=model, base_url='https://open.bigmodel.cn/api/paas/v4')
        for model in ('glm-5.3-flash', 'glm-5.3'))


def source_projection_time(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value is not None and (not isinstance(value, datetime) or value.utcoffset() is None):
        raise ValueError('role_development_source_now_requires_timezone')
    return value


def prepare(args, *, settings):
    descriptor = ROLE_COACH_CONTRACT.descriptor()
    if any(descriptor[k] != v for k, v in LIMITS.items()):
        raise ValueError('role_development_shared_budget_changed')
    factory = FirstRequestBoundFactory(RunScopedRoleReceiptedProviderFactory(
        generator_settings=settings[0], reviewer_settings=settings[1], transport_root=args.output_root / 'transport'))
    source_now = source_projection_time(getattr(args, 'source_now', None))
    prepared = prepare_frozen_application(builder=build_role_coach_application,
        contract=ROLE_COACH_CONTRACT, provider_factory=factory,
        output_root=args.output_root, run_id=args.run_id, now=source_now)
    factory.expected = prepared.first_request
    raw = validate_request(prepared.first_request, transport_id=CAPACITY_TRANSPORT_ID)
    identity = candidate_identity()
    plan = dict(experiment='actual-role-coach-development-v1', run_id=args.run_id,
        source_scope='frozen_ShowMaker_development_not_current_meta', source_now=prepared.source_now.isoformat(),
        candidate_identity=identity, candidate_sha256=digest(compact(identity)),
        first_request_sha256=hashlib.sha256(raw).hexdigest(), first_input_ceiling=prepared.first_input_ceiling,
        shared_budget=dict(LIMITS, sdk_retries=0), reservation_estimate=bounded_product_estimate(),
        first_request_normalization='Only a shorter timeout and the fixed Coach budget metadata are allowed.',
        evidence_scope='One development application run, not original-15 qualification or independent quality evidence.',
        product_execution_enabled=False, **NON_QUALIFICATION)
    # Stable approval identity excludes later execution mode / HEAD / CI fields.
    plan['preparation_plan_sha256'] = digest(compact(plan))
    return prepared, factory, raw, plan


def summarize_calls(directory):
    summary = summarize_role_calls(directory)
    prices = ROLE_COACH_CONTRACT.pricing_profiles
    by_model = {}
    for (_, model), price in prices.items():
        rows = [c for c in summary['calls'] if c['model'] == model]
        known = [c for c in rows if c['usage'] is not None]
        input_tokens = sum(c['usage']['input_tokens'] for c in known)
        output_tokens = sum(c['usage']['output_tokens'] for c in known)
        cost = (Decimal(input_tokens) * price.input_cost_per_million
            + Decimal(output_tokens) * price.output_cost_per_million) / 1_000_000
        unknown = sum(c['usage'] is None for c in rows)
        by_model[model] = dict(reserved_calls=len(rows), completed_calls=sum(c['completed'] for c in rows),
            input_tokens=input_tokens, output_tokens=output_tokens, unknown_usage_calls=unknown,
            known_usage_estimated_uncached_cny=str(cost),
            total_estimated_uncached_cny=None if unknown else str(cost))
    known_cost = sum(Decimal(c['known_usage_estimated_uncached_cny']) for c in by_model.values())
    revision = [c for c in summary['calls'] if c['role'] == 'revision']
    return dict(summary, accounting_status='partial' if summary['unknown_usage_calls'] else 'known_usage',
        by_model=by_model, known_usage_estimated_uncached_cny=str(known_cost),
        total_estimated_uncached_cny=None if summary['unknown_usage_calls'] else str(known_cost),
        cost_scope='Uncached estimate of observed usage; unknown calls are excluded, not free.',
        revision_exercised=bool(revision), revision_completed=any(c['completed'] for c in revision),
        real_generation_included=any(c['role'] == 'generation' and c['completed'] for c in summary['calls']))


def _summary_without_result(value):
    return {k: v for k, v in value.items() if k != 'result'}


def run(args):
    execute = bool(getattr(args, 'execute', False))
    args.output_root = Path(args.output_root).resolve()
    run_id = args.run_id or 'role-development-preview'
    if normalize_run_id(run_id) != run_id:
        raise ValueError('role_development_run_id_invalid')
    args.run_id = run_id
    if not execute:
        _, _, raw, plan = prepare(args, settings=preview_settings())
        plan.update(mode='preview', head_sha=None, provider_requests=0)
        request_output = getattr(args, 'request_output', None)
        if request_output is not None:
            with Path(request_output).open('xb') as stream:
                stream.write(raw)
        print(compact(plan))
        return plan

    if (run_id == 'role-development-preview' or not run_id.startswith('role-development-')
            or not args.ci_run or args.env_file is None
            or getattr(args, 'source_now', None) is None
            or not getattr(args, 'approval_plan_sha', '')):
        raise ValueError('role_development_execution_arguments_required')
    if getattr(args, 'request_output', None) is not None:
        raise ValueError('role_development_execute_uses_reserved_request_output')
    # Compare the concrete preview before CI network, credentials or run writes.
    args.source_now = source_projection_time(args.source_now)
    _, _, _, preflight_plan = prepare(args, settings=preview_settings())
    if preflight_plan['preparation_plan_sha256'] != args.approval_plan_sha:
        raise ValueError('role_development_approved_preparation_mismatch')
    # The public verifier requires clean HEAD and all three successful jobs.
    # No credentials are loaded and no development run is claimed before it.
    head = verify_public_ci(args.ci_run)
    for kind in ('observations', 'reports', 'transport'):
        if (args.output_root / kind / run_id).exists():
            raise FileExistsError('role_development_run_already_exists')
    directory = args.output_root / 'observations' / run_id
    directory.mkdir(parents=True, exist_ok=False)
    outcome = dict(status='failed', run_id=run_id, head_sha=head, ci_run=args.ci_run,
        mode='development', report_available=False, first_request_matched=False,
        declared_approved_preparation_plan_sha256=args.approval_plan_sha, **NON_QUALIFICATION)
    factory = None
    try:
        prepared, factory, raw, plan = prepare(args, settings=load_role_settings(args.env_file))
        plan.update(mode='development', head_sha=head, ci_run=args.ci_run)
        with (directory / 'first-request.json').open('xb') as stream:
            stream.write(raw)
        write_new_json(directory / 'plan.json', plan)
        if plan['preparation_plan_sha256'] != args.approval_plan_sha:
            raise ValueError('role_development_loaded_preparation_changed')
        require_unchanged_checkout(head)
        if candidate_identity() != plan['candidate_identity']:
            raise ValueError('role_development_candidate_changed_after_plan')
        result = prepared.app.review_by_puuid(prepared.request, puuid='frozen-observation', routing_region='asia',
            game_name='DK ShowMaker', tag_line='KR1', run_id=run_id,
            memory_context_binding=prepared.memory, publication_context=prepared.context)
        manifest = prepared.publication.read(prepared.context)
        pending = prepared.publication.read_pending_snapshot(prepared.context)
        outcome.update(status=result.publication_status.value,
            application_publication_status=result.publication_status.value,
            report_available=result.output.report is not None,
            report_sha256=manifest.report.sha256 if manifest.report else None,
            evidence_bundle_digest=manifest.bundle.bundle_digest, pending_snapshot_run_id=pending.run_id,
            result=result.model_dump(mode='json'))
    except BaseException as error:
        outcome.update(status='cancelled' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'failed',
            error_type=type(error).__name__)
    finally:
        outcome['first_request_matched'] = factory.matched if factory is not None else False
        try:
            outcome.update(summarize_calls(args.output_root / 'transport' / run_id))
        except (ValueError, OSError, KeyError, TypeError):
            # Broken evidence cannot be interpreted as zero consumption or pass.
            outcome.update(status='cancelled' if outcome['status'] == 'cancelled' else 'failed',
                accounting_status='invalid_receipts', reserved_calls=None, completed_calls=None,
                unknown_usage_calls=None, known_usage_estimated_uncached_cny=None,
                total_estimated_uncached_cny=None, by_model=None, revision_exercised=None,
                revision_completed=None, real_generation_included=None)
        write_new_json(directory / 'result.json', outcome)
    print(compact(_summary_without_result(outcome)))
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--run-id', default='')
    parser.add_argument('--ci-run', default='')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--request-output', type=Path)
    parser.add_argument('--source-now', help='Required for execute: reuse the exact preview source_now ISO timestamp.')
    parser.add_argument('--approval-plan-sha', default='',
        help='Required for execute: preparation_plan_sha256 from the fixed-time, intended-run preview.')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'data/runs/role_development')
    args = parser.parse_args()
    result = run(args)
    if args.execute and result['status'] != 'published':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
