import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import document_sampling_screening as screening
from scripts import document_sampling_screening_request as identity
from app.providers.models import ChatResponse, TokenUsage, ToolCall


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def test_sampling_plan_has_explicit_temperature_pairs():
    rows = screening.controls()
    assert len(rows) == 10
    assert [rows[i][0]['source_key'] for i in range(0, len(rows), 2)] == [
        'claim-scope:4', 'scope:3', 'scope:4', 'observed:3', 'observed:5']
    assert [rows[i][0]['expected_verdict'] for i in range(0, len(rows), 2)] == [
        'accept', 'accept', 'reject', 'accept', 'reject']
    for index in range(0, len(rows), 2):
        baseline, _, baseline_request = rows[index]
        candidate, _, candidate_request = rows[index + 1]
        assert baseline['variant'] == identity.BASELINE
        assert candidate['variant'] == identity.CANDIDATE
        assert baseline_request.max_tokens == candidate_request.max_tokens == 32768
        baseline_wire = json.loads(identity.request_bytes(baseline_request))
        candidate_wire = json.loads(identity.request_bytes(candidate_request))
        del baseline_wire['metadata'][identity.MARKER]
        candidate_wire['temperature'] = baseline_wire['temperature']
        del candidate_wire['metadata'][identity.MARKER]
        assert candidate_wire == baseline_wire
        assert baseline_request.temperature == 1.0
        assert candidate_request.temperature == 0.2
        assert candidate_request.metadata[identity.MARKER]['version'] == identity.VERSION


def test_isolated_bridge_keeps_timed_glm_profile_and_limit():
    bridge = identity.isolated_bridge()
    assert bridge.transport_profile(identity.TRANSPORT).model == 'glm-5.3'
    assert bridge.transport_limits(identity.TRANSPORT) == (32768, 600, 65536)


def test_offline_provider_receipt_binds_candidate_temperature_without_network(tmp_path):
    bridge = identity.isolated_bridge()
    observed = []

    def child(command, raw, *, directory, transport_id, **kwargs):
        observed.append((transport_id, raw))
        bridge.write_new_json(directory / 'result.json', {
            'transport_id': transport_id, 'state': 'complete', 'elapsed_ms': 1,
            'body_free': True})
        progress = bridge.TimedReviewBridgeObservation(
            state='complete', close_state='closed', http_requests=1,
            input_tokens=11, output_tokens=7, finish_reason='tool_calls',
            events=1, elapsed_ms=1)
        bridge.write_new_json(directory / 'progress.json', progress.model_dump())
        return ChatResponse(content=None, model='glm-5.3', provider='zhipu',
            usage=TokenUsage(11, 7), finish_reason='tool_calls',
            tool_calls=(ToolCall('fixture', 'submit_report_review', {}),))

    bridge.run_child = child
    provider = screening.transport.SemanticProvider(
        SimpleNamespace(model='glm-5.3', api_key='offline',
            base_url='https://open.bigmodel.cn/api/paas/v4'), bridge=bridge)
    rows = screening.controls()
    for row, _, request in rows[:2]:
        provider.chat(request, tmp_path / row['key'].replace(':', '-'))
    assert len(observed) == 2 and all(t == identity.TRANSPORT for t, _ in observed)
    assert json.loads(observed[0][1])['temperature'] == 1.0
    assert json.loads(observed[1][1])['temperature'] == 0.2
    for row, _, _ in rows[:2]:
        receipt = json.loads((tmp_path / row['key'].replace(':', '-') / 'receipt.json').read_text())
        assert receipt['transport_id'] == identity.TRANSPORT
        assert receipt['model'] == 'glm-5.3'


def test_sampling_replay_rejects_request_tampering_and_preserves_shared_entrypoint(tmp_path):
    # The diagnostic's isolated identity may add its own marker, but it must
    # never mutate the production review request module or accept a replay
    # whose issued bytes no longer match the bound candidate request.
    from scripts import document_semantic_request as shared
    shared_transport = shared.TRANSPORT
    bridge = identity.isolated_bridge()

    def child(command, raw, *, directory, transport_id, **kwargs):
        bridge.write_new_json(directory / 'result.json', {
            'transport_id': transport_id, 'state': 'complete', 'elapsed_ms': 1,
            'body_free': True})
        bridge.write_new_json(directory / 'progress.json',
            bridge.TimedReviewBridgeObservation(
                state='complete', close_state='closed', http_requests=1,
                input_tokens=11, output_tokens=7, finish_reason='tool_calls',
                events=1, elapsed_ms=1).model_dump())
        return ChatResponse(content=None, model='glm-5.3', provider='zhipu',
            usage=TokenUsage(11, 7), finish_reason='tool_calls',
            tool_calls=(ToolCall('fixture', 'submit_report_review', {}),))

    bridge.run_child = child
    provider = screening.transport.SemanticProvider(
        SimpleNamespace(model='glm-5.3', api_key='offline',
            base_url='https://open.bigmodel.cn/api/paas/v4'), bridge=bridge)
    _, _, request = screening.controls()[1]
    folder = tmp_path / 'candidate'
    provider.chat(request, folder)
    issued = folder / 'issued-request.json'
    value = json.loads(issued.read_bytes())
    value['temperature'] = 1.0
    issued.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError, match='semantic_.*|sampling_.*'):
        screening.transport.validate_complete(
            folder, request,
            screening.RESPONSE.validate_json((folder / 'raw-response.json').read_bytes()))
    assert shared.TRANSPORT == shared_transport


