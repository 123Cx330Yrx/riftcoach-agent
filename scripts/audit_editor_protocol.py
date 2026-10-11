"""Read committed public receipts and exercise SDK encoding with a local stub.

No credentials, network, run directory, response repair or qualification. Shape
validity is separate from the historical human judgments of report semantics.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator

from app.evaluation.golden_stream_bridge import REQUEST, CAPACITY_TRANSPORT_ID, transport_profile
from app.providers.zhipu import ZhipuProvider

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT/'data/evaluation/results'
# Select real calls once; prepared/stage/transport copies are not extra calls.
EXPORTS = (
    ('golden_coarse_edit_diagnostic_result_20261001.json',
     'a344b5f00b0e8ed4277a2adba08beea4a257af055ee99cbacb20494ed9f53500',
     ('transport/diagnostic/generation/request-001.json',)),
    ('golden_coarse_inline_edit_result_20261001.json',
     '9d349e66b13c4f89126443a4b6317a5d05b7d1262002499e9dff7a312ecb1911',
     ('necessary-edit/request.json',)),
    ('golden_review_bound_edit_result_20261001.json',
     '941d3ca57984626c4e507dd1f6a8b0adc3927bc9bb8d9767b20cdbbbc9eceffb',
     ('transport/diagnostic/generation/request-001.json', 'transport/diagnostic/generation/request-003.json')),
    ('golden_review_bound_original15_result_20261008.json',
     'c1c3bfdab165fb106522f82008f950283aca18ed27b66af9aaf31d726d3ed525',
     ('transport/claim-scope-4/generation/request-002.json',)),
    ('golden_mixed_review_tail_result_20261008.json',
     '9e97c02e7e10cee21fe03b4d5c190fff293ef22a9716029db1368ede4102bf1a',
     ('transport/diagnostic/generation/request-001.json',)),
    ('golden_document_original15_result_20261008.json',
     'd225f75e39e850e62c7af2cefab1ec823d837e6c46fd65606e93da373d2ed4c5',
     ('transport/claim-scope-3/generation/request-002.json', 'transport/claim-scope-4/generation/request-002.json')),
    ('golden_document_accepted_tails_result_20261009.json',
     'cd3cbe29a9d27ff09dfe560d6272a40f67f54a8e83e6138a0b5ae6a4734c5f4c',
     ('scope-4/revision/issued-request.json',)),
    ('golden_document_checkpoint_tails_result_20261009.json',
     'b87882fd3fc86bc1d3dc873930aabe090fc4b63e1ad1c3ae7405d31a32ca7700',
     ('scope-4/revision/issued-request.json',)),
    ('golden_document_remaining_checkpoint_tails_result_20261009.json',
     '4628e972c6b2b0015e31454a38724f73319e660ed807a62611fd613ddfbad0c5',
     ('claim-scope-6/revision/issued-request.json',)),
)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def anchor_occurrences(blocks, before):
    """Count addresses, including overlapping anchors, without choosing one."""
    if not isinstance(before, str) or not before:
        raise ValueError('editor_audit_empty_anchor')
    count = 0
    for block in blocks:
        start = 0
        while (position := block['text'].find(before, start)) >= 0:
            count += 1
            start = position + 1
    return count


def sdk_projection(request):
    """Call only a local recording stub at the actual provider encoding seam."""
    calls = []

    def capture(**payload):
        calls.append(payload)
        return iter(())

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=capture)))
    provider = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3-flash',
        profile=transport_profile(CAPACITY_TRANSPORT_ID))
    provider._open_stream_for_adapter(request, tool_stream=True, include_usage_tail=True)
    if len(calls) != 1:
        raise ValueError('editor_audit_sdk_projection_count')
    return calls[0]


def assess(request_data, response):
    request = REQUEST.validate_json(json.dumps(request_data, ensure_ascii=False))
    if len(request.tools) != 1:
        raise ValueError('editor_audit_tool_inventory')
    tool = request.tools[0]
    schema = dict(tool.input_schema)
    Draft202012Validator.check_schema(schema)
    payload = sdk_projection(request)
    encoded = payload['tools'][0]['function']
    if encoded['parameters'] != schema or encoded['name'] != tool.name:
        raise ValueError('editor_audit_sdk_schema_changed')
    if (response['finish_reason'] != 'tool_calls' or response.get('content')
            or len(response['tool_calls']) != 1 or response['tool_calls'][0]['name'] != tool.name):
        raise ValueError('editor_audit_response_channel')
    arguments = response['tool_calls'][0]['arguments']
    errors = sorted(Draft202012Validator(schema).iter_errors(arguments),
        key=lambda e: (str(list(e.absolute_path)), e.message))
    # No input values or private reasoning are emitted by the error summary.
    failures = [dict(path=list(e.absolute_path), validator=e.validator,
        missing_fields=[k for k in e.validator_value if k not in e.instance]
            if e.validator == 'required' and isinstance(e.instance, dict) else []) for e in errors]
    item = schema['properties']['edits']['items']
    if '$ref' in item:
        item = schema['$defs'][item['$ref'].rsplit('/', 1)[1]]
    content = request_data['messages'][1]['content']
    prefix, suffix = '[UNTRUSTED DATA]\n', '\n[END UNTRUSTED DATA]'
    if not content.startswith(prefix) or not content.endswith(suffix):
        raise ValueError('editor_audit_source_projection')
    blocks = json.loads(content[len(prefix):-len(suffix)])['source_index']['blocks']
    return dict(tool=tool.name, required_fields=item['required'],
        schema_sha256=fingerprint(schema), schema_uses_ref='$defs' in schema,
        schema_valid=not failures, errors=failures,
        edit_count=len(arguments['edits']), returned_fields=[sorted(e) for e in arguments['edits']],
        before_occurrences_in_source_blocks=[anchor_occurrences(blocks, e['before'])
            for e in arguments['edits']],
        sdk_parameters_preserved=True, sdk_tool_choice=payload['tool_choice'],
        server_strict_requested='strict' in encoded,
        response_format=payload.get('response_format'),
        output_tokens=response['usage']['output_tokens'],
        limits='SDK kwargs reconstructed offline, not captured historical HTTP or raw SSE.')


def audit(results=RESULTS, exports=EXPORTS):
    rows = []
    for filename, expected_sha, requests in exports:
        raw = (Path(results)/filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError('editor_audit_export_changed')
        files = json.loads(raw)['public_json_contents']
        for path in requests:
            response_path = path.replace('issued-request.json', 'response.json').replace('request-', 'response-').replace('/request.json', '/response.json')
            rows.append(dict(export=filename, export_sha256=expected_sha,
                request_path=path, response_path=response_path,
                request_projection_sha256=fingerprint(files[path]),
                response_projection_sha256=fingerprint(files[response_path]),
                **assess(files[path], files[response_path])))
    counts = Counter((r['tool'], r['schema_valid']) for r in rows)
    return dict(kind='editor-protocol-public-audit-v1', rows=rows,
        inventory=[dict(tool=tool, schema_valid=valid, calls=count)
            for (tool, valid), count in sorted(counts.items())],
        provider_calls=0, qualification_evaluated=False, responses_modified=False,
        limits=['Curated closed development calls are not a random reliability sample.',
            'Schema-valid is not semantically accepted or an authenticated Host stage.',
            'Server-side constrained decoding and historical wire are not proved by local encoding.',
            'Anchor counts diagnose address expressibility; they never fill missing block or assemble a report.'],
        decision='No identified schema-loss defect. Retain strict rejection and four-field editor; '
            'do not infer strict support, repair old responses, or buy another schema rearrangement. '
            'Any prospective anchor-only contract needs duplicate/cross-block expressibility '
            'evidence and cannot repair initial-review scope errors.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    value = audit()
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            f.write('\n')
    print(json.dumps(dict(calls_audited=len(value['rows']), inventory=value['inventory'],
        provider_calls=0), ensure_ascii=False))


if __name__ == '__main__':
    main()
