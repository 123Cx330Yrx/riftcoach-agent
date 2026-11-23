"""Reproducible zero-network feasibility audit; not an execution preparation."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.evaluation.review_bound_qualification import frozen_cases
from app.evaluation.source_patch_editor import report_inputs
from scripts import review_duty_composition as duty

ROOT = Path(__file__).resolve().parents[1]


def audit():
    rows = []
    for fixture, source in frozen_cases()[0]:
        inputs = duty.TimedDocumentWorkflow.build_inputs(source)
        base = duty.TimedDocumentWorkflow.make_request(inputs)
        requests = {d: duty.review_request(inputs, d) for d in duty.DUTIES}
        for request in requests.values():
            assert request.messages[1:] == base.messages[1:]
            assert request.tools == base.tools
            try:
                timing.request_bytes(request)
            except ValueError:
                pass
            else:
                raise ValueError('partial_duty_admitted_by_old_identity')
        rows.append(dict(key=fixture['key'], report_sha256=digest(source.report),
            input_sha256=digest(inputs.data_json), complete_sources_unchanged=True,
            requests={d: dict(sha256=duty.request_sha(r), input_ceiling=size(r)) for d,r in requests.items()}))
    # Deliberately authored representation witness: no provider/Host outcome.
    no_citation = report_inputs(inputs, re.sub(r'\[K\d+\]', '', inputs.source.report))
    passing = compact(dict(score=95, verdict='pass', issues=[], advisories=[], issue_resolutions=[]))
    try:
        duty.TimedDocumentWorkflow.validate_review(passing, no_citation)
    except ValueError as error:
        old_rejection = str(error)
        assert 'missing_knowledge_citation' in old_rejection
    else:
        raise ValueError('missing_citation_counterexample_not_reproduced')
    duty.validate(passing, no_citation, 'facts')
    pair = duty.pair(no_citation, [duty.bind(no_citation,d,'initial',passing) for d in duty.DUTIES], 'initial')
    assert not pair['production_admitted']
    per_glm = (Decimal(64000)*8 + Decimal(32768)*28)/1000000
    per_flash = per_glm/10
    return dict(version=duty.VERSION, provider_calls=0, new_host_tasks=0,
        production_admitted=False, execution_ready=False, execution_authorized=False,
        original15_new_qualified=0, complete_request_audit=rows,
        facts_policy_preserved=True, completion_policy_unmeasured=True,
        missing_citation_witness=dict(kind='authored_offline_protocol_counterexample',
            old_full_validator_rejection=old_rejection, facts_wire_valid=True,
            both_structurally_pass_can_still_be_semantically_incomplete=True, publication_allowed=False),
        next_development_proposal=dict(scope='One complete fixed report: new facts/completion initial pair, at most one actual Flash edit, fresh facts/completion pair over actual revised report.',
            source_selection='duty-3 report snapshot from the closed follow-up seal; reuse input only, not reviews or Host labels',
            maximum_calls=5, glm_calls=4, flash_calls=1, output_per_call=32768,
            input_per_call=64000, maximum_tokens=5*(64000+32768),
            maximum_active_seconds=4*600+300, maximum_host_seconds=86400,
            per_glm_seconds=600, per_flash_seconds=300,
            estimated_uncached_cny=str(4*per_glm+per_flash), hard_billing_cap=False,
            no_generation=True, no_retry=True, requires_new_authorization=True,
            execution_preparation_complete=False),
        natural_product=dict(sequence=['generation','generation','facts_initial','completion_initial',
            'edit','facts_fresh','completion_fresh'], proposed_calls=7, current_calls=5,
            current_tokens=401920, current_seconds=900, token_time_expansion_authorized=False,
            per_request_maxima_sum=7*(64000+32768), per_request_time_sum=3*300+4*600,
            full_envelope_uncached_cny=str(4*per_glm+3*per_flash),
            full_envelope_is_not_current_legal_budget=True,
            admission='Actual settled usage plus unknown reservations plus next request envelope, with one owned task clock. No new ledger per duty.',
            cancellation='Must reuse actual pre-dispatch worker lease/stop guard for every future duty request; not integrated by this prototype.'),
        limitations=['Completion semantics and pair conflict detection are not proven by structure.',
            'Caller conflict_status=clear is not independently authenticated; live execution remains absent.',
            'No natural Agent/Worker/DB/API/UI consumption, no model quality or stability claim.',
            'A fixed-report five-request proposal does not authorize seven-call product integration or original15.'],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
            'scripts/review_duty_composition.py','scripts/audit_review_duty_composition.py',
            'scripts/report_block_keyed_editor.py','scripts/prepare_review_duty_probe.py',
            'tests/test_review_duty_composition.py')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output.is_relative_to(ROOT/'data/runs'):
        raise ValueError('offline_audit_outside_runs_required')
    result = audit()
    write_new_json(output, result)
    print(json.dumps(dict(output=str(output), requests=len(result['complete_request_audit'])*2,
        provider_calls=0, status='offline_only'), ensure_ascii=True))
