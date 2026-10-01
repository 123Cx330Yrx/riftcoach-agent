import hashlib
import json
import os
from dataclasses import replace

import pytest

from app.providers.errors import ProviderTimeoutError
from scripts import diagnose_block_review_route as diagnostic
from tests.test_golden_native_block_tool_review import grouped
from tests.test_golden_native_partitioned_tool_review import exchange_provider, tool_response, valid_review


def test_same_original_request_bytes_from_committed_sources(monkeypatch):
    from pathlib import Path
    original = Path.open
    def committed(path, *args, **kwargs):
        assert 'data/runs/' not in path.as_posix()
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', committed)
    request, _ = diagnostic.prepare()
    raw = diagnostic.validate_request(request, transport_id=diagnostic.CAPACITY_TRANSPORT_ID)
    assert hashlib.sha256(raw).hexdigest() == diagnostic.REQUEST_SHA
    assert request.timeout_s == 300 and request.max_tokens == 32768


@pytest.mark.parametrize('route', ['direct', 'proxy_12000'])
def test_proxy_override_is_restored_on_exception(route, monkeypatch):
    from httpx._utils import get_environment_proxies
    monkeypatch.setenv('https_proxy', 'http://localhost:12345')
    monkeypatch.setenv('NO_PROXY', '*')
    before = dict(os.environ)
    with pytest.raises(RuntimeError):
        with diagnostic.route_environment(route):
            routes = get_environment_proxies()
            if route == 'direct':
                assert 'https://' not in routes and 'all://' not in routes
            else:
                assert routes['https://'] == 'http://127.0.0.1:12000'
                assert 'NO_PROXY' not in os.environ
            raise RuntimeError('scripted')
    assert dict(os.environ) == before


def test_timeout_stops_without_second_route_and_keeps_unknown_charge(tmp_path):
    request, inputs = diagnostic.prepare()
    class Failed:
        _calls = 0
        def chat(self, request):
            self._calls += 1
            raise ProviderTimeoutError(provider='zhipu', code='stream_deadline')
    result = diagnostic.observe(tmp_path, request, inputs, lambda _: Failed())
    assert result['reserved_calls'] == result['unknown_usage_calls'] == 1
    assert not (tmp_path / 'proxy_12000').exists()
    assert result['cases'][0]['error_code'] == 'stream_deadline'


def test_pair_keeps_complete_public_responses_and_does_not_claim_quality(tmp_path):
    request, inputs = diagnostic.prepare()
    def factory(_):
        response = replace(tool_response(grouped(valid_review(), len(inputs.source.blocks))),
            reasoning_content='private reasoning must not be published')
        provider = exchange_provider([response])
        provider._calls = 1
        return provider
    result = diagnostic.observe(tmp_path, request, inputs, factory)
    assert result['reserved_calls'] == 2 and result['unknown_usage_calls'] == 0
    assert all(r['valid'] for r in result['cases'])
    assert not result['semantic_approval'] and not result['production_admitted']
    assert 'private reasoning' not in json.dumps(result)


def test_failed_assembly_keeps_observed_usage_and_single_diagnostic_call(tmp_path):
    from app.evaluation.golden_stream_bridge import CapacityBridgeObservation
    request, inputs = diagnostic.prepare()
    class Failed:
        _calls = 0
        def __init__(self, path):
            self.path = path
        def chat(self, request):
            self._calls = 1
            stream = self.path / 'stream-001'
            stream.mkdir(parents=True)
            (stream / 'progress.json').write_text(CapacityBridgeObservation(
                input_tokens=12307, output_tokens=5791).model_dump_json())
            raise ProviderTimeoutError(provider='zhipu', code='stream_child_failed')
    result = diagnostic.observe(tmp_path, request, inputs, Failed, argument_diagnostic=True)
    assert result['reserved_calls'] == 1 and result['unknown_usage_calls'] == 0
    assert result['input_tokens'] == 12307 and result['output_tokens'] == 5791
    assert result['cases'][0]['usage_source'] == 'normalized_stream_usage'
    assert not result['cases'][0]['completed']
