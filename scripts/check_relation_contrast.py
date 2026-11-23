"""Read-only candidate/source audit; no paid entrypoint or execution authority."""
import hashlib
import json
from pathlib import Path

from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.golden_review_experiment import digest
from app.evaluation.role_qualification import frozen_cases
from scripts import report_relation_contrast as candidate
from scripts.audit_editor_responsibility import audit as historical_audit

ROOT = Path(__file__).resolve().parents[1]


def audit():
    historical = historical_audit()
    # This evidence disconfirms the previous next-action proposal. Do not replay
    # old Provider work or quietly relabel an already-rejected route as new.
    assert not historical['conclusions']['no_prior_opinion_is_sufficient']
    assert not historical['conclusions']['editor_only_change_repairs_initial_review']
    cells = []
    for case, source in frozen_cases()[0]:
        inputs = candidate.parent.ContrastDocumentWorkflow.build_inputs(source)
        original = candidate.parent.ContrastDocumentWorkflow.make_request(inputs)
        request = candidate.RelationContrastWorkflow.make_request(inputs)
        assert candidate.restore(request) == original
        assert request.messages[1:] == original.messages[1:] and request.tools == original.tools
        cells.append(dict(key=case['key'], report_sha256=digest(source.report),
            input_sha256=digest(inputs.data_json), parent_policy_sha256=digest(original.messages[0].content),
            candidate_policy_sha256=digest(request.messages[0].content),
            parent_input_ceiling=size(original), candidate_input_ceiling=size(request),
            complete_sources_and_schema_identical=True, model_observed=False))
    paths = ('scripts/report_relation_contrast.py', 'tests/test_report_relation_contrast.py',
        'scripts/check_relation_contrast.py', 'scripts/report_contrast_review.py',
        'scripts/audit_editor_responsibility.py',
        'data/evaluation/results/golden_editor_responsibility_audit_20261008.json',
        'data/evaluation/results/correction_consumption_audit_20261012.json')
    return dict(kind='OFFLINE-relation-contrast-preparation-v1', provider_calls=0, http_calls=0,
        native_tasks=0, business_submissions=0, new_qualification=0,
        execution_ready=False, production_admitted=False,
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        prior_source_edit_failure=historical['observed'],
        withdrawn_proposal='source-first replacement of complete initial review',
        reason='Existing live counterevidence and ADR0110; editor changes do not fix initial-review semantics.',
        hypothesis='A contrast separating ordinal group comparison, mean direction and causality may '
            'reduce unsupported repair inferences; this is untested, not a proven root cause.',
        intervention='Only one fictional teaching example is extended; no schema/source/model/temperature change.',
        offline_flow_scope='Scripted generation prefix, complete initial, keyed edit, complete final; '
            'one real workflow/router/budget stack, at most five simulated calls. Not Harness publication, '
            'natural generation, timed600 transport, Host native audit, or model correctness.',
        cells=cells,
        next_check='Prepare new development reports with correct reverse ordering, overlapping ranges '
            'and true comparison errors; check original full-report preservation and exact time600 '
            'paired request transport before selecting a paid scope. No old H5/V2/S8 reopen.',
        disconfirming_outcomes=['Candidate adds errors to correct controls: reject candidate.',
            'Candidate still gives wrong repair: do not iteratively append similar teaching.',
            'Both baseline and candidate pass: no evidence of improvement or mechanism causation.'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
