"""Offline original15 inventory using the same dual-policy Runtime candidate.

No sender, labels in requests, credentials, qualification or execution grant.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from app.evaluation import role_qualification as frozen, sol_review_contract as candidate
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import digest
from app.runtime.composition import RuntimeCompositionRoot
from scripts import review_duty_composition as duty, review_duty_direct_patch as direct
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.review_necessity_candidate import NECESSITY_POLICY
from scripts.review_completion_necessity_candidate import COMPLETION_NECESSITY_POLICY

ROOT = candidate.ROOT


def audit():
    root = RuntimeCompositionRoot.from_directories(skills_root=candidate.ASSETS/'skills',
        prompt_programs_root=candidate.ASSETS/'prompt_programs', coach_contract=candidate.CONTRACT)
    manifest = root.prompt_program_catalog.get('recent-form-review-coach').manifest
    cases, aliases = frozen.frozen_cases()
    rows = []
    for cell, source in cases:
        inputs = duty.TimedDocumentWorkflow.build_inputs(source)
        if (digest(inputs.data_json) != cell['input_sha256']
                or digest(source.report) != cell['report_sha256']):
            raise ValueError('sol_original15_frozen_input_changed')
        requests = {}
        for name in duty.DUTIES:
            request = candidate.make_request(inputs, name)
            base = direct.review_request(inputs, name)
            policy = NECESSITY_POLICY if name == 'facts' else COMPLETION_NECESSITY_POLICY
            if (request.messages[0].content != base.messages[0].content+policy
                    or request.messages[1:] != base.messages[1:] or request.tools != base.tools):
                raise ValueError('sol_original15_full_input_changed')
            context = request.metadata[candidate.CONTEXT]
            candidate.validate_business(visible(json_value(request)), context)
            if candidate.request_identity(request) != (candidate.REVIEW_PROVIDER, candidate.REVIEW_MODEL):
                raise ValueError('sol_original15_review_identity')
            requests[name] = dict(request_sha256=candidate.request_sha(request),
                input_ceiling=frozen.size(request), timeout_s=request.timeout_s,
                max_output_tokens=request.max_tokens)
        rows.append(dict(key=cell['key'], expected_initial=cell['expected_initial'],
            dataset_sha256=cell['manifest_sha256'], input_sha256=cell['input_sha256'],
            report_sha256=cell['report_sha256'], initial_requests=requests,
            fresh_request_sha256=None, fresh_binding='requires_actual_applied_report', completed=False))
    counts = {label: sum(r['expected_initial'] == label for r in rows) for label in ('accept', 'reject')}
    if counts != dict(accept=5, reject=10):
        raise ValueError('sol_original15_labels_changed')
    descriptor = candidate.CONTRACT.descriptor()
    return dict(kind='sol-dual-necessity-original15-offline-inventory-v1',
        contract_module=candidate.__name__, contract=candidate.CONTRACT.snapshot().model_dump(mode='json'),
        program_sha256=manifest.program_sha256,
        component_fingerprints=[r.model_dump(mode='json') for r in manifest.component_fingerprints],
        profile=asdict(candidate.REVIEW_PROFILE), response_mode=candidate.RESPONSE_MODE,
        review_transport=candidate.REVIEW_TRANSPORT,
        coverage_sha256=hashlib.sha256((frozen.ROOT/frozen.COVERAGE).read_bytes()).hexdigest(),
        policies={k:descriptor[k] for k in ('necessity_policy_sha256', 'completion_policy_sha256')},
        cases=rows, aliases=aliases, label_counts=counts, labels_sent_to_model=False,
        initial_request_count=len(rows)*2,
        fixed_report_review_slots_if_all_cases_match_labels=counts['accept']*2+counts['reject']*4,
        fixed_report_inventory_is_not_natural_generation=True,
        natural_task_budget={k:descriptor[k] for k in ('max_calls', 'total_tokens',
            'execution_timeout_s', 'request_timeout_s', 'max_input_tokens', 'max_output_tokens',
            'generation_logical_calls', 'review_logical_calls', 'transport_retries')},
        provider_calls=0, key_reads=0, new_host_tasks=0, new_qualification=0, qualified=False,
        execution_ready=False, execution_authorized=False, production_admitted=False,
        publication_allowed=False, semantic_approval=False,
        blockers=['Inventory is not an executable original15 evaluation or live semantic result.',
            'Actual applied report and same-report fresh evidence are required per rejected case.',
            'Independent review and concrete paid scope remain to be prepared.',
            'Familiar original15 is not a holdout or a natural generation evaluation.',
            'Product publication, DB/API/UI consumption and five-call budget remain unproven.'],
        audit_source_sha256=digest(Path(__file__).read_text(encoding='utf-8')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.resolve().is_relative_to(ROOT/'data/runs'):
        raise ValueError('offline_inventory_outside_runs_required')
    result = audit()
    if args.output is not None:
        write_new_json(args.output.resolve(), result)
    print(json.dumps(dict(cases=len(result['cases']), initial_requests=result['initial_request_count'],
        provider_calls=0, key_reads=0, qualified=False, execution_ready=False), ensure_ascii=True))


if __name__ == '__main__':
    main()
