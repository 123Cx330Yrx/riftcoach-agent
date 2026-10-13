"""Offline consumption of committed J1/J2 responses; never execute a run.

Author-injected edits exercise the existing timed editor and final request.
They are not Provider responses, new Host judgments, or qualification evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

from app.evaluation import document_review_qualification as qualification
from app.evaluation import document_review_timing_adapter as timing
from app.evaluation.golden_explicit_source_projection import _unpack
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.source_patch_editor import report_inputs
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from scripts.document_full_report_diagnostic import source_inputs
from scripts.report_timed_document_workflow import TimedDocumentWorkflow as Workflow, request_sha
from scripts import report_block_keyed_editor as editor
from scripts.run_full15_resumption_candidate import selected_controls

ROOT = Path(__file__).resolve().parents[1]
SEAL = 'data/evaluation/results/document_relation_joint_result_20261013.json'
CLOSE = 'data/evaluation/results/document_relation_joint_close_audit_20261013.json'
EXPECTED = {
    SEAL: '9ade982f309414a90fe909bbdfca5ad99861fa03d6d4f491e923633c6e91546c',
    CLOSE: '3c53b9011171bcab999d8492c023631b708d6e435f5c6485a8858d7c3d4f9898',
}
CELLS = ('J1-baseline', 'J1-relation-contrast', 'J2-baseline', 'J2-relation-contrast')
INSPECTED = (
    'scripts/audit_post_joint_consumption.py',
    'scripts/run_full15_resumption_candidate.py', 'scripts/full15_resumption_evidence.py',
    'scripts/host_review_workspace.py', 'scripts/document_relation_joint_diagnostic.py',
    'scripts/report_timed_document_workflow.py', 'scripts/report_block_keyed_editor.py',
    'scripts/report_contrast_review.py', 'app/evaluation/document_review_qualification.py',
    'app/evaluation/document_review_identity.py', 'app/evaluation/document_review_timing_adapter.py',
    'app/evaluation/golden_native_partitioned_tool_review.py',
    'app/product/native_coach_composition.py', 'app/product/coach_composition.py',
    'app/workers/composition.py', 'app/workers/review_worker.py',
    'app/runtime/coach_budget.py', 'tests/test_timed_document_worker.py',
)


def checked(path):
    raw = (ROOT / path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED[path]:
        raise ValueError('post_joint_original_changed')
    return json.loads(raw)


def material_inputs(material, issued):
    inputs = source_inputs(material['report'])
    request = Workflow.make_request(inputs)
    if (inputs.data_json != material['current_input_json']
            or len(inputs.source.blocks) != 26
            or [m['content'] for m in issued['messages']] != [
                material['full_policy_text'], request.messages[1].content,
                material['source_message'], material['deterministic_source_message']]
            or request.messages[2].content != material['source_message']
            or request.messages[3].content != material['deterministic_source_message']):
        raise ValueError('post_joint_material_binding')
    return inputs


def consume(inputs, payload, correct):
    _, wire, journal = Workflow.validate_review(compact(payload), inputs)
    request = Workflow.edit_request(inputs, wire)
    _, data = _unpack(request)
    # Existing optional clarity markers stay in the review journal; they must
    # not be promoted to required edits. All substantive opinions stay intact.
    if (wire.model_dump(mode='json') != payload
            or data['accepted_review'] != wire.model_dump(mode='json', exclude={'advisories'})
            or journal['advisories'] != [dict(v, quote=inputs.source.blocks[v['block'] - 1][1])
                                        for v in payload['advisories']]):
        raise ValueError('post_joint_review_consumption')
    base_data = _unpack(Workflow.edit_request(inputs, wire))[1]
    del base_data['accepted_review']
    replacements = {}
    for n in (14, 15):
        before, after = inputs.source.blocks[n - 1][1], correct.source.blocks[n - 1][1]
        if before != after:
            replacements[f'block_{n}'] = [dict(before=before, after=after,
                reason='OFFLINE author fixture; not a model edit or semantic approval.')]
    scenarios = {'correct_both': replacements,
                 'only_14': {k: v for k, v in replacements.items() if k == 'block_14'},
                 'only_15': {k: v for k, v in replacements.items() if k == 'block_15'},
                 'empty': {}} if replacements else {'correct_keep': {}}
    rows = []
    for name, edits in scenarios.items():
        response = ChatResponse(provider='zhipu', model='glm-5.3-flash', content=None,
            usage=TokenUsage(input_tokens=0, output_tokens=0), finish_reason='tool_calls',
            tool_calls=(ToolCall(id='OFFLINE-author-edit', name=editor.TOOL,
                                 arguments={'edits': edits}),))
        assembly = Workflow.inspect_exchange(request,
            Exchange(request, response, request_sha(request)), inputs, wire)
        expected = inputs.source.report
        for changes in edits.values():
            for change in changes:
                if expected.count(change['before']) != 1:
                    raise ValueError('post_joint_fixture_anchor')
                expected = expected.replace(change['before'], change['after'], 1)
        final_inputs = report_inputs(inputs, assembly.report)
        final = Workflow.make_request(final_inputs)
        # Compare the COMPLETE nonreport input, not merely source counts.
        original_data, final_data = json.loads(inputs.data_json), json.loads(final_inputs.data_json)
        for item in (original_data, final_data):
            del item['source_index']['blocks'], item['source_index']['source_digest']
        if (assembly.report != expected or original_data != final_data
                or assembly.journal['semantic_approval'] is not False
                or assembly.journal['full_final_review_required'] is not True
                or assembly.journal['final_review_request_sha256'] != request_sha(final)
                or any('accepted_review' in (m.content or '') for m in final.messages)):
            raise ValueError('post_joint_final_binding')
        rows.append(dict(scenario=name, origin='OFFLINE_author_injection',
            actual_model_edit=False, semantic_approval=False,
            equals_correct_control=assembly.report == correct.source.report,
            requested_edits_only=True, complete_nonreport_inputs_preserved=True,
            report_sha256=digest(assembly.report), final_request_sha256=request_sha(final),
            full_final_required=True, old_opinion_in_final=False))
    return dict(actual_payload_sha256=digest(compact(payload)),
        edit_request_sha256=request_sha(request), issue_blocks=[v.block for v in wire.issues],
        all_issue_fields_preserved=True, optional_advisories_journal_only=payload['advisories'],
        complete_edit_input_sha256=digest(compact(base_data)), scenarios=rows)


def audit():
    source_sha = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in INSPECTED}
    seal, close = checked(SEAL), checked(CLOSE)
    if (close['seal_sha256'] != EXPECTED[SEAL]
            or close['original_file_sha256'] != seal['original_file_sha256']
            or seal['new_qualification'] != 0):
        raise ValueError('post_joint_close_binding')
    files = seal['public_json_contents']
    inputs, records = {}, {}
    for name in CELLS:
        prefix = name + '-initial/'
        inputs[name] = material_inputs(files[prefix + 'material.json'],
                                      files[prefix + 'issued-request.json'])
    correct = inputs['J1-baseline']
    for name in CELLS:
        records[name] = consume(inputs[name],
            files[name + '-initial/response.json']['tool_calls'][0]['arguments'], correct)
    rows, variants = selected_controls(timing_mode='time600')
    plan, _ = qualification.prepare_qualification()
    original_cases = {row['key']: row for row in plan['cases']}
    baseline_policy = files['J1-baseline-initial/material.json']['full_policy_text']
    bindings = []
    for row, (frozen, _, current, request) in zip(rows, variants, strict=True):
        if (request.messages[0].content != baseline_policy
                or any(frozen[k] != original_cases[row['key']][k]
                       for k in ('input_sha256', 'report_sha256', 'manifest_sha256'))):
            raise ValueError('post_joint_full15_input_or_policy_changed')
        try:
            qualification.role_for_request(request)
        except ValueError as exc:
            rejection = str(exc)
        else:
            raise ValueError('post_joint_legacy_identity_accepted_candidate')
        bindings.append(dict(key=row['key'], input_sha256=digest(current.data_json),
            report_sha256=digest(current.source.report), request_sha256=request_sha(request),
            schema_sha256=digest(compact(request.tools[0].input_schema)),
            legacy_identity_rejection=rejection))
    limits = timing._TimedLimits().descriptor()
    result = dict(kind='OFFLINE-post-joint-consumption-v1', original_sha256=EXPECTED,
        inspected_source_sha256=source_sha,
        provider_calls=0, http_calls=0, native_tasks=0, business_submissions=0,
        actual_model_edits=0, semantic_approval=False, new_qualification=0,
        execution_ready=False, production_admitted=False,
        actual_review_consumption=records, original15_same_inputs=bindings,
        original15_policy_equals_joint_baseline=True,
        baseline_is_prior_whole_text_teaching=True,
        relation_teaching_adopted=False,
        shared_task_budget=dict(max_calls=limits['max_calls'], max_tokens=limits['total_tokens'],
            task_seconds=timing.TASK_TIMEOUT_S, review_seconds=timing.GLM_REVIEW_TIMEOUT_S,
            flash_seconds=timing.FLASH_TIMEOUT_S, natural_generation_in_fixed15=False),
        limits=['No Provider edit/final response was obtained.',
            'Familiar sources and four initial reviews do not qualify original15 or natural tasks.',
            'Legacy qualification identity rejects this combination; no historical seal is rewritten.',
            'Full15 Host dispatch/submit needs prospective workspace and observation guards.',
            'Default product has no timed-document composition builder.',
            'Worker publication fencing does not establish between-stage send cancellation.'],
        decision='Retain initial/edit/full final. Prepare prospective full-chain evidence guards before any new paid scope; do not buy another familiar-report teaching comparison.')
    for path in EXPECTED:
        checked(path)
    if any(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha for p, sha in source_sha.items()):
        raise ValueError('post_joint_source_changed_during_audit')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = audit()
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(provider_calls=0, cases=len(result['actual_review_consumption']),
                         controls=len(result['original15_same_inputs']), execution_ready=False)))
