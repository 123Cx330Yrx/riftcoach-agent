"""Offline full-path witnesses; scripted decisions are never live acceptance."""
import argparse
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_integrated_runtime import BudgetedReviewSender
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.harness.steps import RevisionRequest
from app.providers.errors import ProviderResponseError
from scripts.blind_edit_settlement import (OfflineBlindEditWorkflow, blind_request,
    settlement_request, validate_settlement, expand_original)
from scripts.check_native_contract_options import (corrected_case3, computed_root, OfflineResponses,
    PASS, sizes, reservation, actual_case)
from scripts.native_contract_options import body


def settlement_value(original, revised, original_raw, *, validities=('confirmed', 'false_positive'),
                     statuses=('corrected', 'not_required'), review=None):
    return dict(original_review_sha256=digest(original_raw), original_report_sha256=digest(original.source.report),
        revised_report_sha256=digest(revised.source.report), decisions=[dict(issue_id=i,
            original_validity=v, revision_status=s, source_ids=[computed_root(revised)],
            explanation='分析者构造的原稿/新稿合同见证，不是模型判断或语义质量证据。')
            for i, (v, s) in enumerate(zip(validities, statuses, strict=True), 1)],
        review=native.strict_json(PASS) if review is None else review)


def path(req, responses, *, charge_ceiling=False):
    provider = OfflineResponses(responses, charge_ceiling=charge_ceiling)
    sender = BudgetedReviewSender(provider)
    flow = OfflineBlindEditWorkflow(sender)
    initial = flow.evaluate(req)
    draft = flow.revise(RevisionRequest(req.player_summary, req.deterministic_report, req.knowledge, req.report, initial))
    final = flow.evaluate(replace(req, report=draft.report))
    return final, flow, provider, sender


def run():
    req, original_raw, edit = corrected_case3()
    original = native.build_inputs(req)
    revised = native.build_inputs(replace(req, report=edit['report']))
    final_value = settlement_value(original, revised, original_raw)
    final, flow, provider, budget = path(req, [original_raw, edit['report'], compact(final_value)], charge_ceiling=True)
    assert final.verdict.value == 'pass' and flow.revisions == 1
    final_data = body(provider.requests[-1])
    old_data = native.request_data(original)
    assert final_data['original_source_index'] == old_data['source_index']
    for key, identity in [('source_roots', 'catalog_sha256'), ('computed_evidence', 'source_digest')]:
        assert expand_original(final_data, key, identity) == old_data[key]

    # Five-call report path: first-review recovery and final-settlement recovery.
    malformed = native.strict_json(original_raw)
    malformed['score'] = str(malformed['score'])
    fixed = native.strict_json(original_raw)
    fixed['issue_resolutions'] = [dict(previous_id=i, disposition='replaced', final_issue=i,
        source_ids=p['source_ids'], explanation='分析者类型恢复见证。') for i, p in enumerate(fixed['issues'], 1)]
    recovered_raw = compact(fixed)
    recovered_final = settlement_value(original, revised, recovered_raw)
    final_bad = deepcopy(recovered_final)
    final_bad['decisions'].pop()
    five_responses = [compact(malformed), recovered_raw, edit['report'], compact(final_bad), compact(recovered_final)]
    five = path(req, five_responses)
    assert len(five[2].requests) == 5 and five[0].verdict.value == 'pass'
    saturated_provider = OfflineResponses(five_responses, charge_ceiling=True)
    saturated_sender = BudgetedReviewSender(saturated_provider)
    saturated_flow = OfflineBlindEditWorkflow(saturated_sender)
    first = saturated_flow.evaluate(req)
    draft = saturated_flow.revise(RevisionRequest(req.player_summary, req.deterministic_report,
        req.knowledge, req.report, first))
    try:
        saturated_flow.evaluate(replace(req, report=draft.report))
    except ProviderResponseError as error:
        saturation = dict(completed_calls=len(saturated_provider.requests), stop_reason=error.code,
            synthetic_tokens=saturated_sender.budget.tokens, stopped=saturated_flow.stopped)
    else:
        saturation = dict(completed_calls=len(saturated_provider.requests), stop_reason=None,
            synthetic_tokens=saturated_sender.budget.tokens, stopped=saturated_flow.stopped)

    # True-only and false-only original reports still have complete paths.
    contrasts = []
    true_req, saved = actual_case(4)
    false_req, _ = actual_case(1)
    false_old = native.strict_json(original_raw)
    false_old['issues'] = [false_old['issues'][1]]
    for name, current_req, raw, actual, validity, status in [
        ('true_only', true_req, saved['responses'][0]['content'], saved['revised_report'], 'confirmed', 'corrected'),
        ('false_only', false_req, compact(false_old), false_req.report, 'false_positive', 'not_required')]:
        before = native.build_inputs(current_req)
        after = native.build_inputs(replace(current_req, report=actual))
        result = settlement_value(before, after, raw, validities=(validity,), statuses=(status,))
        route = path(current_req, [raw, actual, compact(result)], charge_ceiling=True)
        assert route[0].verdict.value == 'pass' and len(route[2].requests) == 3
        contrasts.append(dict(id=name, actual_report=actual, input_sha256=digest(before.data_json),
            original_review_raw=raw, scripted_settlement=result, calls=sizes(route[2].requests), semantic_approval=False))

    # Structural checks cannot certify semantic truth. Preserve the bad edit.
    _, bad_saved = actual_case(3)
    bad_report = bad_saved['revised_report']
    bad_inputs = native.build_inputs(replace(req, report=bad_report))
    bad = settlement_value(original, bad_inputs, original_raw)
    _, _, journal = validate_settlement(compact(bad), bad_inputs, original, original_raw)
    assert not journal['semantic_approval']
    return dict(evidence_kind='offline_two_state_contract_not_model_quality', provider_calls=0,
        live_status='offline_unregistered', original_report=req.report, actual_scripted_report=edit['report'],
        original_review_raw=original_raw, scripted_settlement=final_value,
        normal_calls=sizes(provider.requests), normal_reservation=reservation(sizes(provider.requests)),
        five_calls=sizes(five[2].requests), five_reservation=reservation(sizes(five[2].requests)),
        scripted_five_usage=five[3].budget.tokens, contrasts=contrasts,
        saturated_five_path=saturation,
        blind_editor_contains_prior_opinion=False, original_indices_reconstruct=True,
        real_bad_edit_remains_semantically_rejected=dict(report=bad_report, scripted_settlement=bad,
            structure_valid=True, semantic_approval=False),
        semantic_approval=False, production_admitted=False, initial_reviewer_qualified=False,
        limitations=['Final reviewer sees prior opinions and may still anchor.',
            'Valid source IDs cannot prove citation completeness or original validity.',
            'Actual product generation consumes the same budget; five calls here exclude generation.',
            'Real per-case full-report acceptance and unchanged extra-finding guard remain required.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = run()
    write_new_json(args.output, value)
    print(compact(dict(path=str(args.output), normal=value['normal_reservation'], five=value['five_reservation'])))
