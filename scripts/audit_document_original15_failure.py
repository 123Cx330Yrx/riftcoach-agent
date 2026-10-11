"""Read-only forensic comparison of the closed document original15 batch."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT/'data/evaluation/results/golden_document_original15_result_20261008.json'

def sha(value):
    return hashlib.sha256(value).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    sealed = json.loads(PUBLIC.read_bytes())
    values = sealed['public_json_contents']
    sources = {key:values[key.replace(':','-')+'/source.json']
        for key in ('claim-scope:1','claim-scope:4','claim-scope:3','attribution:1')}
    inputs = {key:json.loads(value['input_json']) for key,value in sources.items()}
    reference = inputs['claim-scope:1']
    shared = ('facts_and_provenance','generation_facts','deterministic_source_facts','knowledge','user_utterance')
    assert all(all(data[k]==reference[k] for k in shared) for data in inputs.values())
    blocks = {key:{b['block']:b['text'] for b in data['source_index']['blocks']}
        for key,data in inputs.items()}
    assert blocks['claim-scope:1'][4] == blocks['attribution:1'][4]
    assert [n for n in blocks['claim-scope:1'] if blocks['claim-scope:1'][n]!=blocks['attribution:1'][n]] == [14]
    initial = values['attribution-1/initial.json']['journal']['parsed_review']
    assert [(i['block'],i['category']) for i in initial['issues']] == [(14,'unsupported_comparison'),(4,'fact_error')]
    request = values['transport/attribution-1/review/request-001.json']
    policy = request['messages'][0]['content']
    rule = '不把未写出的全称、因果或长期含义补成作者断言'
    advisory_rule = '不要把仅可选的措辞改善升级为issues'
    assert rule in policy and advisory_rule in policy
    assert blocks['attribution:1'][4] in request['messages'][1]['content']
    assert blocks['attribution:1'][13] in request['messages'][1]['content']
    primary = values['attribution-1/primary-initial-review.json']
    independent = values['attribution-1/independent-initial-review.json']
    assert primary['accepted'] is False and independent['accepted'] is True
    assert primary['defects'][0]['kind'] == 'false_positive'
    facts = reference['facts_and_provenance']['facts']
    full = facts['facts:recent_aggregate']['win_loss_comparison']
    mid_win = Decimal(str(facts['role:MIDDLE:win:damage_per_min']['mean']))
    mid_loss = Decimal(str(facts['role:MIDDLE:loss:damage_per_min']['mean']))
    full_gap = Decimal(str(full['wins']['damage_per_min']))-Decimal(str(full['losses']['damage_per_min']))
    mid_gap = mid_win-mid_loss
    assert full_gap == Decimal('695.42') and mid_gap == Decimal('669.235')
    matches = reference['generation_facts']['matches']
    wins = [Decimal(str(m['damage_per_min'])) for m in matches if m['win']]
    losses = [Decimal(str(m['damage_per_min'])) for m in matches if not m['win']]
    raw_full_gap = sum(wins)/len(wins)-sum(losses)/len(losses)
    raw_composition_change = raw_full_gap-mid_gap
    assert raw_composition_change.quantize(Decimal('.01'),rounding=ROUND_HALF_UP) == Decimal('26.18')
    receipts = sealed['execution_result']['cases']
    assert [r['key'] for r in receipts[:3]] == ['claim-scope:1','claim-scope:4','claim-scope:3']
    assert all(r['task_outcome'] and r['reviewer_quality'] for r in receipts[:3])
    def check_public(value):
        if isinstance(value,dict):
            assert not ({'api_key','access_token','authorization'} & set(value))
            assert value.get('reasoning_content') is None
            for child in value.values(): check_public(child)
        elif isinstance(value,list):
            for child in value: check_public(child)
    check_public(values)
    result = dict(schema_version='document-original15-failure-audit-v1',provider_requests=0,
        public_seal_sha256=sha(PUBLIC.read_bytes()),
        shared_source_fields_equal=list(shared),same_block4=True,
        changed_blocks_between_correct_and_attribution=[14],
        complete_report_and_existing_rules_delivered=True,
        policy_sha256=sha(policy.encode()),
        full_damage_gap_display=str(full_gap),middle_damage_gap=str(mid_gap),
        raw_full_damage_gap=str(raw_full_gap),
        pooled_gap_minus_middle_gap=str(raw_composition_change),
        true_damage_attribution_error_detected=True,
        primary_accepted=False,independent_accepted=True,dual_acceptance=False,
        primary_classification='false_positive_from_unsupported_universal_reading',
        independent_classification='broad_mean_direction_claim_requires_metric_restriction',
        interpretation_disagreement_preserved=True,
        accepted_prefix_keys=[r['key'] for r in receipts[:3]],
        failure_key='attribution:1',unexecuted_count=11,
        decision='Document presentation alone has not met the complete fifteen-control quality gate. Do not register it or repeat this batch. Preserve the existing full-context standard and both reviews; first distinguish genuine unresolved meaning from optional specificity using actual context, prior boundary evidence and existing runtime mechanisms.',
        causal_claims_proven=False,review_controls_qualified=False,production_admitted=False)
    if args.output:
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,ensure_ascii=False,sort_keys=True,indent=2)
            stream.write('\n')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    main()
