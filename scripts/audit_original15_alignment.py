"""Read-only original15 inventory and prospective version binding. No run/review.

Human semantic rulings live in the companion decision record. This script
recomputes arithmetic and binds evidence; it does not classify report meaning.
"""
import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

from app.evaluation import document_review_qualification as qualification
from app.evaluation import document_review_timing_adapter as timing
from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation import role_qualification as frozen
from scripts.full_chain_evidence import FullChainEvidence, ROOT, sha
from scripts.report_timed_document_workflow import TimedDocumentWorkflow as Workflow, request_sha
from scripts.run_full15_resumption_candidate import selected_controls

HISTORY = (
    ('full15', '20261010', '30f8e336d11fa2bd425434d90c37e8ce77cded74cec534a8c958fb914446f576'),
    ('remaining8', '20261011', '75c8c04dbb6f045de4e24993cae0fa28d192f510fb6726bf68ca99f494ec2bf8'),
    ('remaining4', '20261011', 'a98734911f9384bd23f1b8e76bdd47513d6024add89c6a830b3155c13351feec'),
)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def arithmetic(data):
    matches = data['generation_facts']['matches']
    facts = data['facts_and_provenance']['facts']
    metrics = ('cs_per_min', 'gold_per_min', 'damage_per_min', 'vision_score', 'deaths_before_15')
    for i, match in enumerate(matches):
        actual = facts[f'facts:recent_match:{i:02d}']
        if any(match[k] != actual[k] for k in (*metrics, 'match_id', 'role', 'win')):
            raise ValueError('alignment_source_rows_disagree')
    result = {}
    with localcontext() as ctx:
        ctx.prec = 28
        for label, rows in (('all5', matches), ('middle4', [m for m in matches if m['role'] == 'MIDDLE'])):
            result[label] = {}
            for win in (True, False):
                group = [m for m in rows if m['win'] is win]
                result[label]['wins' if win else 'losses'] = dict(
                    match_ids=[m['match_id'] for m in group], count=len(group),
                    means={k: str(sum((Decimal(str(m[k])) for m in group), Decimal(0)) / len(group)) for k in metrics})
        middle = [m for m in matches if m['role'] == 'MIDDLE']
        result['middle_pairwise_win_above_loss'] = {k: all(
            Decimal(str(w[k])) > Decimal(str(l[k])) for w in middle if w['win']
            for l in middle if not l['win']) for k in ('gold_per_min', 'damage_per_min')}
        result['damage_gap_reduction_removing_support'] = str(
            Decimal(result['middle4']['losses']['means']['damage_per_min'])
            - Decimal(result['all5']['losses']['means']['damage_per_min']))
    return result


