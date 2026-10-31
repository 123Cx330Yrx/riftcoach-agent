"""Offline execution tests; synthetic streams never assert Flash review quality."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from types import SimpleNamespace as NS

import httpx
from openai import OpenAI
import pytest

from app.evaluation import golden_stream_bridge as bridge
from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.providers.config import ZhipuSettings
from app.providers.zhipu import ZhipuProvider
from app.providers.zhipu_profiles import (
    ZHIPU_GLM53_FLASH_HIGH_CANDIDATE_PROFILE as FLASH,
    ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE as GLM,
)
from scripts import run_flash_source_review_pair as cli
from scripts import run_native_coach_product as product
from scripts import run_review_model_comparison as runner
from scripts.prepare_role_qualification import PAIR_EVIDENCE
from tests.test_review_model_comparison import fake_provider, decision


@pytest.fixture(scope='module')
def pair():
    return cli.prepare_pair()


@pytest.fixture(scope='module')
def responses():
    saved = json.loads(PAIR_EVIDENCE.read_text(encoding='utf-8'))['original_json_contents']
    return [replace(bridge.RESPONSE.validate_python(saved[name + '/response.json']),
        model='glm-5.3-flash') for name in (
            'attribution_original-baseline', 'attribution_corrected-baseline')]


def flash_provider(responses):
    provider = fake_provider(responses)
    provider.model_name = FLASH.model
    provider.thinking_profile_id = FLASH.profile_id
    provider.transport_id = bridge.CAPACITY_TRANSPORT_ID
    return provider


def observe(provider, directory, pair, **kwargs):
    return runner.observe(provider, directory, *pair, reviewer_profile=FLASH,
        transport_id=bridge.CAPACITY_TRANSPORT_ID, **kwargs)


def test_prepared_request_bytes_match_actual_completed_glm_reservations(pair):
    variants, plan = pair
    saved = json.loads(PAIR_EVIDENCE.read_text(encoding='utf-8'))['original_json_contents']
    assert plan['candidate']['roles']['review']['model'] == 'glm-5.3'
    for ordinal, ((name, _, request), cell) in enumerate(zip(variants, plan['cells'], strict=True), 1):
        raw = bridge.validate_request(request, transport_id=bridge.CAPACITY_TRANSPORT_ID)
        assert hashlib.sha256(raw).hexdigest() == saved[f'transport/stream-{ordinal:03d}/reservation.json']['request_sha256']
        assert json.loads(raw) == saved[name + '/request.json']
        assert 'expected_host_only' not in raw.decode()
        assert cell['sdk_body']['model'] == FLASH.model


def test_actual_receipted_flash_sdk_stream_and_inputs(pair, responses, tmp_path, monkeypatch):
    """Run real SDK through MockTransport; preserve the real process selector."""
    sent = []

    def child(command, raw, *, directory, timeout_s, environ, transport_id):
        assert transport_id == bridge.CAPACITY_TRANSPORT_ID
        assert environ['LLM_MODEL'] == FLASH.model
        assert command[-1] == bridge.CAPACITY_TRANSPORT_ID
        request = bridge.REQUEST.validate_json(raw)
        index = len(sent)
        call = responses[index].tool_calls[0]
        payload = dict(id=f'offline-{index}', object='chat.completion.chunk', created=1,
            model=FLASH.model, choices=[dict(index=0, delta=dict(tool_calls=[dict(index=0,
                id=call.id, type='function', function=dict(name=call.name,
                    arguments=json.dumps(call.arguments, ensure_ascii=False)))]), finish_reason='tool_calls')])
        tail = dict(id=f'offline-{index}', object='chat.completion.chunk', created=1,
            model=FLASH.model, choices=[], usage=dict(prompt_tokens=10, completion_tokens=10, total_tokens=20))
        data = ''.join('data: ' + json.dumps(item, ensure_ascii=False) + '\n\n' for item in (payload, tail)) + 'data: [DONE]\n\n'

        def handle(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=data.encode())

        with httpx.Client(transport=httpx.MockTransport(handle)) as http:
            with OpenAI(api_key='offline-placeholder', base_url='https://offline.invalid/v4/',
                        http_client=http, max_retries=0) as sdk:
                adapter = ZhipuProvider.from_candidate_profile(client=sdk, model=environ['LLM_MODEL'],
                    profile=bridge.transport_profile(transport_id)).stream_adapter(tool_stream=True,
                        evaluation_request_policy=bridge.transport_request_policy(transport_id))
                response = bridge.collect(request,
                    lambda issued, hook: adapter.stream_session(issued, include_usage_tail=True),
                    directory=directory, started=0, deadline=timeout_s, clock=lambda: 1,
                    allow_tool_content=True, transport_id=transport_id)
        write_new_json(directory / 'result.json', dict(state='complete', transport_id=transport_id))
        return response

    monkeypatch.setattr(bridge, 'run_child', child)
    provider = ReceiptedStreamProvider(settings=NS(model=FLASH.model,
        base_url='https://open.bigmodel.cn/api/paas/v4', api_key='offline-placeholder'),
        directory=tmp_path / 'transport', transport_id=bridge.CAPACITY_TRANSPORT_ID)
    result = observe(provider, tmp_path, pair, adjudicate=decision(True))
    assert result['pair_accepted'] and result['reserved_calls'] == 2
    assert not result['production_admitted']
    assert sent == [cell['sdk_body'] for cell in pair[1]['cells']]
    assert result['input_tokens'] == result['output_tokens'] == 20
    for name, _, _ in pair[0]:
        arm = tmp_path / name
        accounting = json.loads((arm / 'accounting.json').read_text())
        assert hashlib.sha256((arm / 'request.raw.json').read_bytes()).hexdigest() == accounting['request_sha256']


@pytest.mark.parametrize('attribute,value', [
    ('model_name', 'glm-5.3'), ('thinking_profile_id', GLM.profile_id),
    ('transport_id', bridge.REVIEW_MODEL_TRANSPORT_ID), ('sdk_max_retries', 1), ('_calls', 1),
])
def test_flash_identity_rejected_before_calls(pair, responses, tmp_path, attribute, value):
    provider = flash_provider(responses)
    setattr(provider, attribute, value)
    before = provider._calls
    with pytest.raises(ValueError, match='model_comparison_identity'):
        observe(provider, tmp_path, pair)
    assert provider._calls == before and not list(tmp_path.iterdir())


def test_profile_cannot_be_forged_by_reusing_profile_id(pair, responses, tmp_path):
    with pytest.raises(ValueError, match='model_comparison_identity'):
        runner.observe(flash_provider(responses), tmp_path, *pair,
            reviewer_profile=replace(FLASH, reasoning_effort='low'), transport_id=bridge.CAPACITY_TRANSPORT_ID)


@pytest.mark.parametrize('accepted', [False, None])
def test_first_host_reject_or_no_acceptance_never_sends_second(pair, responses, tmp_path, accepted):
    def adjudicate(path, remaining):
        if accepted is None:
            raise ValueError('model_comparison_host_deadline')
        return decision(accepted)(path, remaining)
    result = observe(flash_provider(responses), tmp_path, pair, adjudicate=adjudicate)
    assert result['reserved_calls'] == 1 and not result['pair_accepted']
    assert not (tmp_path / pair[0][1][0]).exists()


def test_host_wait_cannot_reset_shared_deadline(pair, responses, tmp_path):
    now = [0]
    def adjudicate(path, remaining):
        assert remaining == 600
        now[0] = 601
        return decision(True)(path, remaining)
    result = observe(flash_provider(responses), tmp_path, pair, adjudicate=adjudicate, clock=lambda: now[0])
    assert result['reserved_calls'] == 1 and result['error_code'] == 'model_comparison_shared_budget'


def test_unknown_source_stops_before_host_and_second_call(pair, responses, tmp_path):
    bad = deepcopy(responses[0].tool_calls[0].arguments)
    bad['issues'][0]['source_ids'] = [9999]
    response = replace(responses[0], tool_calls=(replace(responses[0].tool_calls[0], arguments=bad),))
    result = observe(flash_provider([response]), tmp_path, pair,
        adjudicate=lambda *_: pytest.fail('invalid sources reached host acceptance'))
    assert result['reserved_calls'] == 1 and not result['pair_accepted']
    assert result['error_code'] == 'semantic_source_id_unknown'


def test_existing_receipt_batch_is_never_overwritten(pair, responses, tmp_path):
    provider = flash_provider(responses)
    (tmp_path / 'result.json').write_bytes(b'old-receipt')
    with pytest.raises(ValueError, match='model_comparison_batch_exists'):
        observe(provider, tmp_path, pair)
    assert provider._calls == 0 and (tmp_path / 'result.json').read_bytes() == b'old-receipt'


def test_default_preview_never_reads_credentials_checks_ci_or_creates_provider(pair, monkeypatch, tmp_path):
    monkeypatch.setattr(cli, 'prepare_pair', lambda: pair)
    monkeypatch.setattr(cli, 'verify_public_ci', lambda *_: pytest.fail('preview contacted CI'))
    monkeypatch.setattr(cli, 'ReceiptedStreamProvider', lambda **_: pytest.fail('preview built provider'))
    monkeypatch.setattr(cli, 'RUN_DIRECTORY', tmp_path / 'must-not-exist')
    args = cli.parser().parse_args([])
    result = cli.run(args)
    assert not result['execution_enabled'] and result['provider_requests'] == 0
    assert not (tmp_path / 'must-not-exist').exists()


@pytest.mark.parametrize('kind', ['raw', 'hash', 'input', 'budget'])
def test_prepared_drift_rejected_before_ci_credentials_or_provider(pair, monkeypatch, kind):
    plan, raw = cli.prepare_comparison()
    if kind == 'raw':
        raw[plan['cells'][0]['id']] += b' '
    elif kind == 'hash':
        plan['cells'][0]['request_sha256'] = '0' * 64
    elif kind == 'input':
        plan['cells'][0]['input_sha256'] = '0' * 64
    else:
        plan['proposed_diagnostic_budget']['max_calls'] = 3
    monkeypatch.setattr(cli, 'prepare_comparison', lambda: (plan, raw))
    monkeypatch.setattr(cli, 'verify_public_ci', lambda *_: pytest.fail('drift contacted CI'))
    monkeypatch.setattr(cli, 'ReceiptedStreamProvider', lambda **_: pytest.fail('drift built provider'))
    with pytest.raises(ValueError, match='flash_source_comparison_(input_changed|plan_identity)'):
        cli.prepare_pair()


def test_closed_historical_batch_stops_before_prepare_ci_or_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, 'RUN_DIRECTORY', tmp_path / 'never-created')
    for name in ('prepare_pair', 'verify_public_ci', 'ReceiptedStreamProvider'):
        monkeypatch.setattr(cli, name, lambda *a, **k: pytest.fail('closed batch attempted IO'))
    with pytest.raises(ValueError, match='flash_source_comparison_batch_closed'):
        cli.run(NS(execute=True))
    assert not cli.RUN_DIRECTORY.exists()


def test_terminal_requires_exact_hash_and_never_infers_verdict(tmp_path, monkeypatch):
    response = tmp_path / 'response.json'
    response.write_text('{"verdict":"pass"}')
    monkeypatch.setattr(runner.sys, 'stdin', io.StringIO('accept wrong-sha\n'))
    with pytest.raises(ValueError, match='model_comparison_host_decision_invalid'):
        runner.terminal_adjudication(response, 1)
    sha = hashlib.sha256(response.read_bytes()).hexdigest()
    monkeypatch.setattr(runner.sys, 'stdin', io.StringIO(f'accept {sha}\n'))
    assert runner.terminal_adjudication(response, 1)['accepted']


@pytest.mark.parametrize('real_settings', [False, True])
def test_reviewer_model_copy_keeps_credentials_endpoint_timeout(real_settings):
    values = dict(model='glm-5.3-flash', base_url='https://open.bigmodel.cn/api/paas/v4',
        api_key='offline-placeholder', default_timeout_s=123)
    settings = ZhipuSettings(**values) if real_settings else NS(**values)
    reviewer = product.reviewer_settings_from(settings)
    assert reviewer.model == 'glm-5.3' and settings.model == 'glm-5.3-flash'
    assert reviewer.api_key == settings.api_key
    assert reviewer.base_url == settings.base_url
    assert reviewer.default_timeout_s == settings.default_timeout_s
