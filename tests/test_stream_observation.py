import json

import httpx
import pytest

from scripts.stream_observation import ROOT, StreamObservation


class Stream(httpx.SyncByteStream):
    def __init__(self, error=None):
        self.error, self.closed = error, 0

    def __iter__(self):
        yield b'PRIVATE-body-and-reasoning'
        if self.error:
            raise self.error

    def close(self):
        self.closed += 1


@pytest.mark.parametrize('error', [None, httpx.ReadTimeout('PRIVATE-error'),
    httpx.ReadError('PRIVATE-error'), httpx.RemoteProtocolError('PRIVATE-error')])
def test_observer_preserves_bytes_errors_and_close_without_recording_content(tmp_path, error):
    obs = StreamObservation(tmp_path / 'observation')
    raw = Stream(error)
    request = httpx.Request('POST', 'https://example.invalid/PRIVATE-url',
        headers={'Authorization': 'PRIVATE-credential'},
        extensions={'timeout': {'read': 10}})
    response = httpx.Response(200, request=request, stream=raw,
        headers={'x-request-id': 'bad id PRIVATE-header'})
    obs.on_request(request)
    obs.on_response(response)
    iterator = iter(response.stream)
    assert next(iterator) == b'PRIVATE-body-and-reasoning'
    if error:
        with pytest.raises(type(error)) as caught:
            next(iterator)
        assert caught.value is error
    else:
        with pytest.raises(StopIteration):
            next(iterator)
    response.close()
    obs.close()
    text = (obs.directory / 'observation.json').read_text()
    value = json.loads(text)
    assert 'PRIVATE' not in text
    assert raw.closed == 1 and value['closed']
    assert value['raw_bytes'] == len(b'PRIVATE-body-and-reasoning')
    assert value['response_request_id'] is None
    assert value['timeout'] == {'read': 10}
    assert value['exception_type'] is not None if error else value['eof']
    assert obs.failure is None


def test_rejects_run_evidence_and_existing_output_before_writes(tmp_path):
    with pytest.raises(ValueError, match='outside_run_evidence'):
        StreamObservation(ROOT / 'data/runs/never-create-observation')
    with pytest.raises(FileExistsError):
        StreamObservation(tmp_path)


def test_observation_write_failure_is_visible_and_does_not_mask_stream_result(tmp_path, monkeypatch):
    obs = StreamObservation(tmp_path / 'observation')
    def fail():
        raise OSError('PRIVATE-path')
    monkeypatch.setattr(obs, '_save', fail)
    obs.close()
    assert obs.failure == 'observation_write_failed'


def test_preheader_failure_is_recorded_as_fixed_category(tmp_path):
    obs = StreamObservation(tmp_path / 'preheader')
    request = httpx.Request('POST', 'https://example.invalid/responses')
    obs.on_request(request)
    obs.mark_failure('connect_error')
    obs.close()
    value = json.loads((obs.directory / 'observation.json').read_text())
    assert value['phase'] == 'response_headers_failed'
    assert value['exception_type'] == 'connect_error'
    assert value['response_status'] is None


def test_gateway_timing_distinguishes_headers_first_bytes_and_empty_chunks(tmp_path):
    now = [0.0]
    obs = StreamObservation(tmp_path / 'timing', clock=lambda: now[0])
    class TimedStream(httpx.SyncByteStream):
        def __iter__(self):
            now[0] = 120.2
            yield b''
            now[0] = 120.3
            yield b'PRIVATE-error-body'
            now[0] = 125.0
            yield b'PRIVATE-tail'
    now[0] = .1
    obs.on_request(httpx.Request('POST', 'https://example.invalid'))
    now[0] = 120.1
    response = httpx.Response(524, stream=TimedStream(), headers={
        'cf-ray': 'a52b9ffb8c98d774-NRT', 'set-cookie': 'PRIVATE-cookie'})
    obs.on_response(response)
    assert response.read() == b'PRIVATE-error-bodyPRIVATE-tail'
    response.close()
    obs.close()
    text = (obs.directory / 'observation.json').read_text()
    value = json.loads(text)
    assert value['request_started_ms'] == 100
    assert value['response_headers_ms'] == 120100
    assert value['first_bytes_ms'] == 120300
    assert value['last_bytes_ms'] == 125000
    assert value['response_cf_ray'] == 'a52b9ffb8c98d774-NRT'
    assert value['response_status'] == 524 and value['eof'] and value['closed']
    assert 'PRIVATE' not in text


@pytest.mark.parametrize('ray', ['PRIVATE-header', 'a' * 1000, 'a52b9ffb8c98d774-NRT PRIVATE'])
def test_unrecognized_gateway_header_is_not_retained(tmp_path, ray):
    obs = StreamObservation(tmp_path / 'invalid-header')
    response = httpx.Response(524, stream=Stream(), headers={'cf-ray': ray})
    obs.on_response(response)
    response.close()
    obs.close()
    value = json.loads((obs.directory / 'observation.json').read_text())
    assert value['response_cf_ray'] is None
    assert value['first_bytes_ms'] is None
