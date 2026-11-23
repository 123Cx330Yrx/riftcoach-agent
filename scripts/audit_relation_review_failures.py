"""Read-only decision evidence for missed relations and incorrect corrections.

Uses committed complete materials and public responses, never local run files.
Known semantic defects come from the recorded primary/native assessments, not
an NLP rule or a new business verdict. No provider or native task is created.
"""
import argparse
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_coarse_source_projection import resolve_refs
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.source_patch_editor import report_inputs
from scripts import audit_correction_consumption as historical
from scripts.document_full_report_diagnostic import source_facts, source_inputs, source_payload
from scripts import report_block_keyed_editor as editor
from scripts.report_contrast_review import ContrastDocumentWorkflow as Workflow

ROOT = Path(__file__).resolve().parents[1]
SEAL = 'data/evaluation/results/document_relation_repair_result_20261013.json'
CLOSE = 'data/evaluation/results/document_relation_repair_close_audit_20261013.json'
EXPECTED = {
    SEAL: 'b11d033fabffdec069b0d527a7ec11b55aaa1bb75e87388a6b20228494cf669d',
    CLOSE: 'b81bfcba4183eedcb218b853c0644be3f398c722b58406c752fbb52a44dc898b',
    **historical.EXPECTED,
}


def checked(path):
    raw = (ROOT / path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED[path]:
        raise ValueError('relation_audit_original_changed')
    return json.loads(raw)


def arithmetic(inputs, cohort, metric):
    """Recompute selected operands; never infer a claim from report wording."""
    computed = resolve_refs(inputs, [31])[0]['value']
    facts = resolve_refs(inputs, [32])[0]['value']['facts']
    rows = [v for k, v in facts.items() if k.startswith('facts:recent_match:')
            and v.get('included_in_aggregate') is True
            and (cohort == 'selected' or v.get('role') == cohort)]
    if not rows or any(type(v.get('win')) is not bool or metric not in v for v in rows):
        raise ValueError('relation_audit_incomplete_cohort')
    wins = [Decimal(str(v[metric])) for v in rows if v['win']]
    losses = [Decimal(str(v[metric])) for v in rows if not v['win']]
    if not wins or not losses:
        raise ValueError('relation_audit_missing_outcome_group')
    win_mean, loss_mean = sum(wins) / len(wins), sum(losses) / len(losses)
    relation = ('greater' if min(wins) > max(losses) else
                'less' if max(wins) < min(losses) else 'overlap')
    index = computed['metrics'].index(metric)
    supplied = computed['cohorts'][cohort]
    observed = dict(win_mean=str(win_mean.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)),
                    loss_mean=str(loss_mean.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)),
                    all_pairs=relation)
    if observed != {k: supplied[k][index] for k in observed}:
        raise ValueError('relation_audit_computed_conflict')
    return dict(cohort=cohort, metric=metric, wins=[str(v) for v in wins],
                losses=[str(v) for v in losses], **observed,
                exact_mean_difference=str(win_mean - loss_mean),
                establishes_causality=False, semantic_approval=False)


def validate_observed(name, inputs, response, *, recorded_defect, certified):
    payload = response['tool_calls'][0]['arguments']
    _, wire, journal = Workflow.validate_review(compact(payload), inputs)
    if journal['semantic_approval'] is not False:
        raise ValueError('relation_audit_unexpected_semantic_approval')
    return dict(case=name, report_sha256=digest(inputs.source.report),
                actual_blocks=len(inputs.source.blocks),
                response_payload_sha256=digest(compact(payload)), score=payload['score'],
                verdict=payload['verdict'], issue_blocks=[i.block for i in wire.issues],
                structural_validation='accepted_without_semantic_approval',
                recorded_semantic_defect=recorded_defect,
                historical_dual_review_certified=certified,
                new_business_verdict=False)


