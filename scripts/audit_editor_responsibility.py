"""Offline comparison of sealed public evidence; never constructs a provider.

Observed host decisions remain historical judgments, not computed truth labels.
This audit neither rewrites old requests nor manufactures a counterfactual run.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'data/evaluation/results'
FILES = {
    'locator_pair': 'golden_native_editor_pair_result_483f91d.json',
    'blind_full_edit': 'golden_blind_edit_result_6c22e93.json',
    'full_edit_timeout': 'golden_independent_edit_result_58449abb.json',
    'source_patch': 'golden_source_patch_pair_result_v1.json',
    'mixed_tail': 'golden_mixed_review_tail_result_20261008.json',
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def request_facts(request):
    message = request['messages'][1]['content']
    start, end = '[UNTRUSTED DATA]\n', '\n[END UNTRUSTED DATA]'
    assert start in message and message.endswith(end)
    data = json.loads(message.split(start, 1)[1][:-len(end)])
    tool = request['tools'][0] if request['tools'] else None
    fields = []
    if tool:
        schema = tool['input_schema']
        item = schema['properties']['edits']['items']
        if '$ref' in item:
            item = schema['$defs'][item['$ref'].split('/')[-1]]
        fields = item['required']
    return dict(
        data_fields=sorted(data),
        prior_review_fields=sorted(set(data) & {
            'accepted_review', 'review_findings', 'previous_review', 'original_review'}),
        report_projection_sha256=fingerprint(data['source_index']['blocks']),
        system_sha256=fingerprint(request['messages'][0]['content']),
        output_fields=fields, tool=tool['name'] if tool else None,
        timeout_s=request['timeout_s'], max_tokens=request['max_tokens'])


def audit():
    saved = {k: json.loads((RESULTS / name).read_bytes()) for k, name in FILES.items()}
    pair, blind, timeout, patch, mixed = (saved[k] for k in FILES)
    dispositions = {a['condition']: a['structure_result']['dispositions'] for a in pair['arms']}
    assert dispositions == {'locator_only': ['apply', 'withdraw'], 'full_opinion': ['apply', 'apply']}
    assert blind['manual_adjudication']['actual_edit_accepted_for_this_case'] is True
    assert blind['manual_adjudication']['final_review_accepted'] is False
    assert timeout['original_result']['error_code'] == 'stream_deadline'
    assert timeout['conclusion']['editing_semantics_observed'] is False
    assert patch['host_review']['remaining']['block'] == 18
    assert patch['host_review']['corrected']['block'] == 27
    assert patch['host_review']['semantic_approval'] is False
    result = mixed['execution_result']
    assert result['calls'] == 1 and result['error_code'] == 'mixed_tail_host_rejected'
    assert mixed['accounting']['by_model']['glm-5.3']['reserved_calls'] == 0
    requests = {
        'full_edit_timeout': timeout['public_json_contents']['original-date-error/request.json'],
        'source_patch': patch['public_json_contents']['original-date-error/request.json'],
        'mixed_tail': mixed['public_json_contents']['necessary-edit/request.json'],
    }
    facts = {k: request_facts(r) for k, r in requests.items()}
    assert facts['mixed_tail']['prior_review_fields'] == ['accepted_review']
    assert facts['source_patch']['prior_review_fields'] == facts['full_edit_timeout']['prior_review_fields'] == []
    assert facts['mixed_tail']['output_fields'] == ['block', 'before', 'after', 'reason']
    assert facts['source_patch']['output_fields'] == ['block', 'before', 'after', 'source_ids', 'reason']
    assert facts['source_patch']['report_projection_sha256'] != facts['mixed_tail']['report_projection_sha256']
    return dict(
        kind='editor_responsibility_evidence_audit_v1', provider_calls=0,
        input_sha256={FILES[k]: hashlib.sha256((RESULTS / FILES[k]).read_bytes()).hexdigest() for k in FILES},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        method='Read sealed public request fields and recorded host decisions; no private reasoning or new model results.',
        request_comparison=facts,
        observed=dict(locator_dispositions=dispositions, blind_edit_accepted=True,
            blind_complex_final_accepted=False, full_edit_semantics_observed=False,
            source_patch_corrected_block=27, source_patch_remaining_unsupported_block=18,
            mixed_edit_rejected=True, mixed_fresh_sent=False),
        conclusions=dict(
            no_prior_opinion_is_sufficient=False,
            matched_four_field_no_opinion_control_in_reviewed_seals=False,
            old_timeout_proves_semantic_failure=False,
            old_opinion_is_proven_internal_cause=False,
            editor_only_change_repairs_initial_review=False,
            host_filtered_issues_are_autonomous_product_path=False),
        decision='Do not prepare another paid tail variant solely to remove prior opinions. '
                 'Retain editor success evidence, preserve initial-review qualification, '
                 'and evaluate changes at the failing complete initial-review task.',
        qualification_evaluated=False, production_admitted=False)


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
