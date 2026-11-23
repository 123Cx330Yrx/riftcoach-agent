"""Prepare a four-request reviewer screen offline; no provider or live sender.

Rebuild the closed run's public input before deriving two full reports. Labels
stay outside requests. This is a candidate screen, not a GLM comparison trial,
production profile, application/fresh run, or semantic qualification.
"""
from dataclasses import fields, replace
from decimal import Decimal
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_bounded_correction_requests import restore_generation
from app.evaluation.golden_contextual_requests import restore as restore_tables
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import _mapping
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from app.evaluation.natural_duty_contract import make_request
from app.evaluation.source_patch_editor import report_inputs
from app.harness.steps import EvaluationRequest, KnowledgeCitation, KnowledgeEvidence, KnowledgeRetrieval
from scripts.report_document_view import restore_document

ROOT = Path(__file__).resolve().parents[1]
MATERIAL = ROOT / 'data/evaluation/fixtures/natural_duty_observed_review_20261015/review-evidence/material.json'
MATERIAL_SHA = '8b2343d550a402ca18c58926b8044749342fef7c1ae3126663e3f1aff37192c6'
PACKAGE = ROOT / 'data/evaluation/fixtures/reviewer_profile_screen_20261015'
VERSION = 'offline-reviewer-profile-screen-v1'
REPORT_PREFIX = 'reports/natural-duty-observed-20261015/'
TRANSPORT_PREFIX = 'transport/natural-duty-observed-20261015/review/'
DUTIES = ('facts', 'completion')


def json_value(request):
    return json.loads(json.dumps(request, default=_mapping, ensure_ascii=False, allow_nan=False))


def visible(value):
    """Ignore Host metadata and empty dataclass defaults, not supplied content."""
    if any(m.get('name') or m.get('tool_call_id') or m.get('tool_calls') for m in value['messages']):
        raise ValueError('unexpected_message_fields')
    return dict(messages=[dict(role=m['role'], content=m['content']) for m in value['messages']],
                tools=value['tools'], tool_choice=value['tool_choice'], response_contract=value['response_contract'])


def source_inputs():
    raw = MATERIAL.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MATERIAL_SHA:
        raise ValueError('public_source_snapshot_changed')
    artifacts = json.loads(raw)['artifacts']
    actual = {d: artifacts[TRANSPORT_PREFIX + f'request-00{n}.json']['public_value']
              for d, n in zip(DUTIES, (3, 4))}
    request = actual['facts']
    text = request['messages'][2]['content']
    start, end = '[UNTRUSTED DATA]\n', '\n[END UNTRUSTED DATA]'
    if not text.startswith(start) or not text.endswith(end):
        raise ValueError('source_data_envelope')
    data = json.loads(text[len(start):-len(end)])
    source = request['messages'][3]['content']
    start, end = '[UNTRUSTED deterministic_source_facts]\n', '\n[END UNTRUSTED deterministic_source_facts]'
    if not source.startswith(start) or not source.endswith(end):
        raise ValueError('deterministic_source_envelope')
    knowledge = artifacts[REPORT_PREFIX + 'knowledge/retrieval_evidence.json']['public_value']
    knowledge = KnowledgeEvidence(context=knowledge['context'], source_ids=tuple(knowledge['source_ids']),
        abstained=knowledge['abstained'], diagnostics=knowledge['diagnostics'],
        citations=tuple(KnowledgeCitation(**{f.name: c[f.name] for f in fields(KnowledgeCitation)
                        if f.name in c}) for c in knowledge['citations']),
        retrievals=tuple(KnowledgeRetrieval(**{**r, 'chunk_ids': tuple(r['chunk_ids'])})
                         for r in knowledge['retrievals']))
    inputs = build_inputs(EvaluationRequest(
        artifacts[REPORT_PREFIX + 'inputs/player_summary.json']['public_value'],
        source[len(start):-len(end)], knowledge,
        artifacts[REPORT_PREFIX + 'drafts/coach_draft_attempt_0.md']['public_value'], data['user_utterance']))
    # The archived summary JSON sorts object keys. Restore the original lossless
    # generation view (including its field order), then check value equality
    # against the independently rebuilt summary before using that presentation.
    restored = dict(data, deterministic_source_facts=source[len(start):-len(end)],
        source_index={'evidence_keys': list(inputs.source.evidence_keys)})
    restored = restore_tables(restored)
    original_generation = restore_generation(restored['generation_view'], restored['facts_and_provenance']['facts'])
    rebuilt = json.loads(inputs.data_json)
    if (restored['facts_and_provenance'] != rebuilt['facts_and_provenance']
            or original_generation != rebuilt['generation_facts']):
        raise ValueError('source_value_reconstruction_changed')
    rebuilt['generation_facts'] = original_generation
    inputs = replace(inputs, data_json=compact(rebuilt))
    for duty in DUTIES:
        if visible(json_value(make_request(inputs, duty))) != visible(actual[duty]):
            raise ValueError('closed_public_request_reconstruction_changed:' + duty)
    return inputs


def research_request(inputs, duty):
    # Reuse exact business policy/schema. A new offline marker cannot impersonate
    # the frozen GLM candidate or be accepted by its role/identity validator.
    base = make_request(inputs, duty)
    return replace(base, metadata={'offline_screen': VERSION, 'duty': duty})