def test_sampling_budget_is_five_glm_pairs_at_published_estimate():
    plan, rows = screening.prepare(root_thread_id='fixture-root', independent_thread_id='fixture-child')
    assert len(rows) == 10
    assert plan['budget']['max_calls'] == 10
    assert plan['budget']['role_calls'] == {'glm-5.3': 10}
    assert plan['budget']['estimated_uncached_cny'] == '14.29504'
    assert plan['budget']['per_request_seconds'] == 600
    assert plan['budget']['per_request_output'] == 32768


# This child is a real worker process.  It uses the repository's stream-test
# SDK fixture and fails closed if any socket connection is attempted.  The
# parent-side bridge below rewrites only the executable entrypoint, exactly as
# the production isolated bridge does; no provider or credential is involved.
_FAKE_SDK_CHILD = r'''
import json, socket, sys
from pathlib import Path
from types import SimpleNamespace as NS
import openai
from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage, tool_fragment
from app.providers import config

def forbidden(*args, **kwargs):
    raise AssertionError("offline_network_forbidden")
socket.socket.connect = forbidden
socket.create_connection = forbidden
config.load_zhipu_settings = lambda: NS(model="glm-5.3", api_key="OFFLINE_FIXTURE",
    base_url="https://open.bigmodel.cn/api/paas/v4")
raw = ClosableStream([
    chunk(model="glm-5.3", reasoning="FIXTURE_PRIVATE"),
    chunk(model="glm-5.3", tool_calls=[tool_fragment(index=0, call_id="fixture",
        call_type="function", name="submit_report_review",
        arguments='{"score":96,"verdict":"pass","issues":[],"issue_resolutions":[],"advisories":[]}')],
        finish_reason="tool_calls"),
    chunk(model="glm-5.3", raw_usage=usage()),
])
client = FakeClient(raw)
original = client.completions.create
def create(**kwargs):
    client.hook(NS(extensions={}))
    Path(sys.argv[sys.argv.index("--worker") + 1], "sdk-fixture.json").write_text(
        json.dumps(kwargs), encoding="utf-8")
    return original(**kwargs)
client.completions.create = create
def close():
    assert raw.closed
client.close = close
def factory(**kwargs):
    client.hook = kwargs["http_client"]._event_hooks["request"][0]
    return client
openai.OpenAI = factory
from scripts.document_sampling_screening_request import main
main()
'''


def test_real_sampling_worker_sdk_receives_only_temperature_delta_and_no_network(tmp_path, monkeypatch):
    bridge = identity.isolated_bridge()
    original_popen = bridge.subprocess.Popen

    def child(command, **kwargs):
        marker = command.index('-m')
        command = [*command[:marker], '-c', _FAKE_SDK_CHILD, *command[marker + 2:]]
        return original_popen(command, **kwargs)

    monkeypatch.setattr(bridge.subprocess, 'Popen', child)
    settings = SimpleNamespace(model='glm-5.3', api_key='OFFLINE_FIXTURE',
        base_url='https://open.bigmodel.cn/api/paas/v4')
    provider = screening.transport.SemanticProvider(settings, bridge=bridge)
    rows = screening.controls()[:2]
    sdk_payloads = []
    for row, _, request in rows:
        directory = tmp_path / row['key'].replace(':', '-')
        provider.chat(request, directory)
        sdk = json.loads((directory / 'stream-001' / 'sdk-fixture.json').read_text())
        sdk_payloads.append(sdk)
    assert [payload['temperature'] for payload in sdk_payloads] == [1.0, 0.2]
    assert all(payload['model'] == 'glm-5.3' for payload in sdk_payloads)
    assert all(payload['top_p'] == .95 and payload['max_tokens'] == 32768
               for payload in sdk_payloads)
    assert all('metadata' not in payload for payload in sdk_payloads)


