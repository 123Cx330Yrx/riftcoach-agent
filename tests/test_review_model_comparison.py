from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace as NS

import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_integrated_runtime import Exchange
from app.providers.errors import ProviderResponseError
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE, resolve_zhipu_thinking_profile
from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT
from scripts import run_review_model_comparison as runner
from scripts.prepare_review_model_comparison import sdk_arguments
from tests.test_golden_native_partitioned_tool_review import tool_response, valid_review
from tests.test_zhipu_stream_adapter import FakeClient, ClosableStream, chunk, usage, tool_fragment


def prepared():
    return [v for v in runner.prepare()[0] if v[0].endswith('-baseline')], runner.build_plan()


def fake_provider(responses):
    class Provider:
        model_name = 'glm-5.3'
        thinking_profile_id = ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE.profile_id
        transport_id = bridge.REVIEW_MODEL_TRANSPORT_ID
        sdk_max_retries = 0
        _calls = 0
        last_exchange = None

        def chat(self, request):
            response = responses[self._calls]
            self._calls += 1
            self.last_exchange = Exchange(request, response, hashlib.sha256(
                bridge.validate_request(request, transport_id=self.transport_id)).hexdigest())
            return response
    return Provider()


def decision(accepted):
    return lambda path, _: {'accepted': accepted, 'response_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def test_actual_full_model_stream_profile_matches_prepared_sdk_proposal(tmp_path):
    variants, _ = prepared()
    request = variants[0][2]
    chunks = [chunk(model='glm-5.3', tool_calls=[tool_fragment(index=0, call_id='call',
        name='submit_report_review', arguments=json.dumps(valid_review()))], finish_reason='tool_calls'),
        chunk(model='glm-5.3', raw_usage=usage())]
    raw = ClosableStream(chunks)
    client = FakeClient(raw)
    provider = ZhipuProvider.from_candidate_profile(client=client, model='glm-5.3',
        profile=ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE)
    response = bridge.collect(request,
        lambda r, hook: provider.stream_adapter(tool_stream=True,
            evaluation_request_policy=bridge.transport_request_policy(bridge.REVIEW_MODEL_TRANSPORT_ID)
        ).stream_session(r, include_usage_tail=True), directory=tmp_path,
        started=0, deadline=300, clock=lambda: 1, allow_tool_content=True,
        transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID)
    expected = sdk_arguments(request)
    expected['model'] = 'glm-5.3'
    expected['timeout'] = 299  # collect subtracts elapsed time before opening.
    assert client.completions.calls == [expected]
    assert response.model == 'glm-5.3' and raw.closed
    assert resolve_zhipu_thinking_profile('glm-5.3').reasoning_effort == 'low'
    with pytest.raises(ValueError):
        CONTEXT_COACH_CONTRACT.require_provider(provider)
    with pytest.raises(ValueError):
        bridge.GoldenProcessStreamProvider(settings=NS(model='glm-5.3',
            base_url='https://open.bigmodel.cn/api/paas/v4'), directory=tmp_path)


def test_capacity_exception_requires_exact_diagnostic_identity():
    from app.model_runtime import _issue_candidate_evaluation_request_policy
    with pytest.raises(ValueError):
        _issue_candidate_evaluation_request_policy(policy_id='glm-5.3-flash-coach-high-32768',
            version='1.0.0', provider_id='zhipu', model='glm-5.3', agent_timeout_s=330,
            llm_tool_timeout_s=330, transport_timeout_s=360, max_output_tokens=32768,
            temperature=1, top_p=.95)


@pytest.mark.parametrize('model,accepted', [('glm-5.3', True), ('glm-5.3-flash', False)])
def test_child_validates_response_against_selected_transport(tmp_path, model, accepted):
    import sys
    from pydantic import TypeAdapter
    from app.providers.models import ChatResponse
    response = replace(tool_response(valid_review()), model=model)
    body = TypeAdapter(ChatResponse).dump_json(response).decode()
    code = 'import sys; sys.stdout.write(' + repr(body) + ')'
    operation = lambda: bridge.run_child([sys.executable, '-c', code], b'{}', directory=tmp_path,
        timeout_s=10, transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID)
    if accepted:
        assert operation().model == model
    else:
        with pytest.raises(ProviderResponseError):
            operation()


def test_semantic_rejection_stops_before_second_call_and_retains_response(tmp_path):
    variants, plan = prepared()
    provider = fake_provider([replace(tool_response(valid_review(advisory=True)), model='glm-5.3')])
    result = runner.observe(provider, tmp_path, variants, plan, adjudicate=decision(False))
    assert result['error_code'] == 'model_comparison_semantic_failure'
    assert result['reserved_calls'] == 1 and result['unknown_usage_calls'] == 0
    assert (tmp_path / variants[0][0] / 'response.json').exists()
    assert not (tmp_path / variants[1][0]).exists()


def test_two_host_accepted_controls_share_one_bounded_batch(tmp_path):
    from app.providers.models import TokenUsage
    variants, plan = prepared()
    provider = fake_provider([replace(tool_response(valid_review()), model='glm-5.3', usage=TokenUsage(10, 10, 9))] * 2)
    second = plan['cells'][1]
    plan['proposed_diagnostic_budget']['total_token_reservation'] = second['input_reservation'] + second['output_cap'] + 20
    result = runner.observe(provider, tmp_path, variants, plan, adjudicate=decision(True))
    assert result['pair_accepted'] and result['reserved_calls'] == 2
    assert result['input_tokens'] == result['output_tokens'] == 20
    assert result['production_admitted'] is False


def test_host_review_time_cannot_reset_shared_deadline(tmp_path):
    variants, plan = prepared()
    provider = fake_provider([replace(tool_response(valid_review()), model='glm-5.3')])
    now = [0]

    def delayed(path, remaining):
        now[0] = 601
        return decision(True)(path, remaining)

    result = runner.observe(provider, tmp_path, variants, plan, adjudicate=delayed, clock=lambda: now[0])
    assert result['error_code'] == 'model_comparison_shared_budget'
    assert result['reserved_calls'] == 1 and result['unknown_usage_calls'] == 0


def test_protocol_failure_does_not_get_host_approval_or_second_call(tmp_path):
    variants, plan = prepared()
    provider = fake_provider([replace(tool_response({'score': 90}), model='glm-5.3')])

    def forbidden(*_):
        raise AssertionError('invalid output reached semantic acceptance')

    result = runner.observe(provider, tmp_path, variants, plan, adjudicate=forbidden)
    assert result['reserved_calls'] == 1 and not result['cases'][0]['valid']
    assert result['completed_calls'] == 1 and result['unknown_usage_calls'] == 0


@pytest.mark.parametrize('known', [False, True])
def test_rejected_transport_preserves_known_or_unknown_usage(tmp_path, known):
    from app.evaluation.golden_journal import write_new_json
    variants, plan = prepared()
    provider = fake_provider([])

    def fail(request):
        provider._calls += 1
        if known:
            stream = tmp_path / 'transport/stream-001'
            stream.mkdir(parents=True)
            write_new_json(stream / 'reservation.json', {'ordinal': 1,
                'transport_id': bridge.REVIEW_MODEL_TRANSPORT_ID, 'state': 'reserved_before_io',
                'request_sha256': hashlib.sha256(bridge.validate_request(request, transport_id=bridge.REVIEW_MODEL_TRANSPORT_ID)).hexdigest()})
            write_new_json(stream / 'result.json', {'transport_id': bridge.REVIEW_MODEL_TRANSPORT_ID, 'state': 'failed'})
            write_new_json(stream / 'progress.json', bridge.CapacityBridgeObservation(input_tokens=123, output_tokens=456).model_dump(mode='json'))
        raise ProviderResponseError(provider='zhipu', code='stream_child_failed')

    provider.chat = fail
    result = runner.observe(provider, tmp_path, variants, plan)
    assert result['reserved_calls'] == 1 and result['completed_calls'] == 0
    assert result['unknown_usage_calls'] == (0 if known else 1)
    assert result['input_tokens'] == (123 if known else 0)


def test_ci_gate_precedes_directory_and_credentials(monkeypatch):
    def refuse(_):
        raise ValueError('exact_sha_public_ci_required')
    monkeypatch.setattr(runner, 'verify_public_ci', refuse)
    monkeypatch.setattr(runner, 'LIVE_STATUS', 'approved_bounded_diagnostic_after_exact_ci')
    monkeypatch.setattr(runner, 'RUN_DIRECTORY', NS(mkdir=lambda **_: pytest.fail('created run before CI')))
    with pytest.raises(ValueError, match='exact_sha_public_ci_required'):
        runner.run(NS(execute=True, ci_run='wrong', env_file=None))


def test_stopped_batch_refuses_before_sources_ci_or_credentials(monkeypatch):
    def forbidden(*_):
        pytest.fail('closed batch accessed preparation or CI')
    monkeypatch.setattr(runner, 'build_plan', forbidden)
    monkeypatch.setattr(runner, 'verify_public_ci', forbidden)
    with pytest.raises(ValueError, match='model_comparison_closed_no_retry'):
        runner.run(NS(execute=True, ci_run='', env_file=None))


def test_actual_completed_response_remains_rejected_without_id_repair():
    artifact = json.loads((runner.ROOT / 'data/evaluation/results/golden_review_model_comparison_result_b6b30f8.json').read_text(encoding='utf-8'))
    response = artifact['original_json_contents']['attribution_original-baseline/response.json']
    arguments = response['tool_calls'][0]['arguments']
    assert arguments['issues'][0]['source_ids'] == [9, 13, 17, 8, 12, 16, 0]
    assert artifact['original_json_contents']['result.json']['reserved_calls'] == 1
    variants, _ = prepared()
    with pytest.raises(ValueError, match='semantic_source_id_unknown'):
        runner.review.validate(runner.compact(arguments), variants[0][1])
