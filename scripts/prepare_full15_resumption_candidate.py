"""Prepare complete original15 candidate inputs offline, never execute them.

All original cases remain in the inventory. A proposed ten-case diagnostic
contains the two disputes, paired controls and six unresolved edit categories.
This is not an authorized/executable paid plan or a qualification manifest.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from app.evaluation import document_review_qualification as old
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from scripts import report_contrast_review as candidate
from scripts.report_document_workflow import DocumentReviewWorkflow

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'full15-resumption-candidate-preparation-v1'
DIAGNOSTIC = ('attribution:1', 'scope:3', 'claim-scope:1', 'claim-scope:4',
    'claim-scope:6', 'scope:4', 'observed:2', 'observed:3', 'observed:4', 'observed:5')
SOURCE_FILES = tuple(dict.fromkeys((*old.SOURCE_FILES,
    'scripts/report_block_keyed_editor.py', 'scripts/report_contrast_review.py',
    'scripts/prepare_full15_resumption_candidate.py')))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(root=ROOT):
    rows, artifacts = [], {}
    for cell, source in old.frozen_cases(root=root)[0]:
        inputs = DocumentReviewWorkflow.build_inputs(source)
        original = DocumentReviewWorkflow.make_request(inputs)
        request = candidate.ContrastDocumentWorkflow.make_request(inputs)
        if candidate.baseline_request(request) != original:
            raise ValueError('resumption_baseline_changed')
        raw = validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)
        path = cell['key'].replace(':', '-') + '/initial-request.json'
        artifacts[path] = raw
        rows.append(dict(key=cell['key'], report_sha256=sha(source.report.encode()),
            input_sha256=sha(inputs.data_json.encode()), original_initial_request_sha256=sha(
                validate_request(original, transport_id=REVIEW_MODEL_TRANSPORT_ID)),
            candidate_initial_request_sha256=sha(raw), input_ceiling=size(request),
            policy_sha256=sha(request.messages[0].content.encode()),
            host_only_expected_initial=cell['expected_initial'],
            selected_for_proposed_diagnostic=cell['key'] in DIAGNOSTIC))
    if len(rows) != 15 or not set(DIAGNOSTIC) <= {r['key'] for r in rows}:
        raise ValueError('resumption_inventory')
    selected = [r for r in rows if r['key'] in DIAGNOSTIC]
    needs_edits = sum(r['host_only_expected_initial'] == 'reject' for r in selected)
    roles = {'glm-5.3': len(selected) + needs_edits, 'glm-5.3-flash': needs_edits}
    costs = sum(count * (Decimal(64000) * old.CONTRACT.pricing_profiles['zhipu', model].input_cost_per_million
        + Decimal(32768) * old.CONTRACT.pricing_profiles['zhipu', model].output_cost_per_million)
        / 1_000_000 for model, count in roles.items())
    return dict(kind=VERSION, execution_ready=False, execution_authorized=False,
        paid_plan_frozen=False, provider_calls=0, new_qualification=0,
        production_admitted=False, original15_qualified=False, historical_reviews_reused=False,
        teaching_candidate=candidate.VERSION, editor_candidate=candidate.editor.VERSION,
        source_sha256={path: sha((root / path).read_bytes()) for path in SOURCE_FILES},
        cells=rows, proposed_diagnostic_sequence=list(DIAGNOSTIC),
        artifact_sha256={path: sha(raw) for path, raw in artifacts.items()},
        proposed_budget=dict(max_calls=sum(roles.values()), role_calls=roles,
            max_tokens=sum(roles.values()) * 96768, max_active_seconds=sum(roles.values()) * 300,
            max_host_seconds=86400, per_request_output=32768, per_request_seconds=300,
            estimated_uncached_cny=str(costs), hard_billing_cap=False),
        proposed_stop_rule='Semantic rejection/disagreement stops dependent stages of that case, '
            'continues independent cases. Any identity/source/native/checkpoint/protocol/transport/'
            'budget/availability failure stops the whole batch. No retry/reassessment/restart.',
        acceptance='Real full-source native dual reviews, four report flags when accepted, '
            'fresh pass>=85 without material false or missed findings; no Host labels to Provider.',
        unknowns=['Examples are a testable teaching hypothesis, not proven diagnosis or semantic fix.',
            'Keyed selectors preserve offline addressing, not proven real-model protocol reliability.',
            'Actual new edit/fresh requests depend on new accepted initial responses and new draft.',
            'Executable runner/checkpoint/handoff/strict replay/native preflight and exact CI remain required.',
            'This proposal is not authority to buy calls, reopen old runs or automatically run original15.']), artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    manifest, artifacts = prepare()
    args.directory.mkdir(parents=True, exist_ok=False)
    for path, raw in artifacts.items():
        output = args.directory / path
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('xb') as file:
            file.write(raw)
    raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode() + b'\n'
    with (args.directory / 'preparation.json').open('xb') as file:
        file.write(raw)
    print(json.dumps(dict(cases=len(manifest['cells']), provider_calls=0,
        execution_ready=False, preparation_sha256=sha(raw),
        proposed_budget=manifest['proposed_budget']), ensure_ascii=False))


if __name__ == '__main__':
    main()
