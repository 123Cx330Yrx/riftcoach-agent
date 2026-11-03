"""No-I/O audit of decoding controls using public closed comparison evidence.

This neither defines a runnable candidate nor changes a frozen transport gate.
The recorder replaces the SDK client entirely; no credentials or network client
are constructed, no responses/receipts are invented, and no old run is read.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_review_experiment import SourceIndex, compact
from app.providers.zhipu import ZhipuProvider
from app.providers.errors import ProviderResponseError
from scripts import document_semantic_request as identity
from scripts.prepare_document_semantic_comparison import read_request
from scripts.report_timed_document_workflow import TimedDocumentWorkflow

ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / 'data/evaluation/results/document_semantic_comparison_result_20261011.json'
OUTPUT = ROOT / 'data/evaluation/results/document_sampling_boundary_audit_20261011.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


class EmptyLocalStream:
    def __iter__(self):
        return iter(())

    def close(self):
        pass


def sdk_payload(request):
    recorded = []

    def record(**kwargs):
        recorded.append(kwargs)
        return EmptyLocalStream()

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=record)), max_retries=0)
    bridge = identity.isolated_bridge()
    provider = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3',
                                                    profile=bridge.transport_profile(identity.TRANSPORT))
    session = provider.stream_adapter(tool_stream=True,
        evaluation_request_policy=bridge.transport_request_policy(identity.TRANSPORT)).stream_session(
            request, include_usage_tail=True)
    session.close()
    if len(recorded) != 1:
        raise ValueError('local_sdk_recording_count')
    return recorded[0]


def audit():
    raw = SEAL.read_bytes()
    seal = json.loads(raw)
    if seal['strict_replay'] is not True or not seal['result']['scan_completed']:
        raise ValueError('sampling_source_not_closed')
    rows = []
    for ordinal in range(1, 6):
        stem = f'sample-{ordinal}-expanded_examples'
        path = stem + '/issued-request.json'
        value = seal['public_json_contents'][path]
        preserved = read_request(json.dumps(value, ensure_ascii=False).encode('utf-8'))
        material = seal['public_json_contents'][stem + '/material.json']
        # The public seal sorts JSON object keys. Rebuild through the actual
        # workflow to restore schema/metadata insertion order, then require the
        # original issued-byte digest rather than treating JSON equality as SHA.
        data = json.loads(material['current_input_json'])
        pack = data['facts_and_provenance']
        source = SourceIndex.build(material['report'], pack)
        if source.prompt_sources() != data['source_index']:
            raise ValueError('sampling_complete_source_changed')
        inputs = ReviewInput(source, material['current_input_json'], compact(pack))
        baseline_request = TimedDocumentWorkflow.make_request(inputs)
        baseline_request = replace(baseline_request, timeout_s=preserved.timeout_s,
            metadata={**baseline_request.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
        request = identity.prepare_request(baseline_request, 'expanded_examples')
        if request != preserved:
            raise ValueError('sampling_baseline_contents_changed')
        if sha(identity.request_bytes(request)) != seal['original_file_sha256'][path]:
            raise ValueError('sampling_baseline_bytes_changed')
        baseline = sdk_payload(request)
        changed = replace(request, temperature=0.2)
        low = sdk_payload(changed)
        outside = dict(low, temperature=baseline['temperature'])
        if outside != baseline or baseline['temperature'] != 1.0 or low['temperature'] != 0.2:
            raise ValueError('sampling_payload_difference')
        if (low['top_p'] != 0.95 or low['model'] != 'glm-5.3'
                or low['max_tokens'] != 32768 or low['timeout'] != 600
                or low['extra_body'] != baseline['extra_body']):
            raise ValueError('sampling_other_parameters_changed')
        try:
            identity.request_bytes(changed)
        except ProviderResponseError as error:
            rejection = error.code
        except ValueError as error:
            rejection = str(error)
        else:
            raise ValueError('sampling_frozen_transport_unexpectedly_admitted')
        if rejection != 'document_identity_request_contract':
            raise ValueError('sampling_unexpected_rejection')
        review_path = stem + '/stage.json'
        review = seal['public_json_contents'][review_path]['journal']['parsed_review']
        rows.append(dict(sample=f'sample-{ordinal}', source_request_path=path,
            source_request_sha256=seal['original_file_sha256'][path],
            baseline_local_sdk_payload_sha256=sha(canonical(baseline)),
            changed_local_sdk_payload_sha256=sha(canonical(low)),
            differs_only=['temperature'], baseline_temperature=1.0,
            proposed_temperature=0.2, top_p=0.95, timeout_s=600,
            frozen_transport_rejection=rejection,
            actual_baseline_score=review['score'], actual_baseline_verdict=review['verdict']))
    if SEAL.read_bytes() != raw:
        raise ValueError('sampling_source_mutated')
    files = ['scripts/audit_document_sampling_boundary.py', 'scripts/document_semantic_request.py',
             'scripts/prepare_document_semantic_comparison.py', 'app/evaluation/golden_stream_bridge.py',
             'app/providers/zhipu.py', 'app/providers/zhipu_stream_adapter.py']
    return dict(kind='document-sampling-boundary-offline-audit-v1',
        source_seal_path=SEAL.relative_to(ROOT).as_posix(), source_seal_sha256=sha(raw),
        source_code_sha256={p: sha((ROOT / p).read_bytes()) for p in files},
        samples=rows, provider_calls=0, credential_reads=0, network_client_constructed=False,
        raw_run_read=False, execution_ready=False, production_admitted=False, new_qualification=0,
        limitation='SDK kwargs are captured by an entirely local recorder, not HTTP wire evidence. '
                   'Changed-temperature kwargs bypass only the frozen request validator in this offline '
                   'construction witness; all five changed requests are rejected by that validator. '
                   'Provider acceptance, parameter honoring and semantic effects are untested. '
                   'No causal explanation, stable quality, runnable identity or paid authorization follows.')


if __name__ == '__main__':
    value = audit()
    write_new_json(OUTPUT, value)
    print(json.dumps(dict(samples=len(value['samples']), provider_calls=0,
                          execution_ready=False, artifact_sha256=sha(OUTPUT.read_bytes()))))
