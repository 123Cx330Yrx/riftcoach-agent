"""Offline fail-closed sampling path witness; never creates a runnable identity.

Only public closed evidence is read. Local providers stop before delegation and
never return model output/usage/receipts. The direct base-budget invocation is
explicitly a component witness, not a bypass made available to any runner.
"""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_journal import write_new_json
from app.providers.errors import ProviderError
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
from app.runtime.reviewer_roles import ROLE_COMPOSITION_ID, ROLE_PROFILE_ID
from scripts.audit_document_sampling_boundary import ROOT, SEAL, canonical
from scripts.prepare_document_semantic_comparison import read_request

OUTPUT = ROOT / 'data/evaluation/results/document_sampling_reachability_audit_20261011.json'


class LocalBoundaryStop(RuntimeError):
    pass


class BudgetWitness(timing.TimedDocumentBudget):
    def _provider_for_request(self, request):
        self.locally_observed = request
        raise LocalBoundaryStop('local_stop_before_delegation')


def local_provider():
    def forbidden(request):
        raise AssertionError('provider_delegation_forbidden')
    return SimpleNamespace(provider_name='zhipu', model_name=ROLE_COMPOSITION_ID,
        thinking_profile_id=ROLE_PROFILE_ID, sdk_max_retries=0, runtime_profile=None,
        source_projection=DOCUMENT_REVIEW_COACH_CONTRACT.descriptor()['source_projection'],
        report_presentation=DOCUMENT_REVIEW_COACH_CONTRACT.descriptor()['report_presentation'],
        request_timing_identity=timing.TIMED_IDENTITY, capabilities=None, chat=forbidden)


def audit():
    raw = SEAL.read_bytes()
    seal = json.loads(raw)
    if seal['strict_replay'] is not True or not seal['result']['scan_completed']:
        raise ValueError('sampling_source_not_closed')
    rows = []
    for ordinal in range(1, 6):
        stem = f'sample-{ordinal}-expanded_examples'
        material = seal['public_json_contents'][stem + '/material.json']
        # This is the historical request's complete content, with the fresh
        # source stage explicitly retained. No original-byte hash is invented.
        request = read_request(canonical(material['original_request']))
        if timing.role_for_request(request) != 'review':
            raise ValueError('sampling_original_role_changed')
        low = replace(request, temperature=0.2)
        budget = BudgetWitness(local_provider(), clock=lambda: 0)
        try:
            budget.chat(low)
        except (ValueError, ProviderError) as error:
            rejection = error.code if isinstance(error, ProviderError) else str(error)
        else:
            raise ValueError('sampling_low_unexpectedly_reachable')
        if (rejection != 'document_identity_request_contract' or budget.calls != 0
                or budget.tokens != 0 or budget.reserved_tokens != 0
                or not budget.stopped or hasattr(budget, 'locally_observed')):
            raise ValueError('sampling_timed_predelegation_gate_changed')
        # Exercise the inherited budget normalization in isolation. Stop before
        # role selection/delegation/count/reservation; no response is fabricated.
        component = BudgetWitness(local_provider(), clock=lambda: 0)
        try:
            CoachBudgetedProvider.chat(component, low)
        except LocalBoundaryStop:
            pass
        else:
            raise ValueError('sampling_component_did_not_stop')
        observed = component.locally_observed
        if (observed.temperature != 1.0 or observed.top_p != .95
                or replace(observed, temperature=0.2) != low
                or component.calls != 0 or component.tokens != 0
                or component.reserved_tokens != 0 or not component.stopped):
            raise ValueError('sampling_component_witness_changed')
        rows.append(dict(sample=f'sample-{ordinal}', source_key=material['source_key'],
            historical_source_stage=material['source_stage'], complete_request_content_sha256=hashlib.sha256(
                canonical(material['original_request'])).hexdigest(),
            request_digest_is='canonical content, not issued bytes', timed_gate_rejection=rejection,
            attempted_calls=0, reserved_tokens=0, actual_delegations=0,
            inherited_budget_component_temperature=observed.temperature,
            component_witness='Direct base-budget body, stopped before delegation; not an executable path.'))
    if SEAL.read_bytes() != raw:
        raise ValueError('sampling_source_mutated')
    paths = ['scripts/audit_document_sampling_reachability.py', 'scripts/audit_document_sampling_boundary.py',
        'app/runtime/coach_budget.py', 'app/runtime/coach_contract.py',
        'app/evaluation/document_review_identity.py', 'app/evaluation/document_review_timing_adapter.py',
        'scripts/report_timed_document_workflow.py', 'scripts/report_document_workflow.py',
        'scripts/report_block_keyed_editor.py', 'app/evaluation/review_bound_editor.py',
        'app/providers/zhipu.py', 'app/providers/zhipu_stream_adapter.py']
    return dict(kind='document-sampling-reachability-offline-audit-v1',
        source_seal_sha256=hashlib.sha256(raw).hexdigest(), samples=rows,
        source_code_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        provider_calls=0, credential_reads=0, raw_run_read=False, network_client_constructed=False,
        execution_ready=False, production_admitted=False, new_qualification=0,
        existing_full_workflow_low_temperature_reachable=False,
        reason='Timed identity rejects low temperature before delegation; inherited shared budget '
               'also normalizes temperature back to 1.0. Local SDK expressibility is insufficient.',
        task_contract=dict(max_calls=5, total_tokens=401920, active_timeout_s=900,
            normal_path_roles=['generation', 'generation', 'review', 'revision', 'review'],
            recovery_consumes_shared_calls=True),
        limitation='No new identity, runnable workflow, generation/edit/fresh model result or Provider '
                   'parameter honoring is demonstrated. Historical fresh requests test existing review '
                   'entry gates only. An isolated candidate would need consistent request construction, '
                   'budget normalization, role/transport identity and receipt replay changes; no '
                   'production gate is relaxed and no paid screening is authorized.')


if __name__ == '__main__':
    value = audit()
    write_new_json(OUTPUT, value)
    print(json.dumps(dict(samples=len(value['samples']), provider_calls=0,
        existing_full_workflow_low_temperature_reachable=False,
        artifact_sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest())))
