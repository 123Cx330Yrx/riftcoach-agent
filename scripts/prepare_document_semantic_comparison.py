"""Build exact prospective requests, full-source materials and a costed plan.

Only public evidence is read. No network, credentials, Provider calls, old-run
mutation, fabricated response or native review is performed by preparation.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation import document_review_qualification as qualification
from app.evaluation.golden_stream_bridge import REQUEST, validate_request, TIMED_REVIEW_TRANSPORT_ID
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
from scripts import document_semantic_request as identity
from scripts import prepare_document_semantic_options as options
from scripts.report_timed_document_workflow import TimedDocumentWorkflow
from scripts.review_independence_contract import FINAL_POLICY, MODE_V2, freeze_v2_identity

ROOT = options.ROOT
VERSION = 'document-semantic-comparison-preparation-v1'
RUN_ID = 'document-semantic-comparison-20261011'
EXPECTED = ('reject', 'accept', 'reject', 'accept', 'reject')
FILES = ('scripts/document_semantic_request.py',
         'scripts/prepare_document_semantic_comparison.py',
         'scripts/document_semantic_host_task.py',
         'scripts/prepare_document_semantic_options.py',
         'scripts/document_semantic_transport.py',
         'scripts/document_semantic_comparison.py',
         'app/providers/zhipu.py', 'app/providers/zhipu_profiles.py',
         'app/providers/stream_adapter_contract.py',
         'app/providers/config.py', 'app/evaluation/golden_stream_diagnostic.py',
         'app/evaluation/golden_journal.py', 'scripts/diagnose_block_review_route.py',
         'tests/test_document_semantic_comparison.py', 'tests/test_document_semantic_execution.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_request(raw):
    value = json.loads(raw)
    request = REQUEST.validate_json(raw, strict=True)
    # Restore JSON numeric representation before exact-byte checks.
    return replace(request, **{k: value[k] for k in ('temperature', 'timeout_s', 'top_p')})


def controls(root=ROOT):
    inert = options.prepare(root)
    sources = {cell['key']: source for cell, source in qualification.frozen_cases(root=root)[0]}
    rows = []
    for index, ((path, key, stage), expected) in enumerate(zip(options.SOURCES, EXPECTED, strict=True)):
        seal_raw = (root / path).read_bytes()
        seal = json.loads(seal_raw)
        relative = key.replace(':', '-') + '/' + stage
        original = seal['public_json_contents'][relative + '/issued-request.json']
        original_request = read_request(json.dumps(original, ensure_ascii=False).encode())
        report = seal['public_json_contents'][relative + '/stage.json']['report']
        source = replace(sources[key], report=report)
        inputs = TimedDocumentWorkflow.build_inputs(source)
        rebuilt = TimedDocumentWorkflow.make_request(inputs)
        rebuilt = replace(rebuilt, timeout_s=original_request.timeout_s,
                          metadata={**rebuilt.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
        if rebuilt != original_request or json.loads(validate_request(rebuilt,
                transport_id=TIMED_REVIEW_TRANSPORT_ID)) != original:
            raise ValueError('semantic_fixed_source_request_changed')
        # Every preserved artifact is public; source/current inputs differ for
        # historical fresh stages, so retain both explicitly instead of silently
        # substituting the original erroneous report for the fixed final report.
        material = dict(original_source=seal['public_json_contents'][key.replace(':', '-') + '/source.json'],
            current_input_json=inputs.data_json, report=report,
            original_stage=seal['public_json_contents'][relative + '/stage.json'],
            original_request=original,
            initial_stage=seal['public_json_contents'][key.replace(':', '-') + '/initial/stage.json'],
            initial_request=seal['public_json_contents'][key.replace(':', '-') + '/initial/issued-request.json'],
            source_seal=path, source_seal_sha256=sha(seal_raw), source_key=key, source_stage=stage)
        for variant in identity.SUFFIXES:
            request = identity.prepare_request(rebuilt, variant)
            raw = identity.request_bytes(request)
            old = identity.baseline(request)
            if old != original_request:
                raise ValueError('semantic_full_request_changed')
            masked = json.loads(raw)
            masked['messages'][0]['content'] = '<POLICY>'
            del masked['metadata'][identity.MARKER]
            if sha(options.canonical(masked)) != inert['samples'][index]['nonpolicy_canonical_sha256']:
                raise ValueError('semantic_nonpolicy_changed')
            # Host labels/expectations remain outside Provider messages/metadata.
            row = dict(key=f'sample-{index + 1}:{variant}', variant=variant,
                source_key=key, source_stage=stage, stage=stage, expected_verdict=expected,
                request_sha256=sha(raw), report_sha256=sha(report.encode()),
                material_sha256=sha(options.canonical(material)),
                policy_sha256=sha(request.messages[0].content.encode()),
                original_issued_request_sha256=seal['original_file_sha256'][relative + '/issued-request.json'])
            rows.append((row, material, request))
    return inert, rows


def prepare(root=ROOT, *, root_thread_id, independent_thread_id):
    inert, rows = controls(root)
    # All requests are isolated reviews. No editor, generation, retry or fresh
    # dependent on this diagnostic's findings is bought by this budget.
    count = len(rows)
    price = DOCUMENT_REVIEW_COACH_CONTRACT.pricing_profiles['zhipu', 'glm-5.3']
    cost = count * (Decimal(64000) * price.input_cost_per_million
                   + Decimal(32768) * price.output_cost_per_million) / 1_000_000
    historical = json.loads((root / options.OLD).read_bytes())['public_json_contents']['plan.json']['preparation_plan']
    files = tuple(dict.fromkeys((*historical['source_sha256'], *FILES)))
    plan = dict(kind=VERSION, run_id=RUN_ID, cells=[x[0] for x in rows],
        sequence=[x[0]['key'] for x in rows], identity=identity.VERSION,
        transport_id=identity.TRANSPORT, static_preparation_sha256=sha(options.canonical(inert)),
        source_sha256={p: sha((root / p).read_bytes()) for p in files},
        source_seal_sha256={p: sha((root / p).read_bytes()) for p, _, _ in options.SOURCES},
        sdk_retries=0, labels_sent_to_model=False, execution_authorized=False,
        execution_ready=False, native_preflight_verified=False,
        runner_contract='document-semantic-comparison-run-v1',
        execution_checks=['exact-source-package','explicit-cost-authorization',
                          'clean-same-HEAD-public-CI','current-native-principals'],
        production_admitted=False,
        original15_qualified=False, new_qualification=0,
        host_review_submission_mode=MODE_V2, host_review_evidence_policy=FINAL_POLICY,
        max_host_seconds=86400,
        budget=dict(max_calls=count, role_calls={'glm-5.3': count, 'glm-5.3-flash': 0},
            max_tokens=count * 96768, max_active_seconds=count * 600,
            max_host_seconds=86400, per_request_seconds=600, per_request_output=32768,
            estimated_uncached_cny=str(cost), hard_billing_cap=False),
        recovery_dispatch_policy='Exactly one NEW_TASK per native turn; same checkpoint recovery uses MESSAGE only.',
        semantic_failure_rule='Record each full-source false finding, miss, correction defect or Host disagreement; no retry. Continue only independent comparison requests.',
        hard_failure_rule='Identity/source/native/checkpoint/protocol/transport/budget/availability failure stops all remaining requests.',
        scope='Five fixed public complete requests times three teaching suffixes; development comparison, not fresh qualification or a new complete15 workflow.',
        limitations=['No actual semantic result is implied by preparation.',
            'Single paired observations cannot establish causality or stability.',
            'Historical failed/uncertified cases are not reopened, recertified or given credit.',
            'The prospective marker and transport are not admitted by any default product entrypoint.'])
    return freeze_v2_identity(plan, root_thread_id=root_thread_id,
        primary_id=root_thread_id, independent_id=independent_thread_id), rows


def package(directory, *, root_thread_id, independent_thread_id, root=ROOT):
    plan, rows = prepare(root, root_thread_id=root_thread_id, independent_thread_id=independent_thread_id)
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    manifests = []
    for row, material, request in rows:
        arm = directory / row['key'].replace(':', '-')
        arm.mkdir()
        raw = identity.request_bytes(request)
        with (arm / 'prepared-request.json').open('xb') as handle:
            handle.write(raw)
        material_raw = options.canonical(material)
        with (arm / 'material.json').open('xb') as handle:
            handle.write(material_raw)
        manifests.append(dict(key=row['key'], request_path=arm.name + '/prepared-request.json',
            request_sha256=sha(raw), material_path=arm.name + '/material.json',
            material_sha256=sha(material_raw)))
    value = dict(preparation_plan=plan, plan_sha256=sha(options.canonical(plan)), files=manifests,
                 provider_calls=0, native_reviews=0)
    with (directory / 'plan.json').open('xb') as handle:
        handle.write(options.canonical(value))
    verify_package(directory, root=root)
    return value


def verify_package(directory, *, root=ROOT):
    directory = Path(directory)
    value = json.loads((directory / 'plan.json').read_bytes())
    plan = value['preparation_plan']
    rebuilt, rows = prepare(root, root_thread_id=plan['root_thread_id'],
        independent_thread_id=plan['review_principals']['independent']['principal_id'])
    if rebuilt != plan or value['plan_sha256'] != sha(options.canonical(plan)):
        raise ValueError('semantic_package_plan_changed')
    expected_paths = {'plan.json'}
    expected_manifests = []
    for row, material, request in rows:
        arm = row['key'].replace(':', '-')
        request_path, material_path = arm + '/prepared-request.json', arm + '/material.json'
        expected_paths.update((request_path, material_path))
        raw = (directory / request_path).read_bytes()
        if raw != identity.request_bytes(request) or (directory / material_path).read_bytes() != options.canonical(material):
            raise ValueError('semantic_package_material_changed')
        expected_manifests.append(dict(key=row['key'], request_path=request_path,
            request_sha256=sha(raw), material_path=material_path, material_sha256=sha(options.canonical(material))))
    if (value['files'] != expected_manifests or value['provider_calls'] != 0 or value['native_reviews'] != 0
            or {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()} != expected_paths):
        raise ValueError('semantic_package_inventory_changed')
    return dict(verified=True, requests=len(rows), plan_sha256=value['plan_sha256'],
                provider_calls=0, execution_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--root-thread-id')
    parser.add_argument('--independent-thread-id')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not args.root_thread_id or not args.independent_thread_id:
            parser.error('prepare requires explicit actual principal identifiers; not a connectivity assertion')
        value = package(args.directory, root_thread_id=args.root_thread_id,
                        independent_thread_id=args.independent_thread_id)
        value = {k: value[k] for k in ('plan_sha256', 'provider_calls', 'native_reviews')}
    else:
        value = verify_package(args.directory)
    print(json.dumps(value))


if __name__ == '__main__':
    main()