class _ObserveProvider:
    """Small fully receipted transport fixture for runner control-flow tests."""

    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def chat(self, request, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        raw = identity.request_bytes(request)
        (directory / 'issued-request.json').write_bytes(raw)
        self.calls.append(request)
        if self.fail_at is not None and len(self.calls) == self.fail_at:
            raise ValueError('fixture_hard_transport_failure')
        stream = directory / 'stream-001'
        stream.mkdir()
        bridge = identity.isolated_bridge()
        from app.evaluation.golden_journal import write_new_json
        write_new_json(stream / 'reservation.json', dict(
            transport_id=identity.TRANSPORT, ordinal=1, request_sha256=_sha(raw),
            stream_tool_arguments=True, state='reserved_before_io',
            request_metrics=bridge.request_metrics(request, raw), model='glm-5.3',
            thinking_profile_id=bridge.transport_profile(identity.TRANSPORT).profile_id))
        response = ChatResponse(content=None, model='glm-5.3', provider='zhipu',
            usage=TokenUsage(11, 7), finish_reason='tool_calls',
            tool_calls=(ToolCall('fixture', 'submit_report_review', {}),))
        from app.evaluation.golden_stream_bridge import RESPONSE, TimedReviewBridgeObservation
        (directory / 'raw-response.json').write_bytes(RESPONSE.dump_json(response))
        write_new_json(stream / 'result.json', dict(transport_id=identity.TRANSPORT,
            state='complete', elapsed_ms=1, body_free=True))
        write_new_json(stream / 'progress.json', TimedReviewBridgeObservation(
            state='complete', close_state='closed', http_requests=1,
            input_tokens=11, output_tokens=7, finish_reason='tool_calls', events=1,
            elapsed_ms=1).model_dump())
        write_new_json(directory / 'receipt.json', screening.transport.validate_complete(
            directory, request, response))
        return response


def _observe_fixture(monkeypatch, tmp_path, fail_at=None, reject_at=None):
    rows = screening.controls()[:4]
    plan = dict(
        kind='fixture', run_id='fixture', cells=[r for r, _, _ in rows],
        sequence=[r['key'] for r, _, _ in rows], plan_sha256='f' * 64,
        max_host_seconds=86400,
        budget=dict(max_calls=4, max_tokens=967680, max_active_seconds=3000,
                    per_request_seconds=600, per_request_output=32768),
        review_principals={'primary': {'principal_id': 'fixture-root'},
                           'independent': {'principal_id': 'fixture-child'}},
        host_review_evidence_policy='fixture',
    )
    # Keep the real observe loop, but isolate the host/native boundary with a
    # deterministic fixture.  These replacements do not weaken transport or
    # request validation; they only provide an offline review result.
    runner = screening.runner
    monkeypatch.setattr(runner, 'inputs_for', lambda cell, material: None)
    monkeypatch.setattr(runner.host, 'stage_for',
        lambda cell, inputs, request, response: (
            SimpleNamespace(score=96, verdict='pass'),
            {'stage': cell['stage'], 'report': material_for(cell), 'journal': {}}))
    monkeypatch.setattr(runner, 'task_for', lambda directory, key: '{}')
    # Observe must still publish a checkpoint; create a valid immutable fixture
    # at the expected path and return its digest.
    def publish(path, source, reviewer):
        Path(path).write_bytes(Path(source).read_bytes())
        return _sha(Path(path).read_bytes())
    monkeypatch.setattr(runner.checkpoint, 'publish', publish)
    monkeypatch.setattr(runner.checkpoint, 'dispatch', lambda path, pin: 'fixture-dispatch')
    monkeypatch.setattr(runner, 'validate_submission',
        lambda directory, key, submission, source: key != rows[reject_at][0]['key']
        if reject_at is not None else True)
    monkeypatch.setattr(runner, 'outcome',
        lambda cell, wire, bound, submission, accepted: dict(
            key=cell['key'], variant=cell['variant'], temperature=cell['temperature'],
            binding=bound, score=wire.score, verdict=wire.verdict,
            expected_verdict=cell['expected_verdict'], verdict_matched=True,
            primary_accepted=True, independent_accepted=accepted,
            host_disagreement=not accepted, semantic_accepted=accepted,
            new_qualification=0))
    monkeypatch.setattr(runner, 'task_for', lambda directory, key: '{}')

    def material_for(cell):
        return 'offline fixture report for ' + cell['key']

    return plan, rows


def test_observe_records_semantic_rejection_and_continues_next_pair(tmp_path, monkeypatch):
    plan, rows = _observe_fixture(monkeypatch, tmp_path, reject_at=1)
    provider = _ObserveProvider()
    result = screening.runner.observe(tmp_path, plan, rows, provider, object(),
                                      adjudicate=lambda *args: {})
    assert result['scan_completed'] is True, result
    assert len(provider.calls) == 4
    assert len(result['completed']) == 4
    assert result['completed'][1]['semantic_accepted'] is False
    assert result['completed'][2]['key'] == rows[2][0]['key']


def test_observe_hard_transport_failure_stops_without_retry(tmp_path, monkeypatch):
    plan, rows = _observe_fixture(monkeypatch, tmp_path)
    provider = _ObserveProvider(fail_at=2)
    result = screening.runner.observe(tmp_path, plan, rows, provider, object(),
                                      adjudicate=lambda *args: {})
    assert result['scan_completed'] is False, result
    assert len(provider.calls) == 2, result
    assert result['first_deviation']['key'] == rows[1][0]['key']
    assert result['unexecuted'] == [rows[2][0]['key'], rows[3][0]['key']]
