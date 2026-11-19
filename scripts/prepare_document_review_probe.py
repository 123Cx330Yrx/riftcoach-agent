"""Prepare exact offline comparison material; no execution or provider entrypoint.

Requests contain only complete report/source material and the existing policy.
Expected outcomes and historical opinions remain in the separate Host manifest.
"""
import argparse
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from app.evaluation.golden_explicit_source_projection import _unpack
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.role_qualification import frozen_cases
from app.runtime.coach_contract import BOUNDARY_EXAMPLES_COACH_CONTRACT
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE as PROFILE
from scripts import report_document_view as view
from scripts.prepare_scope_resolution_probe import SEAL, SEAL_SHA

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'document-initial-review-probe-preparation-v1'
ANCHOR = '早期死亡在胜败样本间几乎相同'
EXPLICIT = '中单早期死亡在中单胜败样本间几乎相同'
SOURCE_FILES = ('scripts/prepare_document_review_probe.py', 'scripts/report_document_view.py',
    'app/evaluation/golden_role_boundary_examples.py', 'app/evaluation/golden_coarse_source_projection.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(request):
    return validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)


def historical(public, hashes, key, inputs, baseline):
    prefix = key.replace(':', '-')
    saved = public[prefix + '/source.json']
    journal = public[prefix + '/initial-journal.json']
    transport = f'transport/{prefix}/review/'
    archived_timeout = public[transport + 'request-001.json']['timeout_s']
    if not 0 < archived_timeout <= baseline.timeout_s:
        raise ValueError('document_probe_historical_timeout')
    issued = replace(baseline, timeout_s=archived_timeout,
        metadata={**baseline.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
    raw = encoded(issued)
    if (inputs.data_json != saved['input_json'] or inputs.source.report != saved['report']
            or digest(inputs.data_json) != saved['input_sha256']
            or digest(inputs.source.report) != saved['report_sha256']
            or sha(encoded(baseline)) != hashes[prefix + '-prepared-request.json']
            or json.loads(raw) != public[transport + 'request-001.json']
            or sha(raw) != hashes[transport + 'request-001.json']
            or sha(raw) != public[transport + 'stream-001/reservation.json']['request_sha256']
            or journal['policy_sha256'] != digest(baseline.messages[0].content)
            or json.loads(journal['raw']) != public[transport + 'response-001.json']['tool_calls'][0]['arguments']):
        raise ValueError('document_probe_historical_binding')
    return dict(prepared_request_sha256=sha(encoded(baseline)), issued_request_sha256=sha(raw),
        initial_response_sha256=hashes[transport + 'response-001.json'],
        primary_accepted=public[prefix + '/initial-host.json']['accepted'],
        independent_accepted=public[prefix + '/independent-initial-review.json']['accepted'],
        comparison_scope='Exact historical input and request, not a contemporaneous control or new qualification.')


def prepare(root=ROOT):
    seal_raw = (root/SEAL).read_bytes()
    if sha(seal_raw) != SEAL_SHA:
        raise ValueError('document_probe_seal_changed')
    seal = json.loads(seal_raw)
    sources = {row['key']: source for row, source in frozen_cases(root=root)[0]}
    mixed = sources['claim-scope:3']
    if mixed.report.count(ANCHOR) != 1:
        raise ValueError('document_probe_counterfactual_anchor')
    cases = (
        ('actual-mixed', 'claim-scope:3', mixed, False, [6]),
        ('explicit-middle-error', 'claim-scope:3', replace(mixed, report=mixed.report.replace(ANCHOR, EXPLICIT, 1)), True, [4, 6]),
        ('correct-context', 'claim-scope:1', sources['claim-scope:1'], False, []),
    )
    rows, artifacts = [], {}
    for key, original_key, source, synthetic, issue_blocks in cases:
        inputs = view.Current.build_inputs(source)
        baseline, document = view.Current.make_request(inputs), view.project(inputs)
        if view.restore(document, inputs) != baseline:
            raise ValueError('document_probe_projection_changed')
        # No prior opinion, known answer, extra audit schema or hand-selected
        # paragraph is used in the actual initial-review request.
        data = _unpack(baseline)[1]
        if {'previous_review', 'previous_issues', 'accepted_review'} & data.keys():
            raise ValueError('document_probe_initial_not_fresh')
        if baseline.tools != document.tools or size(document) > 64000:
            raise ValueError('document_probe_contract_or_capacity')
        history = None if synthetic else historical(seal['public_json_contents'], seal['original_file_sha256'],
            original_key, inputs, baseline)
        marked, markers = view.document(inputs)
        if view.restore_document(marked, inputs) != source.report:
            raise ValueError('document_probe_report_loss')
        # Descriptive layout inventory, not a Markdown equivalence proof.
        layout = dict(blocks=len(markers), headings=sum(text.lstrip().startswith('#') for _, text in inputs.source.blocks),
            pipe_table_blocks=sum(text.lstrip().startswith('|') for _, text in inputs.source.blocks),
            fenced_code_lines=len(re.findall(r'^ {0,3}(?:`{3,}|~{3,})', source.report, re.M)),
            ordered_or_unordered_list_lines=len(re.findall(r'^\s*(?:[-+*]|\d+[.)])\s+', source.report, re.M)),
            inserted_labels_are_new_presentation=True, markdown_semantic_equivalence_proven=False)
        rows.append(dict(key=key, original_key=original_key, synthetic_report=synthetic,
            report_sha256=digest(source.report), input_sha256=digest(inputs.data_json),
            baseline_request_sha256=sha(encoded(baseline)), document_request_sha256=sha(encoded(document)),
            policy_sha256=digest(document.messages[0].content), schema_sha256=digest(json.dumps(
                document.tools[0].input_schema, sort_keys=True, ensure_ascii=False)),
            document_input_ceiling=size(document), output_limit=document.max_tokens, timeout_seconds=document.timeout_s,
            historical=history, layout=layout,
            host_only_expected_issue_blocks=issue_blocks,
            host_only_acceptance=('Full report pass >=85 without substantive false findings.' if not issue_blocks else
                'Find all true errors, without false findings or unsupported corrections anywhere in the complete report.'),
            host_only_minimum_targets_are_not_exhaustive_semantic_review=True))
        artifacts[f'{key}/baseline-request.json'] = encoded(baseline)
        artifacts[f'{key}/document-request.json'] = encoded(document)
        artifacts[f'{key}/source.json'] = json.dumps(dict(report=source.report, input_json=inputs.data_json),
            ensure_ascii=False, sort_keys=True).encode('utf-8')
    prices = BOUNDARY_EXAMPLES_COACH_CONTRACT.pricing_profiles['zhipu', PROFILE.model]
    cost = (Decimal(64000)*prices.input_cost_per_million + Decimal(32768)*prices.output_cost_per_million) / 1_000_000
    manifest = dict(kind=VERSION, source_seal=SEAL, source_seal_sha256=SEAL_SHA,
        execution_authorized=False, execution_ready=False, paid_plan_frozen=False, provider_calls=0,
        model_quality_proven=False, original15_qualified=False, production_admitted=False,
        model=dict(provider='zhipu', model=PROFILE.model, profile_id=PROFILE.profile_id,
            extra_body=PROFILE.extra_body(), transport=REVIEW_MODEL_TRANSPORT_ID, sdk_retries=0),
        source_sha256={p: digest((root/p).read_text(encoding='utf-8')) for p in SOURCE_FILES},
        proposed_order=[r['key'] for r in rows], cells=rows,
        artifact_sha256={p: sha(raw) for p, raw in artifacts.items()},
        budget_proposal=dict(max_calls=3, max_tokens=290304, max_active_seconds=900, max_host_seconds=86400,
            estimated_uncached_cny=str(cost*3), hard_billing_cap=False, baseline_calls=0,
            budget_kind='separate_future_diagnostic_not_product_budget_change'),
        stop_rule='First semantic, identity, source, transport, budget or Host-review failure stops. No retry or reassessment.',
        decision=dict(failure='Reject sufficiency of this presentation on the failed control; do not retry with synonymous policy.',
            all_three_accepted='Only a narrow feasibility signal. Decide matched baseline/repetition before any causal or reliability claim; no admission.',
            unknown='Transport or incomplete output is not semantic evidence; close and account unknown usage, no automatic retry.'),
        limitations=['Historical results are not same-time controls; provider sampling and backend changes are not isolated.',
            'Message boundaries, report serialization and its address instruction change together; no isolated JSON causal claim.',
            'Host labels split list grouping in these reports; unchanged raw text does not prove Markdown structure or model interpretation equivalence.',
            'These known diagnostics are not blind holdout or independent reliability samples.',
            'Model-facing request files contain no manifest labels or historical opinions.',
            'A reviewed executable route, frozen identity/authorization and passing CI are still required before paid IO.'])
    return manifest, artifacts


def export(directory):
    manifest, artifacts = prepare()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    for name, raw in artifacts.items():
        target = directory/name
        target.parent.mkdir(exist_ok=True)
        with target.open('xb') as handle:
            handle.write(raw)
    write_new_json(directory/'host-manifest.json', manifest)
    return manifest


def verify_directory(directory):
    """Read-only verification against current preparation, not live admission."""
    directory = Path(directory)
    manifest, artifacts = prepare()
    expected_names = {*artifacts, 'host-manifest.json'}
    if ({p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()} != expected_names
            or json.loads((directory/'host-manifest.json').read_bytes()) != manifest
            or any((directory/name).read_bytes() != raw for name, raw in artifacts.items())):
        raise ValueError('document_probe_packet_changed')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path)
    parser.add_argument('--verify-directory', type=Path)
    args = parser.parse_args()
    if args.output_directory and args.verify_directory:
        parser.error('choose output or verification, not both')
    manifest = (verify_directory(args.verify_directory) if args.verify_directory else
        export(args.output_directory) if args.output_directory else prepare()[0])
    print(json.dumps(dict(cells=len(manifest['cells']), provider_calls=0, execution_ready=False,
        budget_proposal=manifest['budget_proposal']), ensure_ascii=False))
