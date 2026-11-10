"""Read-only comparison of failed and adjacent passing requests with today's workflow.

Uses a pinned public seal, never a model call, new Host judgment or old-run mutation.
Acceptance here describes structural parsing only, not repaired model behavior.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation.document_review_timing_adapter import request_bytes
from app.evaluation.golden_review_experiment import compact
from app.evaluation.source_patch_editor import report_inputs
from scripts.report_timed_document_workflow import TimedDocumentWorkflow as Workflow
from scripts.run_full15_resumption_candidate import selected_controls

ROOT = Path(__file__).resolve().parents[1]
SEAL = 'data/evaluation/results/golden_document_full15_time600_result_20261010.json'
SEAL_SHA = '30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576'
CASES = (('claim-scope:4', 'initial', 'both_rejected'),
         ('scope:4', 'initial', 'primary_independent_disagreement'),
         ('scope:3', 'final', 'both_rejected'),
         ('claim-scope:1', 'initial', 'both_accepted'),
         ('claim-scope:3', 'final', 'both_accepted'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audit():
    raw = (ROOT/SEAL).read_bytes()
    if sha(raw) != SEAL_SHA:
        raise ValueError('readiness_historical_seal_changed')
    sealed = json.loads(raw)
    public = sealed['public_json_contents']
    controls = {cell['key']: inputs for cell, _, inputs, _ in
                selected_controls(timing_mode='time600')[1]}
    rows = []
    for key, stage, recorded in CASES:
        prefix = key.replace(':', '-') + '/' + stage + '/'
        old = public[prefix+'issued-request.json']
        report = public[prefix+'stage.json']['report']
        inputs = report_inputs(controls[key], report)
        current = Workflow.make_request(inputs)
        # The old budget wrapper added this exact marker before transport.
        # No prompt, source, schema or parameter is normalized away here.
        projected = json.loads(request_bytes(replace(current, metadata={**current.metadata,
            'coach_budget_contract':'coach-bounded-review-v2'})))
        differences = sorted(k for k in set(old) | set(projected) if old.get(k) != projected.get(k))
        payload = public[prefix+'response.json']['tool_calls'][0]['arguments']
        _, _, journal = Workflow.validate_review(compact(payload), inputs)
        hosts = public[prefix+'host-reviews.json']
        accepted = {role:hosts[role]['stage_assessment']['accepted'] for role in ('primary','independent')}
        expected = {'primary': recorded != 'both_rejected', 'independent':recorded == 'both_accepted'}
        if accepted != expected or journal['semantic_approval'] is not False:
            raise ValueError('readiness_recorded_assessment_changed')
        rows.append(dict(key=key, stage=stage, recorded_outcome=recorded,
            original_file_sha256={prefix+n:sealed['original_file_sha256'][prefix+n] for n in
                ('issued-request.json','response.json','stage.json','host-reviews.json')},
            historical_principal_ids={r:hosts[r]['stage_assessment']['reviewer'] for r in accepted},
            recorded_host_acceptance=accepted,
            recorded_defects={r:hosts[r]['stage_assessment']['defects'] for r in accepted},
            same_complete_model_request=(old == projected), changed_request_fields=differences,
            current_structural_validator_accepts_old_response=True,
            semantic_approval=journal['semantic_approval'], new_host_assessment=False,
            shared_request_sha256=sha(compact(projected).encode('utf-8')) if not differences else None))
    if (ROOT/SEAL).read_bytes() != raw:
        raise ValueError('readiness_historical_seal_mutated')
    sources = ('scripts/audit_full15_repair_readiness.py','scripts/report_timed_document_workflow.py',
        'scripts/report_contrast_review.py','scripts/report_block_keyed_editor.py',
        'scripts/report_document_workflow.py','scripts/full_chain_execution.py',
        'app/evaluation/document_review_timing_adapter.py')
    return dict(kind='OFFLINE-full15-repair-readiness-v1', seal=SEAL, seal_sha256=SEAL_SHA,
        cases=rows, source_sha256={p:sha((ROOT/p).read_bytes()) for p in sources},
        failed_contexts_with_changed_model_input=sum(not r['same_complete_model_request'] for r in rows[:3]),
        failed_contexts_with_new_structural_rejection=0,
        new_semantic_repair_evidence=False, full15_paid_proposal_status='withdrawn',
        execution_authorized=False, provider_calls=0, new_host_tasks=0, new_qualification=0,
        limits=['Request equality excludes neither report text nor source nor policy nor schema nor sampling parameters.',
            'Only the known budget metadata marker is added to a prepared request for comparison.',
            'Same request does not imply deterministic future output; stochastic success would not prove a repair.',
            'Historical Host opinions are cited, not reissued or certified by this audit.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    if output.resolve() != output or output.is_relative_to(ROOT/'data/runs'):
        raise ValueError('readiness_output_inside_run')
    value = audit()
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(cases=len(value['cases']),
        failed_contexts_with_changed_model_input=value['failed_contexts_with_changed_model_input'],
        new_semantic_repair_evidence=False, provider_calls=0)))
