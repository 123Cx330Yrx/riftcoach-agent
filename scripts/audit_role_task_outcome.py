"""Offline observations from immutable public evidence; never issues model IO.

The rejected initial review and accepted tail are deliberately combined only
for deterministic replay. This is not a new execution or a qualification row.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_role_clarity import RoleClarityReviewWorkflow as Workflow
from app.evaluation.golden_stream_bridge import REQUEST, RESPONSE, validate_request
from app.evaluation.role_qualification import ROOT, prepare_qualification, frozen_cases
from app.evaluation.role_task_outcome import prepare_observation, assess_task_outcome
from app.harness.steps import EvaluationVerdict, RevisionRequest

RESULTS = ROOT / 'data/evaluation/results'
EXPORTS = {
    'clarity': ('golden_role_clarity_result_v1.json', '2884776f4f866e67738d43bdb9f4966ec37400486ccb1e6706a0f59aee8dcdd9'),
    'tail': ('golden_role_containment_result_v1.json', 'cb2991fc122b38ba9ef7cca3940b0e983dee41f1698741f2766eb0c22c17e2cb'),
}


def load_exports():
    result = {}
    for name, (file, expected) in EXPORTS.items():
        raw = (RESULTS / file).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('task_outcome_historical_export_changed')
        result[name] = json.loads(raw)
    return result


def public_call(export, prefix, ordinal, origin, journal_path=None):
    contents = export['public_json_contents']
    record = contents[f'{prefix}/call-{ordinal:03d}.json']
    path = f'{prefix}/{record["raw_directory"]}'
    wire = contents[f'{path}/request-{ordinal:03d}.json']
    request = REQUEST.validate_json(json.dumps(wire, ensure_ascii=False), strict=True)
    request = replace(request, **{k: wire[k] for k in ('temperature', 'timeout_s', 'top_p')})
    response = RESPONSE.validate_json(json.dumps(contents[f'{path}/response-{ordinal:03d}.json'], ensure_ascii=False))
    if journal_path:
        # Public export sorts object keys, while the retained raw tool arguments
        # preserve their original order for the journal/editor reconstruction.
        arguments = json.loads(contents[journal_path]['raw'])
        if arguments != dict(response.tool_calls[0].arguments):
            raise ValueError('task_outcome_public_journal_changed')
        response = replace(response, tool_calls=(replace(response.tool_calls[0], arguments=arguments),))
    return dict(binding=record, request=request, response=response,
        artifact_sha256={f'{origin}/{name}': sha for name, sha in export['original_file_sha256'].items()
            if name.startswith(prefix + '/')})


def restore_public_order(key, calls):
    """Recover builder ordering, then require the original request-byte digest.

    Sorted public JSON cannot be reserialized as the original request bytes.
    Restore only dictionary order from the unchanged builder; never replace the
    recorded hash with a new projection hash to make the receipt pass.
    """
    source = next(s for f, s in frozen_cases()[0] if f['key'] == key)
    iterator = iter(calls)
    def send(prepared):
        call = next(iterator)
        issued = call['request']
        metadata = dict(prepared.metadata)
        if 'coach_budget_contract' in issued.metadata:
            metadata['coach_budget_contract'] = issued.metadata['coach_budget_contract']
        rebuilt = replace(prepared, timeout_s=issued.timeout_s, metadata=metadata)
        raw = validate_request(rebuilt, transport_id=call['binding']['transport_id'])
        if rebuilt != issued or hashlib.sha256(raw).hexdigest() != call['binding']['request_sha256']:
            raise ValueError('task_outcome_public_request_reconstruction_failed')
        call['request'] = rebuilt
        return Exchange(rebuilt, call['response'], call['binding']['request_sha256'])
    workflow = Workflow(send)
    initial = workflow.evaluate(source)
    if initial.verdict is EvaluationVerdict.NEEDS_REVISION:
        draft = workflow.revise(RevisionRequest(source.player_summary, source.deterministic_report,
            source.knowledge, source.report, initial))
        workflow.evaluate(replace(source, report=draft.report))
    if next(iterator, None) is not None:
        raise ValueError('task_outcome_unused_public_call')
    return calls


def historical_cases():
    exports = load_exports()
    correct = [public_call(exports['clarity'], 'transport/claim-scope-1', 1, 'clarity', 'claim-scope-1/initial-journal.json')]
    combined = [public_call(exports['clarity'], 'transport/claim-scope-4', 1, 'clarity', 'claim-scope-4/initial-journal.json'),
        public_call(exports['tail'], 'transport/tail', 1, 'tail'),
        public_call(exports['tail'], 'transport/tail', 2, 'tail', 'final-journal.json')]
    return {key: restore_public_order(key, calls) for key, calls in
        [('claim-scope:1', correct), ('claim-scope:4', combined)]}


def historical_assessment(key, calls):
    """Encode previously completed full-source checks, not new model judgments."""
    observed = prepare_observation(key, calls)
    stages = []
    for stage in observed['stages']:
        rejected = key == 'claim-scope:4' and stage['stage'] == 'initial'
        source_review = (
            'Initial review found the real all-metrics universal error but added middle vision27–43; '
            'sources contain40/43/25/27. Correct direction and repair do not cancel this false range.'
            if rejected else
            'Previously completed primary and independent full-source checks accept this unchanged '
            'stage. See the immutable original review notes in the clarity/tail exports.')
        stages.append(dict(**stage, reviewer='Recorded primary and independent source assessments',
            source_review=source_review, accepted=not rejected,
            defects=[dict(kind='unsupported_explanation', detail='False middle-vision range27–43; actual25–43.')]
                if rejected else []))
    return dict(**observed['binding'], stages=stages, final_report=dict(
        report_sha256=observed['replayed']['bindings']['final_report_sha256'],
        reviewer='Recorded primary and independent full-report assessments',
        source_review=('Original correct report unchanged.' if key == 'claim-scope:1' else
            'Actual Flash edit corrects the true universal claim, omits erroneous27–43, removes only '
            'the redundant introduction and preserves the other23 original paragraphs. Final input '
            'and output bindings were checked against original receipts.'),
        facts_and_sources_correct=True, correct_content_preserved=True,
        identity_and_goal_preserved=True, true_errors_fixed=True))


def audit():
    observations = []
    for key, calls in historical_cases().items():
        result = assess_task_outcome(key, calls, historical_assessment(key, calls))
        result['provenance'] = ('historical_single_case' if key == 'claim-scope:1'
            else 'historical_initial_plus_separate_tail_diagnostic')
        observations.append(result)
    plan, _ = prepare_qualification()
    return dict(kind='role_task_outcome_offline_audit_v1', provider_requests=0,
        sources={name: dict(file=file, sha256=sha) for name, (file, sha) in EXPORTS.items()},
        original15_keys=[row['key'] for row in plan['cases']], observations=observations,
        review_controls_qualified=False, actual_product_task_qualified=False,
        production_admitted=False, execution_enabled=False,
        scope='Retrospective offline replay and separately bound host judgments. No fresh qualification or task-time proof.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        write_new_json(args.output, result)
    print(json.dumps(dict(provider_requests=0, observations=[dict(key=o['key'],
        reviewer_quality=o['reviewer_quality'], task_outcome=o['task_outcome']) for o in result['observations']],
        production_admitted=False), ensure_ascii=False))
