"""Replay the frozen historical delivery audit, never the current candidate."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_native_issues_review import schema_notation
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_notes import RoleNoteReviewWorkflow as Legacy
from app.evaluation.golden_role_tool_delivery import DELIVERY_ID, RoleToolDeliveryReviewWorkflow as Current
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import ROOT, frozen_cases
from scripts.prepare_review_model_comparison import mock_wire, sdk_arguments


def audit():
    original = (ROOT/'data/evaluation/results/golden_role_tool_delivery_audit_v1.json').read_bytes()
    if hashlib.sha256(original).hexdigest() != '7b981fa8277e5380411e6c2501d379855a51f78eca91acbc07a59b477b2bd517':
        raise ValueError('role_delivery_historical_audit_changed')
    historical = json.loads(original)
    evidence_path = ROOT / 'data/evaluation/results/golden_role_note_qualification_pair_result_v1.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    saved = evidence['public_json_contents']
    bad = compact(saved['transport/claim-scope-1/review/response-001.json']['tool_calls'][0]['arguments'])
    diagnostics = [{'type': 'missing', 'loc': ['issues', 0, 'severity']}]
    rows = []
    for frozen, source in frozen_cases()[0]:
        inputs = Legacy.build_inputs(source)
        phases = {}
        for phase, kwargs in [('initial', {}), ('reassessment', dict(previous_raw=bad, diagnostics=diagnostics))]:
            before, after = [flow.make_request(inputs, **kwargs) for flow in (Legacy, Current)]
            header = schema_notation(before.tools[0].input_schema) + '\n'
            assert before.messages[1].content == header + after.messages[1].content
            assert after.metadata == {**before.metadata, 'review_delivery': DELIVERY_ID}
            assert replace(after, messages=before.messages, metadata=before.metadata) == before
            old_wire, new_wire = [mock_wire(sdk_arguments(req)) for req in (before, after)]
            assert old_wire['messages'][1]['content'] == header + new_wire['messages'][1]['content']
            old_wire['messages'][1]['content'] = new_wire['messages'][1]['content']
            assert old_wire == new_wire
            phases[phase] = dict(old_request_sha256=hashlib.sha256(validate_request(before,
                transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest(),
                current_request_sha256=hashlib.sha256(validate_request(after,
                transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest(), removed_header_characters=len(header))
        rows.append(dict(key=frozen['key'], input_sha256=digest(inputs.data_json),
            report_sha256=digest(source.report), phases=phases))
    source = dict((f['key'], s) for f, s in frozen_cases()[0])['attribution:1']
    inputs = Legacy.build_inputs(source)
    raw = compact(saved['transport/attribution-1/review/response-001.json']['tool_calls'][0]['arguments'])
    _, accepted, _ = Legacy.validate_review(raw, inputs)
    editor = Legacy.make_request(inputs, accepted=accepted)
    assert Current.make_request(inputs, accepted=accepted) == editor
    return dict(kind='offline-request-delivery-audit-v1', request_delivery=DELIVERY_ID,
        candidate_identity=historical['candidate_identity'], frozen_case_count=len(rows), cases=rows,
        checks=dict(initial_and_reassessment_only_header_and_metadata_changed=True,
            sdk_wire_only_header_changed=True, full_source_system_and_tool_schema_unchanged=True,
            editor_request_unchanged=True),
        historical_evidence_sha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
        editor_request_sha256=hashlib.sha256(validate_request(editor, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest(),
        provider_requests=0, semantic_fix_verified=False, production_admitted=False,
        limitation='Wire equivalence and history integrity only; no live qualification for this request delivery.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit()
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as target:
            target.write(text)
        print(compact(dict(output=str(args.output), cases=result['frozen_case_count'], provider_requests=0)))
    else:
        print(text)
