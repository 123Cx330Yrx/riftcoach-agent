"""Offline original15 request inventory; no sender or semantic qualification.

Dataset labels stay in evaluation metadata. Fresh request identities cannot be
predicted before the actual new draft exists. This audit grants no live access.
"""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation import role_qualification as frozen
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.evaluation.natural_duty_contract import CONTRACT, make_request, request_sha, request_identity
from app.product.natural_duty_candidate import ASSETS
from app.runtime.composition import RuntimeCompositionRoot
from scripts import review_duty_composition as duty, review_duty_direct_patch as direct

ROOT = Path(__file__).resolve().parents[1]


def audit():
    root = RuntimeCompositionRoot.from_directories(skills_root=ASSETS/'skills',
        prompt_programs_root=ASSETS/'prompt_programs', coach_contract=CONTRACT)
    manifest = root.prompt_program_catalog.get('recent-form-review-coach').manifest
    cases, aliases = frozen.frozen_cases()
    rows = []
    for cell, source in cases:
        inputs = duty.TimedDocumentWorkflow.build_inputs(source)
        if (digest(inputs.data_json) != cell['input_sha256']
                or digest(source.report) != cell['report_sha256']):
            raise ValueError('natural_duty_frozen_input_changed')
        requests = {}
        for name in duty.DUTIES:
            request = make_request(inputs, name)
            base = direct.review_request(inputs, name)
            if request.messages != base.messages or request.tools != base.tools:
                raise ValueError('natural_duty_full_input_changed')
            if request_identity(request) != ('zhipu', 'glm-5.3'):
                raise ValueError('natural_duty_review_model_changed')
            requests[name] = dict(request_sha256=request_sha(request),
                input_ceiling=frozen.size(request), timeout_s=request.timeout_s,
                max_output_tokens=request.max_tokens)
        rows.append(dict(key=cell['key'], expected_initial=cell['expected_initial'],
            dataset_sha256=cell['manifest_sha256'], input_sha256=cell['input_sha256'],
            report_sha256=cell['report_sha256'], initial_requests=requests,
            fresh_request_sha256=None, fresh_binding='requires_actual_applied_report',
            completed=False))
    counts = {label: sum(r['expected_initial'] == label for r in rows) for label in ('accept', 'reject')}
    if counts != dict(accept=5, reject=10):
        raise ValueError('natural_duty_original15_labels_changed')
    descriptor = CONTRACT.descriptor()
    return dict(kind='natural-duty-original15-offline-inventory-v1', provider_calls=0,
        new_host_tasks=0, new_qualification=0, qualified=False, execution_ready=False,
        execution_authorized=False, production_admitted=False, publication_allowed=False,
        contract=CONTRACT.snapshot().model_dump(mode='json'), program_sha256=manifest.program_sha256,
        component_fingerprints=[r.model_dump(mode='json') for r in manifest.component_fingerprints],
        coverage_sha256=hashlib.sha256((frozen.ROOT/frozen.COVERAGE).read_bytes()).hexdigest(),
        cases=rows, aliases=aliases, label_counts=counts, initial_request_count=len(rows)*2,
        fixed_report_review_slots_if_all_cases_match_labels=counts['accept']*2+counts['reject']*4,
        fixed_report_inventory_is_not_natural_generation=True,
        natural_task_budget={k:descriptor[k] for k in ('max_calls', 'total_tokens',
            'execution_timeout_s', 'request_timeout_s', 'max_input_tokens', 'max_output_tokens')},
        blockers=[
            'Automatic opinion/correction correctness and semantic compatibility are unverified.',
            'The current adapter rejects publication even after two fresh passes.',
            'Fresh evidence must bind the actual applied report; none exists in this inventory.',
            'Familiar original15 controls cannot establish holdout or natural-generation quality.',
            'A future paid evaluation needs its own concrete scope and authorization.'],
        audit_source_sha256=digest(Path(__file__).read_text(encoding='utf-8')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.resolve().is_relative_to(ROOT/'data/runs'):
        raise ValueError('offline_audit_outside_runs_required')
    result = audit()
    if args.output is not None:
        write_new_json(args.output.resolve(), result)
    print(json.dumps(dict(cases=len(result['cases']), initial_requests=result['initial_request_count'],
        provider_calls=0, qualified=False, execution_ready=False), ensure_ascii=True))


if __name__ == '__main__':
    main()
