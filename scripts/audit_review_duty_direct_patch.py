"""Zero-provider feasibility evidence for reviewer-authored literal patches."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_coarse_source_projection import resolve_refs
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.review_bound_qualification import frozen_cases
from app.evaluation.source_patch_editor import report_inputs
from scripts import audit_correction_consumption as prior
from scripts import review_duty_direct_patch as direct
from scripts import review_duty_composition as duty

ROOT = Path(__file__).resolve().parents[1]


def audit():
    requests = []
    for case, source in frozen_cases()[0]:
        inputs = duty.TimedDocumentWorkflow.build_inputs(source)
        rows = {}
        for stage in ('initial', 'fresh'):
            for name in duty.DUTIES:
                request = direct.review_request(inputs, name, stage)
                assert request.messages[1:] == duty.review_request(inputs, name, stage).messages[1:]
                try:
                    timing.request_bytes(request)
                except ValueError:
                    pass
                else:
                    raise AssertionError('unregistered direct patches admitted by old transport')
                rows[f'{name}-{stage}'] = dict(request_sha256=duty.request_sha(request), input_ceiling=size(request))
        requests.append(dict(key=case['key'], report_sha256=digest(source.report),
            complete_sources_unchanged=True, requests=rows))

    # A new authored fixture, never the failed real response with repaired keys.
    inputs, wire = prior.synthetic_coach_case()
    passing = compact(dict(score=95, verdict='pass', issues=[], advisories=[], issue_resolutions=[], repairs=[]))
    computed = resolve_refs(inputs, [31])[0]['value']['cohorts']
    counts = {key: {side: len(computed[key][side]) for side in ('wins', 'losses')}
        for key in ('selected', 'MIDDLE')}
    assert counts == {'selected': {'wins': 2, 'losses': 3}, 'MIDDLE': {'wins': 2, 'losses': 2}}
    cases = (
        ('narrow_supported', prior.CORRECT + '中单胜负两组各2局。', 'author_supported'),
        ('widened_sample', prior.CORRECT + '两口径各仅2局。', 'author_wrong_scope'),
        ('wrong_number', prior.CORRECT.replace('2.50', '9.50'), 'author_wrong_number'),
        ('unsupported_cause', prior.CORRECT + '因此减少早死必然导致失败。', 'author_unsupported_cause'),
    )
    witnesses = []
    for key, after, label in cases:
        value = deepcopy(wire.model_dump(mode='json'))
        value['repairs'] = [dict(issue_ids=[1], edits={'block_4': [dict(
            before=prior.BEFORE, after=after, reason='OFFLINE author-written mechanism witness.')]})]
        proposals = [direct.bind(inputs, 'facts', compact(value)), direct.bind(inputs, 'completion', passing)]
        result = direct.preview(inputs, proposals)
        assert result.report == inputs.source.report.replace(prior.BEFORE, after)
        assert result.journal['operations'][0]['after'] == after
        revised = report_inputs(inputs, result.report)
        assert all(result.journal['fresh_request_sha256'][name] == duty.request_sha(
            direct.review_request(revised, name, 'fresh')) for name in duty.DUTIES)
        assert not result.journal['semantic_approval'] and not result.journal['native_acceptance_verified']
        witnesses.append(dict(key=key, author_label=label, literal_replacement_preserved=True,
            untouched_bytes_preserved=True, actual_full_fresh_bound=True,
            preview_sha256=digest(result.report), semantic_approval=False))
    return dict(version=direct.VERSION, kind='OFFLINE-authored-feasibility-not-model-result',
        provider_calls=0, new_host_tasks=0, new_qualification=0, execution_ready=False,
        execution_authorized=False, production_admitted=False,
        complete_request_audit=requests, authored_witnesses=witnesses, source_cohort_counts=counts,
        decision='Select only for offline feasibility; remove a second paraphrasing step, not semantic review.',
        fixed_report_request_count=4, natural_task_request_count=6, current_product_request_limit=5,
        product_budget_compatible=False, product_budget_change_authorized=False,
        limitations=[
            'Initial reviewers must now author exact repairs; old opinions do not satisfy the new contract.',
            'Wrong or incomplete reviewer patches remain possible and are not detected semantically by this program.',
            'Overlapping patches are rejected even if identical; nonoverlap does not establish compatibility.',
            'Actual initial and complete-draft native acceptance, transport, shared budget and cancellation are not integrated.',
            'Full initial policy quality, patch output size and real fresh quality are unmeasured.',
            'Six natural-task calls exceed five; no silent budget expansion or skipped duty/fresh.'],
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
            'scripts/review_duty_direct_patch.py', 'scripts/audit_review_duty_direct_patch.py',
            'scripts/review_duty_composition.py', 'scripts/report_block_keyed_editor.py',
            'scripts/audit_correction_consumption.py')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output.is_relative_to(ROOT / 'data/runs'):
        raise ValueError('offline_audit_outside_runs_required')
    result = audit()
    write_new_json(output, result)
    print(json.dumps(dict(output=str(output), provider_calls=0,
        request_count=len(result['complete_request_audit']) * 4), ensure_ascii=True))