def prepare(package=PACKAGE):
    source = source_inputs()
    dataset = json.loads((package / 'evaluation.json').read_text(encoding='utf-8'))
    if dataset['source_material_sha256'] != MATERIAL_SHA or len(dataset['cases']) != 2:
        raise ValueError('screen_dataset_binding')
    if {c['id'] for c in dataset['cases']} != {'r01', 'r02'}:
        raise ValueError('screen_case_inventory')
    reports = {c['id']: (package / (c['id'] + '.md')).read_text(encoding='utf-8') for c in dataset['cases']}
    derived = source.source.report
    for edit in dataset['derivation_from_closed_report']:
        if derived.count(edit['before']) != 1:
            raise ValueError('screen_derivation_anchor')
        derived = derived.replace(edit['before'], edit['after'], 1)
    if derived != reports['r01']:
        raise ValueError('screen_derivation_changed')
    contrast = dataset['contrast']
    if (reports['r01'].count(contrast['before']) != 1
            or reports['r02'] != reports['r01'].replace(contrast['before'], contrast['after'], 1)):
        raise ValueError('screen_not_one_exact_edit')
    requests, rows = {}, []
    # Start with the legal control: misclassifying it closes this screen before
    # buying the negative control. Each response requires whole-source judgment.
    for case_id in ('r01', 'r02'):
        inputs = report_inputs(source, reports[case_id])
        for duty in DUTIES:
            request = research_request(inputs, duty)
            document = request.messages[1].content
            start, end = '[UNTRUSTED REPORT DOCUMENT]\n', '\n[END UNTRUSTED REPORT DOCUMENT]'
            if not document.startswith(start) or not document.endswith(end):
                raise ValueError('screen_report_envelope')
            if restore_document(document[len(start):-len(end)], inputs) != reports[case_id]:
                raise ValueError('screen_report_projection_loss')
            size = estimate_runtime_request_input_ceiling(request)
            if size > 64000:
                raise ValueError('screen_input_envelope')
            value = visible(json_value(request))
            # No provider parameters are smuggled into the common business input.
            # Provider-specific wire mapping is deliberately still unimplemented.
            key = case_id + '-' + duty
            requests[key] = value
            rows.append(dict(id=key, request_sha256=digest(compact(value)),
                report_sha256=digest(inputs.source.report), input_sha256=digest(inputs.data_json),
                policy_sha256=digest(request.messages[0].content),
                schema_sha256=digest(compact(request.tools[0].input_schema)),
                existing_local_input_estimate=size, model_result=None, actual_http=None))
    # These limits are a proposed budget, not a cross-provider tokenizer proof.
    budget = dict(max_requests=4, max_retries=0, input_tokens_per_request=64000,
        output_tokens_per_request=32768, maximum_total_tokens=4 * (64000 + 32768),
        request_timeout_seconds=300, maximum_model_seconds=1200,
        official_reference_uncached_estimate_usd=str((Decimal(4*64000)*2 + Decimal(4*32768)*10)/1000000),
        pricing_basis='official reference only: 2026-10-15 snapshot in reviewer-route-comparison.md; USD 2/10 per million; not a third-party channel quote or actual cost',
        hard_billing_cap=False, input_tokenizer_verified=False)
    result = dict(version=VERSION, source_material_sha256=MATERIAL_SHA,
        evaluation_sha256=hashlib.sha256((package/'evaluation.json').read_bytes()).hexdigest(),
        source_input_sha256=digest(source.data_json), historical_visible_requests_reconstructed=2,
        official_reference_profile=dict(provider='openai', model='gpt-6.1-sol', reasoning_effort='high',
            api='responses', sampling='provider-supported defaults; not GLM 1.0/.95 equivalence',
            tool_choice='auto as in historical request; exactly one named call required on receipt',
            schema_mode='must preserve existing optional fields; API compatibility not yet verified'),
        selected_execution_profile=None, actual_channel_estimate=None,
        rows=rows, proposed_budget=budget,
        evidence_class='authored-development-screen-familiar-source-not-holdout',
        provider_calls=0, execution_ready=False, execution_authorized=False, qualified=False,
        semantic_detection_proven=False, publication_allowed=False,
        live_dependencies=['explicit profile/cost decision', 'account/model/API availability without assuming Codex access',
            'minimal isolated Responses transport and authentic receipt/usage/timeout tests',
            'exact wire request and input-envelope verification', 'frozen preparation and exact HEAD public CI',
            'new bounded authorization; no reuse of closed batch authorization'])
    return result, requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='create missing output files; never overwrite')
    args = parser.parse_args()
    result, requests = prepare()
    if args.write:
        files = {PACKAGE/'manifest.json': result,
                 **{PACKAGE/'requests'/(key+'.json'): value for key, value in requests.items()}}
        if any(path.exists() for path in files):
            raise ValueError('screen_outputs_already_exist')
        for path, value in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
    else:
        if json.loads((PACKAGE/'manifest.json').read_text(encoding='utf-8')) != result:
            raise ValueError('screen_manifest_changed')
        for key, value in requests.items():
            if json.loads((PACKAGE/'requests'/(key+'.json')).read_text(encoding='utf-8')) != value:
                raise ValueError('screen_saved_request_changed')
    print(json.dumps(dict(requests=len(requests), historical_requests_reconstructed=2,
        budget=result['proposed_budget'], provider_calls=0, execution_ready=False), ensure_ascii=True))


if __name__ == '__main__':
    main()
