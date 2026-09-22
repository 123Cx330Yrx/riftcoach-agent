"""Offline lossless representation spike, not a live candidate or JSON repair.

Use committed public submissions and complete sources. Malformed old parameters
are rejected, never converted to a successful result. No Provider is imported.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from app.evaluation import golden_native_buffered_block_review as review
from app.evaluation.golden_review_experiment import compact, digest
from scripts.check_native_claim_scope import load_controls

ROOT = Path(__file__).resolve().parents[1]


def pack(value):
    wire = review.IndependentReview.model_validate(value, strict=True)
    return dict(score=wire.score, verdict=wire.verdict, reviews=[
        [row.block, [i.model_dump(mode='json') for i in row.issues],
         [a.model_dump(mode='json') for a in row.advisories]] for row in wire.reviews])


def unpack(value):
    if not isinstance(value, dict) or set(value) != {'reviews', 'score', 'verdict'}:
        raise ValueError('shape_top_level')
    if not isinstance(value['reviews'], list):
        raise ValueError('shape_rows')
    rows=[]
    for row in value['reviews']:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError('shape_row_arity')
        rows.append(dict(block=row[0], issues=row[1], advisories=row[2]))
    # Full type/source/inventory validation belongs to the unchanged validator.
    return dict(value, reviews=rows)


def audit():
    read=lambda name:json.loads((ROOT/name).read_text(encoding='utf-8'))
    pair=read('data/evaluation/results/golden_block_buffered_pair_result_eadb930.json')
    dataset=read('data/evaluation/datasets/golden_native_product_attribution_controls_v1.json')
    _,_,source=load_controls()
    rows=[]
    for case,spec in zip(pair['cases'],dataset['cases'],strict=True):
        arguments=case['response']['tool_calls'][0]['arguments']
        # Explicitly select the already implemented independent-phase fields
        # for this proposal comparison. The historical old contract stays failed.
        independent={k:arguments[k] for k in ('reviews','score','verdict')}
        request=replace(source,report=spec['report'],user_utterance=dataset['user_utterance'])
        inputs=review.native.build_inputs(request)
        expected,_,_=review.validate(compact(independent),inputs)
        packed=pack(independent)
        reconstructed=unpack(json.loads(compact(packed)))
        assert reconstructed == independent
        actual,_,_=review.validate(compact(reconstructed),inputs)
        assert actual == expected
        rejected=[]
        for fault in ('merged_rows','missing_row','duplicate_block','wrong_order','bad_block_type','unknown_source'):
            bad=deepcopy(packed)
            if fault == 'merged_rows': bad['reviews'][0].extend(bad['reviews'].pop(1))
            elif fault == 'missing_row': bad['reviews'].pop()
            elif fault == 'duplicate_block': bad['reviews'][-1][0]=1
            elif fault == 'wrong_order': bad['reviews'].reverse()
            elif fault == 'bad_block_type': bad['reviews'][0][0]='1'
            else:
                findings=[i for r in bad['reviews'] for i in r[1]+r[2]]
                findings[0]['source_ids']=[999999]
            try: review.validate(compact(unpack(bad)),inputs)
            except ValueError: rejected.append(fault)
            else: raise AssertionError(f'unsafe shape accepted: {fault}')
        rows.append(dict(id=case['id'],input_sha256=digest(inputs.data_json),report_sha256=digest(request.report),
            original_independent_characters=len(compact(independent)),positional_characters=len(compact(packed)),
            complete_roundtrip_equal=True,issue_and_advisory_payload_equal=True,rejected_faults=rejected))
    failure=read('data/evaluation/results/golden_buffered_phase_failure_da06b5a.json')
    try: review.native.strict_json(failure['raw_arguments'])
    except ValueError: malformed_original_still_rejected=True
    else: raise AssertionError('malformed original accepted')
    return dict(evidence_kind='offline_representation_feasibility_only',cases=rows,
        malformed_original_still_rejected=malformed_original_still_rejected,
        live_requests=0,live_candidate_implemented=False,production_admitted=False,
        limitations=['No model reliability or latency claim.',
            'Explicit reassessment provenance/mapping is not yet implemented for positional rows.',
            'Request schema and actual five-call product path still require verification before any real trial.',
            'Historical failed outputs remain failed; roundtrip is not retroactive qualification.'])


if __name__ == '__main__':
    print(json.dumps(audit(),ensure_ascii=False,indent=2))
