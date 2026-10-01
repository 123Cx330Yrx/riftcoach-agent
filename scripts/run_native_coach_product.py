"""One bounded native product run using frozen ShowMaker facts and real local RAG.

Preview compiles the first request without credentials, network or run writes.
Execution stays closed pending current-composition coverage and actual product
qualification. --composition only selects an explicit offline preview.
"""
import argparse
from dataclasses import is_dataclass, replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact
from app.product.native_coach_composition import build_native_coach_application, build_role_coach_application
from app.runtime.coach_contract import NATIVE_COACH_CONTRACT, ROLE_COACH_CONTRACT
from app.runtime.receipted_provider_factory import RunScopedReceiptedProviderFactory, RunScopedRoleReceiptedProviderFactory
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import candidate_identity, summarize_role_calls
from scripts.run_golden_native_review import prepare, ROOT
from scripts.native_coach_preparation import prepare_frozen_application
from scripts.run_golden_inference_development import verify_public_ci

PRODUCT_LIVE_STATUS = 'offline_source_binding_and_attribution_review'



def reviewer_settings_from(settings):
    """Keep the authorized endpoint, credential and timeout when changing role."""
    if is_dataclass(settings):
        return replace(settings, model='glm-5.3')
    return SimpleNamespace(**{**vars(settings), 'model': 'glm-5.3'})


def run(args):
    if args.execute:
        raise ValueError('native_product_semantic_qualification_required')
    composition = getattr(args, 'composition', 'native')
    if composition not in ('native', 'flash-glm-review'):
        raise ValueError('native_product_composition_invalid')
    contract = ROLE_COACH_CONTRACT if composition == 'flash-glm-review' else NATIVE_COACH_CONTRACT
    builder = build_role_coach_application if composition == 'flash-glm-review' else build_native_coach_application
    run_id = args.run_id or 'native-product-preview'
    settings = SimpleNamespace(model='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/paas/v4')
    head = None
    if args.execute:
        if not args.run_id.startswith('native-product-'):
            raise ValueError('native_product_run_id_required')
        head = verify_public_ci(args.ci_run)
        from dotenv import dotenv_values
        from app.providers.config import load_zhipu_settings
        settings = load_zhipu_settings(dotenv_values(args.env_file))
    if composition == 'flash-glm-review':
        reviewer_settings = reviewer_settings_from(settings)
        factory = RunScopedRoleReceiptedProviderFactory(generator_settings=settings,
            reviewer_settings=reviewer_settings, transport_root=args.output_root/'transport')
    else:
        factory = RunScopedReceiptedProviderFactory(settings=settings, transport_root=args.output_root/'transport')
    prepared = prepare_frozen_application(builder=builder, contract=contract,
        provider_factory=factory, output_root=args.output_root, run_id=run_id)
    app, request = prepared.app, prepared.request
    memory, context, publication = prepared.memory, prepared.context, prepared.publication
    first, ceiling = prepared.first_request, prepared.first_input_ceiling
    plan = dict(run_id=run_id, head_sha=head, ci_run=args.ci_run, source_scope='frozen_ShowMaker_development_not_current_meta',
        composition=composition, contract=contract.snapshot().model_dump(), first_input_ceiling=ceiling,
        total_calls=5, total_tokens=401920, max_seconds=900, max_revisions=1,
        production_admitted=False, real_generation_included=args.execute, semantic_approval=False)
    first_raw = validate_request(first, transport_id=CAPACITY_TRANSPORT_ID)
    plan['first_request_sha256'] = hashlib.sha256(first_raw).hexdigest()
    plan['live_status'] = PRODUCT_LIVE_STATUS
    if composition == 'flash-glm-review':
        from scripts.prepare_role_qualification import bounded_product_estimate
        plan['candidate_identity'] = candidate_identity()
        plan['reservation_estimate'] = bounded_product_estimate()
    if getattr(args, 'request_output', None) is not None:
        # Explicit create-only inspection artifact; never a credentials file.
        with args.request_output.open('xb') as stream:
            stream.write(first_raw)
    if not args.execute:
        print(compact(plan))
        return plan
    directory = args.output_root/'observations'/run_id
    directory.mkdir(parents=True, exist_ok=False)
    write_new_json(directory/'plan.json',plan)
    outcome = dict(status='failed', semantic_approval=False, production_admitted=False)
    try:
        result = app.review_by_puuid(request, puuid='frozen-observation', routing_region='asia',
            game_name='DK ShowMaker',tag_line='KR1',run_id=run_id,memory_context_binding=memory,publication_context=context)
        manifest = publication.read(context)
        pending = publication.read_pending_snapshot(context)
        outcome.update(status=result.publication_status.value, report_available=result.output.report is not None,
            report_sha256=manifest.report.sha256 if manifest.report else None,
            evidence_bundle_digest=manifest.bundle.bundle_digest, pending_snapshot_run_id=pending.run_id,
            result=result.model_dump(mode='json'))
    except Exception as exc:
        outcome['error_type'] = type(exc).__name__  # No arbitrary private error body.
    finally:
        if composition == 'flash-glm-review':
            try:
                outcome.update(summarize_role_calls(args.output_root/'transport'/run_id))
            except (ValueError, OSError, KeyError):
                # Invalid receipts cannot become zero usage or successful work.
                outcome.update(accounting_status='invalid_receipts', unknown_usage_calls=None)
        else:
            responses = list((args.output_root/'transport'/run_id).glob('response-*.json'))
            responses_data=[json.loads(p.read_text(encoding='utf-8')) for p in responses]
            reservations=list((args.output_root/'transport'/run_id).glob('stream-*/reservation.json'))
            outcome.update(reserved_calls=len(reservations),completed_calls=len(responses),
                input_tokens=sum(r['usage']['input_tokens'] for r in responses_data),
                output_tokens=sum(r['usage']['output_tokens'] for r in responses_data),
                unknown_usage_calls=len(reservations)-len(responses))
        write_new_json(directory/'result.json',outcome)
    print(compact({k:v for k,v in outcome.items() if k != 'result'}))
    return outcome


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--composition', choices=('native', 'flash-glm-review'), default='native')
    parser.add_argument('--request-output', type=Path)
    parser.add_argument('--run-id',default='')
    parser.add_argument('--ci-run',default='')
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--output-root',type=Path,default=ROOT/'data/runs/native_product')
    run(parser.parse_args())
