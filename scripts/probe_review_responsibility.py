"""Offline information/consumer counterexamples, never a model request builder.

Problem-only output is a hypothetical responsibility change, not a projection
that may be accepted as an old review. Constructed diagnoses are analyst data.
"""
import argparse
from copy import deepcopy
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.evaluation.golden_native_issues_review import NativeIssuesReview
from app.evaluation.golden_role_clarity import RoleClarityReview

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'data/evaluation/results'
INPUTS = (
    ('golden_native_issue_view_audit_offline_v2.json',
     'b2c4d33e30a97fb4bca5ff70b08c80e2bcce2261d563b4e6fb4cece69a6b5d30'),
    ('golden_document_original15_result_20261008.json',
     'd225f75e39e850e62c7af2cefab1ec823d837e6c46fd65606e93da373d2ed4c5'),
    ('golden_document_remaining11_scan_result_20261009.json',
     '8adfa5cea9b56c063ffb0340b726c55d4c3effbfe86c54738d492f48b00c6baa'),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def without_correction(review):
    value = deepcopy(review)
    for issue in value['issues']:
        del issue['suggested_correction']
    return value


def probe():
    if not __debug__:
        raise ValueError('responsibility_probe_requires_assertions')
    loaded, hashes = [], {}
    for name, expected in INPUTS:
        raw = (RESULTS / name).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if expected is not None and sha != expected:
            raise ValueError('responsibility_probe_source_changed')
        hashes[name] = sha
        loaded.append(json.loads(raw))
    witness, original, scan = loaded
    a, b = witness['same_block_suggestion_only_allegations']
    old_a, old_b = (json.loads(row['raw']) for row in (a, b))
    plain_a, plain_b = without_correction(old_a), without_correction(old_b)
    assert plain_a == plain_b
    assert a['expected_host_only'] != b['expected_host_only']

    # A new producer could put a complete allegation in the existing explanation
    # field. These examples are hand-authored, NOT transformed model judgments.
    source = witness['report']
    targets = (
        '将所选全部 5 局（包括辅助局）合并计算后，胜局与败局的平均补刀/分钟也基本持平。',
        '中单胜局均值 8.805 与败局均值 9.01 基本持平',
    )
    assert all(text in source for text in targets)
    constructed = []
    for order in ((0, 1), (1, 0)):
        value = deepcopy(plain_a)
        for issue, index in zip(value['issues'], order, strict=True):
            issue['explanation'] = '被质疑的原文命题为“' + targets[index] + '”；指控为该范围的补刀胜败均值比较与来源冲突。'
        constructed.append(value)
    assert constructed[0] != constructed[1]
    schema = deepcopy(RoleClarityReview.model_json_schema())
    problem = schema['$defs']['Problem']
    del problem['properties']['suggested_correction']
    problem['required'].remove('suggested_correction')
    # The inherited top-level has advisories; this old witness lacks that field.
    checks = [dict(value, advisories=[]) for value in constructed]
    for value in checks:
        Draft202012Validator(schema).validate(value)
    # Both the true and false allegations remain legal shapes. This explicitly
    # disproves any claim that self-contained diagnosis implies semantic truth.
    assert len(checks[0]['issues']) == 2

    current = []
    for sealed, key, path in (
        (original, 'attribution:1', 'transport/attribution-1/review/response-001.json'),
        (scan, 'scope:3', 'scope-3/response.json'),
    ):
        files = sealed['public_json_contents']
        source = files[key.replace(':', '-') + '/source.json']
        review = files[path]['tool_calls'][0]['arguments']
        projected = without_correction(review)
        Draft202012Validator(schema).validate(projected)
        missing = []
        try:
            NativeIssuesReview.model_validate(
                {k: v for k, v in projected.items() if k != 'advisories'}, strict=True)
        except ValidationError as exc:
            missing = [list(e['loc']) for e in exc.errors(include_input=False)]
        assert missing == [['issues', i, 'suggested_correction'] for i in range(len(review['issues']))]
        assert all(old['explanation'] == new['explanation'] for old, new in
                   zip(review['issues'], projected['issues'], strict=True))
        report_sha = hashlib.sha256(source['report'].encode()).hexdigest()
        assert source.get('report_sha256', report_sha) == report_sha
        current.append(dict(key=key, report_sha256=report_sha,
            actual_review_sha256=digest(review), hypothetical_projection_sha256=digest(projected),
            issue_blocks_preserved=[i['block'] for i in projected['issues']],
            explanations_unchanged=True, current_pydantic_entry_rejections=missing))
    dependencies = (
        'app/evaluation/golden_native_issues_review.py',
        'app/evaluation/golden_semantic_review.py',
        'app/evaluation/golden_role_clarity.py',
        'app/evaluation/golden_role_notes.py',
        'app/evaluation/golden_native_partitioned_tool_review.py',
        'app/evaluation/coach_report.py',
        'app/evaluation/golden_integrated_review.py',
    )
    return dict(kind='review-responsibility-contract-counterexamples-v1',
        source_sha256=hashes, provider_calls=0, model_requests_built=0,
        validation_context=dict(pydantic_version=version('pydantic'),
            jsonschema_version=version('jsonschema'),
            current_consumer_schema_sha256=digest(NativeIssuesReview.model_json_schema()),
            hypothetical_schema_sha256=digest(schema),
            definition_source_sha256={path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
                for path in dependencies}),
        original_responses_modified=False, semantic_approval=False, qualification_credit=0,
        direct_deletion=dict(readable_problem_lists_collide=True,
            witness_expected_dispositions_differ=True, opaque_hashes_do_not_restore_meaning=True),
        prospective_producer=dict(evidence_kind='analyst_constructed_not_model_output',
            existing_explanation_can_distinguish_scopes=True, new_fields_added=0,
            issues=checks[0]['issues'], schema_accepts_allegations_with_opposite_witness_labels=True,
            semantic_labels_origin='sealed analyst witness, not recomputed source truth or new Host decisions',
            cannot_derive_complete_diagnosis_by_deleting_old_correction=True),
        current_cases=current,
        decision='Do not implement as a common repair or build a sender. Direct deletion loses meaning; '
            'a hypothetical new producer can express meaning but can still invent it. '
            'Removing correction prose leaves current attribution interpretation unchanged; '
            'scope correction uncertainty can move to editing. Existing consumers require correction intent.',
        limits=['This is a responsibility/shape counterexample, not model or Host recalibration.',
            'Hand-authored diagnoses distinguish allegations, not complete source-bound diagnosis quality.',
            'Consumer check exercises only its Pydantic entry, not full semantic/source/revision validation.',
            'No whole-task budget or runnable candidate path is proved.',
            'No automatic semantic classifier or old-result migration is provided.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = probe()
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            f.write('\n')
    print(json.dumps(dict(provider_calls=0, model_requests_built=0,
        direct_deletion_collision=True, common_repair_selected=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