def audit(*, verify_local_originals=False):
    rows, variants = selected_controls(timing_mode='time600')
    by_key = {r['key']: r for r in rows}
    history, cases, pins = [], {}, {}
    for stem, date, expected in HISTORY:
        seal_path = f'data/evaluation/results/golden_document_{stem}_time600_result_{date}.json'
        close_path = f'data/evaluation/results/document_{stem}_time600_close_audit_{date}.json'
        if sha(ROOT / seal_path) != expected:
            raise ValueError('alignment_historical_seal_changed')
        seal, close = read(ROOT / seal_path), read(ROOT / close_path)
        if close['seal_sha256'] != expected or seal['new_qualification'] != 0:
            raise ValueError('alignment_historical_close_binding')
        pins.update({seal_path: expected, close_path: sha(ROOT / close_path)})
        public = seal['public_json_contents']
        plan = public['plan.json']
        run = seal['execution_result']['experiment']
        if Path(run).name != run:
            raise ValueError('alignment_run_path')
        run_dir = ROOT / 'data/runs/model_comparison' / run
        if verify_local_originals:
            for name, expected_file in seal['original_file_sha256'].items():
                path = (run_dir / name).resolve()
                if not path.is_relative_to(run_dir.resolve()) or sha(path) != expected_file:
                    raise ValueError('alignment_historical_original_changed')
        for case in seal['execution_result']['cases']:
            key = case['key']
            if key in cases:
                raise ValueError('alignment_duplicate_historical_case')
            cell = next(c for c in plan['preparation_plan']['cells'] if c['key'] == key)
            if any(cell[k] != by_key[key][k] for k in ('input_sha256', 'report_sha256', 'manifest_sha256', 'expected_initial')):
                raise ValueError('alignment_original_case_changed')
            prefix = key.replace(':', '-') + '/initial/'
            response = public[prefix + 'response.json']['tool_calls'][0]['arguments']
            issued = public[prefix + 'issued-request.json']
            cases[key] = dict(seal=seal_path, execution_head=plan['execution_head'], ci_run=plan['ci_run'],
                initial_sent=True, initial_score=response['score'], initial_verdict=response['verdict'],
                status=('passed_in_own_batch' if case['semantic_accepted'] else
                    'uncertified' if not case['stages'] else 'semantic_rejection_or_disagreement'),
                certified_stages=case['stages'],
                original_policy_sha256=digest(issued['messages'][0]['content']),
                original_schema_sha256=digest(compact(issued['tools'][0]['input_schema'])))
        history.append(dict(run=run, seal=seal_path, seal_sha256=expected,
            head=plan['execution_head'], ci_run=plan['ci_run'], originals=len(seal['original_file_sha256']),
            certified_stages=len(seal['stages']), accounting=seal['accounting'],
            local_originals_verified=verify_local_originals, native_reimported=False))
    if set(cases) != set(by_key):
        raise ValueError('alignment_missing_case')

    records, facts = [], {}
    for cell, source, inputs, request in variants:
        key = cell['key']
        try:
            qualification.role_for_request(request)
        except ValueError as exc:
            rejection = str(exc)
        else:
            raise ValueError('alignment_legacy_identity_accepted')
        # A neutral schema probe is not an accepted opinion or an edit request
        # to execute; actual edits must bind the actual reviewed model output.
        _, probe, _ = Workflow.validate_review(compact(dict(score=96, verdict='pass', issues=[],
            issue_resolutions=[], advisories=[])), inputs)
        edit = Workflow.edit_request(inputs, probe)
        family = 'observed' if cell['suite'] == 'observed' else 'other'
        data = json.loads(inputs.data_json)
        facts.setdefault(family, arithmetic(data))
        records.append(dict(key=key, original_label=cell['expected_initial'],
            original_manifest_sha256=cell['manifest_sha256'],
            frozen_original_input_sha256=cell['input_sha256'], input_sha256=digest(inputs.data_json),
            report_sha256=digest(source.report), request_sha256=request_sha(request),
            source_components_sha256={k: digest(compact(v)) for k, v in data.items() if k != 'source_index'},
            policy_sha256=digest(request.messages[0].content),
            schema_sha256=digest(compact(request.tools[0].input_schema)),
            editor_policy_sha256=digest(edit.messages[0].content),
            editor_schema_sha256=digest(compact(edit.tools[0].input_schema)),
            editor_probe_is_not_business_opinion=True,
            original_policy_matches=cases[key]['original_policy_sha256'] == digest(request.messages[0].content),
            original_schema_matches=cases[key]['original_schema_sha256'] == digest(compact(request.tools[0].input_schema)),
            legacy_identity_rejection=rejection, history=cases[key]))
    if facts['other'] != facts['observed']:
        raise ValueError('alignment_match_arithmetic_disagrees')
    # Only construct a preparation descriptor. No directory or business run is created.
    base = ROOT / 'data/evaluation/results/.alignment-path-placeholders'
    session = FullChainEvidence(directory=base/'run', answers=base/'answers', observations=base/'observations')
    plan = session.prepare(root_thread_id='01a1248f-e18c-7282-92bf-7ceb2eb5dce4',
        independent_thread_id='01a12f0c-bb7c-74e3-ad92-775eefbe399a')
    source_pins = dict(plan['source_sha256'])
    source_pins['scripts/audit_original15_alignment.py'] = sha(Path(__file__))
    assets = [frozen.COVERAGE, *frozen.DATASETS.values(),
        Path('tests/fixtures/native_missing_block_reassessment.json'), Path('tests/fixtures/native_heading_recheck_failure.json')]
    combination = dict(kind='original15-time600-full-chain-prepared-v1', cases=[
        {k: v for k, v in r.items() if k != 'history'} for r in records],
        asset_sha256={p.as_posix(): sha(ROOT / p) for p in assets}, source_sha256=source_pins,
        request_timing_identity=timing.TIMED_IDENTITY,
        transports=[bridge.TIMED_REVIEW_TRANSPORT_ID, bridge.TIMED_FLASH_TRANSPORT_ID],
        policy=plan['candidate_policy'], editor=plan['candidate_editor'],
        task_budget=plan['per_case_budget'], host_policy=plan['host_review_evidence_policy'],
        author_contract=plan['author_workspace_contract'], observation_contract=plan['observation_contract'])
    counts = {s: sum(v['status'] == s for v in cases.values()) for s in
        ('passed_in_own_batch', 'semantic_rejection_or_disagreement', 'uncertified')}
    if list(counts.values()) != [10, 3, 2]:
        raise ValueError('alignment_history_counts')
    return dict(kind='OFFLINE-original15-alignment-v1', provider_calls=0, http_calls=0,
        native_tasks=0, new_qualification=0, execution_authorized=False, execution_ready=False,
        production_admitted=False, labels_rewritten=False, historical_recognition_changed=False,
        history=history, historical_file_sha256=pins, historical_case_counts=counts,
        cases=records, decimal_recomputed_facts=facts,
        prepared_combination=combination, combination_sha256=digest(compact(combination)),
        limitations=['Preparation is not qualification or authorization.',
            'Historical stages remain in three distinct batches and are not combined into admission.',
            'Arithmetic and byte binding do not adjudicate semantic disagreements.',
            'No new native final, natural generation, model edit or production consumption occurred.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-local-originals', action='store_true')
    args = parser.parse_args()
    result = audit(verify_local_originals=args.verify_local_originals)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(cases=len(result['cases']), counts=result['historical_case_counts'],
        combination_sha256=result['combination_sha256'], provider_calls=0)))
