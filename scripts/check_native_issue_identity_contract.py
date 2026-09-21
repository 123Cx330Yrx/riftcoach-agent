"""Reproduce why locator/suggestion deletion cannot certify issue meaning."""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from scripts.check_native_contract_options import actual_case, assert_complete
from scripts.issue_identity_contract import project_review, projected_request
from scripts.run_native_editor_pair import ROOT, read


def witnesses():
    req, saved = actual_case(3)
    inputs = native.build_inputs(req)
    raw = saved['responses'][0]['content']
    block = inputs.source.blocks[5][1]
    assert '将所选全部 5 局（包括辅助局）合并计算后，胜局与败局的平均补刀/分钟也基本持平。' in block
    assert '中单胜局均值 8.805 与败局均值 9.01 基本持平' in block
    value = native.strict_json(raw)
    issue = deepcopy(value['issues'][0])
    issue['explanation'] = '本段中的补刀比较不准确，见建议指出的比较范围。'
    true = dict(issue, suggested_correction='修正五局合并比较：胜局8.805、败局约6.45，并非基本持平。')
    false = dict(issue, suggested_correction='将四场中单胜败补刀均值基本持平改为存在显著差距。')
    rows = []
    for issues, expected in [([true, false], ['apply', 'withdraw']), ([false, true], ['withdraw', 'apply'])]:
        text = compact(dict(value, issues=issues))
        native.validate(text, inputs)
        rows.append(dict(raw=text, review_sha256=digest(text), expected_host_only=expected,
            projected={mode: project_review(text, inputs, mode=mode) for mode in
                       ('locator_only', 'without_suggestion', 'complete')}))
    return req, raw, rows


def run():
    req, raw, counter = witnesses()
    inputs = native.build_inputs(req)
    measurements = []
    for mode in ('locator_only', 'without_suggestion', 'complete'):
        request = projected_request(inputs, raw, mode=mode)
        assert_complete(request, inputs)
        wire = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        measurements.append(dict(mode=mode, input_ceiling=size(request),
            request_sha256=hashlib.sha256(wire).hexdigest(), report_and_sources_complete=True))
    for mode in ('locator_only', 'without_suggestion'):
        assert counter[0]['projected'][mode]['issues'] == counter[1]['projected'][mode]['issues']
        assert counter[0]['projected'][mode]['review_sha256'] != counter[1]['projected'][mode]['review_sha256']
    assert counter[0]['projected']['complete']['issues'] != counter[1]['projected']['complete']['issues']
    return dict(schema_version='native-issue-view-audit-v2',
        evidence_kind='analyst_constructed_information_loss_witness_not_model_result',
        provider_calls=0, input_sha256=digest(inputs.data_json), report=req.report,
        original_review_raw=raw, views=measurements, same_block_suggestion_only_allegations=counter,
        prior_same_block_witness=read(ROOT/'data/evaluation/results/golden_native_locator_identity_counterexample_v1.json'),
        decision='reject_projection_as_general_semantics_preserving_editor_contract',
        cause='Original contract permits allegation scope in suggested_correction; deletion cannot guarantee readable per-issue meaning.',
        limits=['Opaque review hashes differ; complete inputs are not byte-identical.',
            'Constructed allegations are not new model failures. The original real pair is unchanged.',
            'A complete view preserves text, but the real full-opinion response still contained a false positive.',
            'Original native validation and security/source/reassessment checks remain in force.'],
        semantic_approval=False, production_admitted=False, paid_candidate_eligible=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = run()
    write_new_json(args.output, value)
    print(compact(dict(path=str(args.output), decision=value['decision'], provider_calls=0)))