def edit_counterexamples(correct, wrong):
    """Author-created edit fault injections over complete U1/U2 documents.

    No historical review is modified or passed through a Host submission gate.
    This checks the existing editor and complete final request, not a model.
    """
    before = '仅这四局中单的早期死亡胜负组均值接近。'
    after = '仅这四局中单的早期死亡胜负组均值并不接近。'
    _, wire, _ = Workflow.validate_review(compact(dict(score=80,
        verdict='needs_revision', issues=[dict(block=14, severity='medium',
            category='fact_error', source_ids=[31, 32],
            explanation='OFFLINE author fixture: selected middle means are 2.50 and 0.50.',
            suggested_correction='OFFLINE author fixture: verify this comparison against full sources.')],
        issue_resolutions=[], advisories=[])), wrong)
    request = editor.edit_request(wrong, wire)
    rows = []
    scenarios = (
        ('correct_relation', after, 'supported_repair'),
        ('false_nonseparation', '仅这四局中单的早期死亡次数并未把胜局与负局分开。', 'wrong_replacement'),
        ('wrong_population', '仅这四局中单的早期死亡胜负组均值分别为2.50与2.67次。', 'wrong_replacement'),
        ('unsupported_cause', '仅这四局中单证明减少早期死亡必然导致失败。', 'wrong_replacement'),
        ('empty_edit_on_error', None, 'original_error_remains'),
    )
    for name, replacement, label in scenarios:
        edits = {} if replacement is None else {'block_14': [dict(before=before,
            after=replacement, reason='OFFLINE author counterexample; no semantic approval.')]}
        assembled = editor.inspect_exchange(request,
            historical.simulated_exchange(request, editor.TOOL, edits), wrong, wire,
            make_final=Workflow.make_request)
        expected = wrong.source.report if replacement is None else wrong.source.report.replace(
            before, replacement, 1)
        if assembled.report != expected:
            raise ValueError('relation_audit_unintended_edit')
        final = Workflow.make_request(report_inputs(wrong, assembled.report))
        if (assembled.journal['semantic_approval'] is not False
                or assembled.journal['full_final_review_required'] is not True
                or assembled.journal['final_review_request_sha256'] != editor.request_sha(final)):
            raise ValueError('relation_audit_final_binding')
        rows.append(dict(case=name, author_semantic_label=label,
            origin='author_injected_edit_not_provider_response_or_host_verdict',
            structural_result='assembled_requires_complete_final_review',
            exactly_requested_replacement=True, other_report_bytes_preserved=True,
            report_sha256=digest(assembled.report),
            equals_correct_control=assembled.report == correct.source.report,
            full_final_request_sha256=editor.request_sha(final), semantic_approval=False))
    _, keep, _ = Workflow.validate_review(compact(dict(score=97, verdict='pass',
        issues=[], issue_resolutions=[], advisories=[])), correct)
    request = editor.edit_request(correct, keep)
    assembled = editor.inspect_exchange(request,
        historical.simulated_exchange(request, editor.TOOL, {}), correct, keep,
        make_final=Workflow.make_request)
    if assembled.report != correct.source.report or assembled.journal['semantic_approval'] is not False:
        raise ValueError('relation_audit_correct_control_changed')
    rows.append(dict(case='correct_control_keep', author_semantic_label='supported_keep',
        origin='author_injected_edit_not_provider_response_or_host_verdict',
        structural_result='unchanged_requires_complete_final_review',
        report_sha256=digest(assembled.report), semantic_approval=False))
    return rows


