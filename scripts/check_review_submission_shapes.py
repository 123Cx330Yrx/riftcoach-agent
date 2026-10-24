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


def audit_recovery_boundary():
    """Test the existing recovery consumer before building a new candidate.

    Positional data cannot be substituted for the old wire contract: passing
    it verbatim loses issue enumeration; projecting first changes raw identity.
    These are offline proposal inputs, not repaired historical model outputs.
    """
    pair = json.loads((ROOT/'data/evaluation/results/golden_block_buffered_pair_result_eadb930.json').read_text(encoding='utf-8'))
    dataset = json.loads((ROOT/'data/evaluation/datasets/golden_native_product_attribution_controls_v1.json').read_text(encoding='utf-8'))
    _, _, source = load_controls()
    spec = dataset['cases'][0]
    inputs = review.native.build_inputs(replace(source, report=spec['report'], user_utterance=dataset['user_utterance']))
    original = pair['cases'][0]['response']['tool_calls'][0]['arguments']
    independent = {key: original[key] for key in ('reviews', 'score', 'verdict')}
    packed = pack(independent)
    packed['score'] = 'invalid'  # An eligible malformed-field reassessment.
    raw = compact(packed)
    projected = unpack(packed)
    expected = review.native.prior_issues(projected)
    assert len(expected) == 1
    observations = []
    for label, previous_raw in [('unchanged_positional_raw', raw), ('named_projection_as_raw', compact(projected))]:
        prepared = review.request(inputs, previous_raw=previous_raw, diagnostics={'errors': ['score']})
        body = json.loads(prepared.messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])
        observations.append(dict(path=label, expected_issues=len(expected), actual_issues=len(body['previous_issues']),
            preserves_original_raw_identity=body['previous_raw_sha256'] == digest(raw),
            enumerated_issues_equal=body['previous_issues'] == expected))
    assert observations[0]['actual_issues'] == 0 and observations[0]['preserves_original_raw_identity']
    assert observations[1]['actual_issues'] == 1 and not observations[1]['preserves_original_raw_identity']
    preserved = []
    issue_row = next(i for i, row in enumerate(packed['reviews']) if row[1])
    for label, malformed in [('null', None), ('text', 'malformed finding'), ('bad_source', {'source_ids': 'invalid'})]:
        changed = deepcopy(packed)
        changed['score'] = independent['score']  # Isolate the malformed opinion.
        changed['reviews'][issue_row][1] = malformed
        mapped = unpack(changed)
        opinions = review.native.prior_issues(mapped)
        assert len(opinions) == 1 and opinions[0]['issue'] == malformed
        assert mapped['reviews'][issue_row]['issues'] == malformed
        try:
            review.validate(compact(mapped), inputs)
        except ValueError:
            pass
        else:
            raise AssertionError('malformed proposal accepted as a review')
        preserved.append(label)
    return dict(evidence_kind='offline_existing_recovery_consumer_probe', original_raw_sha256=digest(raw),
        observations=observations, malformed_opinions_preserved_by_projection=preserved,
        decision='not_a_drop_in_replacement_do_not_open_live_candidate',
        sdk_probe_performed=False, sdk_probe_skip_reason='existing_consumer_incompatibility_decides_against_direct_replacement',
        live_requests=0, production_admitted=False,
        limitations=['A separate representation-aware recovery adapter could be designed, but has not been implemented.',
                    'No conclusion about model reliability, semantic coverage or latency follows from projection.',
                    'Existing object-based recovery is not claimed broken by these unsupported positional inputs.'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recovery-boundary', action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit_recovery_boundary() if args.recovery_boundary else audit(),ensure_ascii=False,indent=2))
