"""Offline view audit: issue IDs/hashes do not prove readable allegation meaning."""
from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_review_experiment import digest
from scripts.native_contract_options import body, editor_request, _replace


def project_review(raw, inputs, *, mode, previous_raw=None):
    payload, proposal, _ = native.validate(raw, inputs, previous_raw=previous_raw)
    if payload.verdict != 'needs_revision':
        raise ValueError('identity_requires_revisable_review')
    if mode not in ('locator_only', 'without_suggestion', 'complete'):
        raise ValueError('identity_unknown_projection')
    rows = []
    for number, issue in enumerate(proposal.issues, 1):
        row = issue.model_dump(mode='json')
        if mode == 'locator_only':
            row = {'block': issue.block}
        elif mode == 'without_suggestion':
            del row['suggested_correction']
        rows.append(dict(issue_id=number, **row))
    return dict(review_sha256=digest(raw), issues=rows)


def projected_request(inputs, raw, *, mode, previous_raw=None):
    """Diagnostic only. Complete original report/sources; existing EditorOutput.

    No host text is relabelled as a precise claim, paraphrased, or oracle-filled.
    """
    base = editor_request(inputs, raw, previous_raw=previous_raw)
    data = body(base)
    view = project_review(raw, inputs, mode=mode, previous_raw=previous_raw)
    data['proposed_review'] = {'issues': view['issues']}
    policy = base.messages[0].content + (
        '\n诊断视图中的issue_id由host预先分配，逐项对应完整原评估。'
        '旧意见可能部分未显示；review_sha256绑定host保留的原评估，而不是展示视图。'
        'block仅定位原段，不代表精确断言或已证实的错误。')
    return _replace(base, data, base.response_contract, policy,
                    'offline_issue_adjudicating_editor')
