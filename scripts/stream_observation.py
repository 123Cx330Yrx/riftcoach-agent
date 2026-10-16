"""Prospective, opt-in body-free HTTP observation outside run evidence.

This does not change timeouts, retry policy, payloads or stream outcomes. Raw
byte activity and a sampler independent of SDK yields distinguish idle IO from
bytes which do not produce model events. Never infer upstream causality here.
"""
import json
import math
import os
from pathlib import Path
import re
import sys
import threading
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


class StreamObservation:
    def __init__(self, directory, *, interval=.5, clock=time.monotonic):
        directory = Path(directory).resolve()
        if directory.is_relative_to(ROOT / 'data/runs'):
            raise ValueError('observation_must_be_outside_run_evidence')
        if not math.isfinite(interval) or interval < .05:
            raise ValueError('observation_interval')
        directory.mkdir(parents=True, exist_ok=False)
        self.directory, self.clock, self.interval = directory, clock, interval
        self.started = clock()
        self.owner = threading.get_ident()
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.failure = None
        self.values = dict(schema_version='stream-observation-v1', body_free=True,
            http_requests=0, response_status=None, response_request_id=None,
            read_calls=0, raw_chunks=0, raw_bytes=0, last_bytes_ms=None,
            pending_read_since_ms=None, eof=False, closed=False,
            phase='before_request', exception_type=None, timeout=None)
        self.thread = threading.Thread(target=self._sample, daemon=True)
        # Establish output writability before starting the worker.
        self._save()
        self.thread.start()

    def ms(self):
        return max(0, round((self.clock() - self.started) * 1000))

    def update(self, **values):
        with self.lock:
            self.values.update(values)

    def mark_failure(self, category, *, phase='response_headers_failed'):
        """Record a fixed pre-response failure without provider details."""
        if category not in {
                'connect_error', 'connect_timeout', 'proxy_error',
                'tls_error', 'protocol_error', 'read_timeout', 'read_error',
                'write_error', 'pool_timeout', 'sdk_error'}:
            category = 'sdk_error'
        with self.lock:
            if self.values['response_status'] is None:
                self.values.update(phase=phase, exception_type=category,
                                   pending_read_since_ms=None)

    def on_request(self, request):
        timeout = request.extensions.get('timeout', {})
        bounded = {key: value for key in ('connect', 'read', 'write', 'pool')
            if isinstance(value := timeout.get(key), (int, float))
            and math.isfinite(value) and 0 <= value <= 86400}
        with self.lock:
            self.values.update(phase='awaiting_response_headers', timeout=bounded)
            self.values['http_requests'] += 1

    def on_response(self, response):
        request_id = response.headers.get('x-request-id')
        if request_id is not None and not re.fullmatch(r'[A-Za-z0-9._-]{1,160}', request_id):
            request_id = None
        self.update(response_status=response.status_code, response_request_id=request_id,
                    phase='response_headers_received')
        response.stream = ObservedStream(response.stream, self)

    def _save(self):
        with self.lock:
            value = dict(self.values)
        frame = sys._current_frames().get(self.owner)
        stack = []
        while frame and len(stack) < 32:
            stack.append(dict(file=Path(frame.f_code.co_filename).name,
                              function=frame.f_code.co_name, line=frame.f_lineno))
            frame = frame.f_back
        del frame
        value.update(observed_ms=self.ms(), stack=stack)
        temporary = self.directory / 'observation.tmp'
        with temporary.open('w', encoding='utf-8') as file:
            json.dump(value, file, ensure_ascii=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, self.directory / 'observation.json')

    def _sample(self):
        try:
            while not self.stop.wait(self.interval):
                self._save()
        except Exception:
            # Diagnostic failure is surfaced to the operator without serializing
            # exception text/locals or changing the Provider stream outcome.
            self.failure = 'observation_write_failed'

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            self.failure = 'observation_sampler_not_stopped'
            return
        try:
            self._save()
        except Exception:
            self.failure = 'observation_write_failed'


class ObservedStream(httpx.SyncByteStream):
    def __init__(self, stream, observer):
        self.stream, self.observer = stream, observer

    def __iter__(self):
        iterator = iter(self.stream)
        while True:
            with self.observer.lock:
                self.observer.values['read_calls'] += 1
                self.observer.values.update(phase='waiting_for_raw_bytes',
                    pending_read_since_ms=self.observer.ms())
            try:
                chunk = next(iterator)
            except StopIteration:
                self.observer.update(eof=True, phase='body_exhausted', pending_read_since_ms=None)
                return
            except BaseException as error:
                # Fixed category only; never an exception message or arbitrary
                # exception class name from a plugin/provider.
                category = ('read_timeout' if isinstance(error, httpx.ReadTimeout) else
                            'read_error' if isinstance(error, httpx.ReadError) else
                            'protocol_error' if isinstance(error, httpx.RemoteProtocolError) else 'other')
                self.observer.update(phase='read_failed', exception_type=category,
                                     pending_read_since_ms=None)
                raise
            with self.observer.lock:
                self.observer.values['raw_chunks'] += 1
                self.observer.values['raw_bytes'] += len(chunk)
                self.observer.values.update(last_bytes_ms=self.observer.ms(),
                    pending_read_since_ms=None, phase='sdk_consuming_bytes')
            yield chunk

    def close(self):
        self.observer.update(phase='closing')
        try:
            self.stream.close()
        except BaseException:
            self.observer.update(phase='close_failed')
            raise
        self.observer.update(closed=True, phase='closed')
