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