def audit():
    originals = {path: checked(path) for path in EXPECTED}
    seal, close = originals[SEAL], originals[CLOSE]
    files = seal['public_json_contents']
    h5_inputs, _, h5_evidence, _, _ = historical.load()
    records = [validate_observed('H5', h5_inputs, h5_evidence['response'],
               recorded_defect='wrong_correction', certified=True)]
    materials, inputs = {}, {}
    for name in ('U1-baseline', 'U2-baseline'):
        prefix = name + '-initial/'
        material = files[prefix + 'material.json']
        current = source_inputs(material['report'])
        if current.data_json != material['current_input_json']:
            raise ValueError('relation_audit_complete_input_changed')
        issued = files[prefix + 'issued-request.json']
        messages = issued['messages']
        if (messages[0]['content'] != material['full_policy_text']
                or messages[1]['content'] != Workflow.make_request(current).messages[1].content
                or messages[2]['content'] != material['source_message']
                or messages[3]['content'] != material['deterministic_source_message']):
            raise ValueError('relation_audit_sent_sources_changed')
        materials[name], inputs[name] = material, current
        records.append(validate_observed(name, current, files[prefix + 'response.json'],
            recorded_defect=None if name == 'U1-baseline' else 'missed_error',
            certified=name == 'U1-baseline'))
    correct, wrong = materials['U1-baseline'], materials['U2-baseline']
    differing_blocks = [number for number, ((_, a), (_, b)) in enumerate(zip(
        inputs['U1-baseline'].source.blocks, inputs['U2-baseline'].source.blocks,
        strict=True), 1) if a != b]
    if differing_blocks != [14] or correct['report'].replace(
            '均值并不接近。', '均值接近。', 1) != wrong['report']:
        raise ValueError('relation_audit_document_pair_changed')
    if source_facts(source_payload(correct['source_message'])) != source_facts(
            source_payload(wrong['source_message'])):
        raise ValueError('relation_audit_pair_facts_changed')
    issued_pair = [files[name + '-initial/issued-request.json']
                   for name in ('U1-baseline', 'U2-baseline')]
    for field in ('tools', 'tool_choice', 'temperature', 'max_tokens', 'response_contract', 'top_p'):
        if issued_pair[0].get(field) != issued_pair[1].get(field):
            raise ValueError('relation_audit_pair_protocol_changed')
    metadata = [deepcopy(request['metadata']) for request in issued_pair]
    for value in metadata:
        del value['source_catalog_sha256']
    if metadata[0] != metadata[1]:
        raise ValueError('relation_audit_pair_identity_changed')
    a, b = [deepcopy(json.loads(m['current_input_json'])) for m in (correct, wrong)]
    for data in (a, b):
        del data['source_index']['blocks'], data['source_index']['source_digest']
    if a != b:
        raise ValueError('relation_audit_pair_nonreport_inputs_changed')
    h5_policy = originals[historical.MATERIAL]['full_policy_text']
    if h5_policy != correct['full_policy_text'] or h5_policy != wrong['full_policy_text']:
        raise ValueError('relation_audit_policy_changed')
    if close['first_semantic_deviation']['kind'] != 'missed_error' or (
            close['first_hard_deviation']['native_final_count'] != 0):
        raise ValueError('relation_audit_failure_status_changed')
    h5_relation = arithmetic(h5_inputs, 'MIDDLE', 'deaths_before_15')
    u2_relation = arithmetic(inputs['U2-baseline'], 'MIDDLE', 'deaths_before_15')
    if h5_relation != u2_relation:
        raise ValueError('relation_audit_old_new_relation_changed')
    result = dict(kind='OFFLINE-relation-review-failure-decision-v1',
        original_sha256=EXPECTED, originals_unchanged=True,
        provider_calls=0, http_calls=0, native_tasks=0, business_submissions=0,
        semantic_approval=False, new_qualification=0, production_admitted=False,
        observed_outputs=records,
        paired_input_check=dict(differing_blocks=differing_blocks,
            full_policy_identical=True, all_nonreport_inputs_identical=True,
            schema_and_sampling_identical=True,
            full_sent_source_messages_verified=True,
            only_binding_digests_and_report_blocks_differ=True),
        arithmetic=[h5_relation,
            arithmetic(inputs['U2-baseline'], 'selected', 'deaths_before_15'),
            arithmetic(inputs['U2-baseline'], 'MIDDLE', 'cs_per_min')],
        complete_document_edit_counterexamples=edit_counterexamples(
            inputs['U1-baseline'], inputs['U2-baseline']),
        first_deviations=dict(H5='Provider suggested_correction adds false nonseparation',
            U2='Provider returns pass with no issue for the explicit middle-cohort comparison',
            subsequent_hard_failure='Independent Host quota failure after complete Provider response'),
        semantic_label_origin=dict(H5='unchanged recorded primary and native independent wrong_correction',
            U1='unchanged recorded dual acceptance',
            U2='recorded primary missed_error only; independent final absent'),
        ruled_out_as_sufficient_fixes=[
            'Supply missing mean/row comparisons: already present in both complete inputs.',
            'Treat structural validation or source IDs as semantic acceptance: both defects pass it.',
            'Change edit representation or bypass complete initial review: cannot repair its first deviation; ADR0110 counterevidence remains.',
            'Use Host availability recovery as a model semantic fix: business response preceded it.',
            'Infer numerical proximity from a new arbitrary threshold or keyword: would change the standard.'],
        open_hypotheses=['Population/metric/relation selection and causal interpretation may be confused.',
            'Whole-document workload or adjacent correct claims may affect judgment.',
            'These are not isolated causes; no internal model-root-cause finding is made.'],
        decision=dict(retain='Complete initial review, complete sources, existing edit and complete final review.',
            candidate='Relation teaching remains unadmitted; U2 candidate was not issued.',
            do_not_build='No keyword semantic gate, correction autodeletion, new schema or pass-after-edit bypass.',
            next_informative_check='A prospective full-report candidate check must cover actual error detection AND the returned correction, plus correct-content preservation; full sources and context remain intact.',
            cost_boundary='No closed-batch retry/redelivery; any new paid scope needs its own concrete authorization.'),
        limitations=['Arithmetic does not interpret natural-language proximity or causality.',
            'H5 and U2 differ in report and earlier runtime; not a randomized causal pair.',
            'Familiar-source development evidence, not holdout, stability or product qualification.',
            'This audit is not a new independent review or historical recertification.'])
    for path, expected in EXPECTED.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError('relation_audit_original_changed_after_read')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = audit()
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(observed_outputs=len(value['observed_outputs']),
        provider_calls=0, new_qualification=0)))
