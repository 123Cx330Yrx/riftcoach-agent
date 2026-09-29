"""Offline prototype: separate developer waiting from active execution time.

Not enabled by any live entry point and not admitted by the qualification gate.
The same process may wait through a conversation interruption. Reconstructing
this clock in an existing run is forbidden; it is not process-crash recovery.
"""
from pathlib import Path
import hashlib
import math
import time

from app.evaluation.golden_journal import write_new_json

TIMING_MODE = 'separate-development-host-clock-v1'


class DevelopmentHostClock:
    def __init__(self, run_directory, *, max_host_seconds, wall_clock=time.monotonic):
        if (type(max_host_seconds) not in (int, float)
                or not math.isfinite(max_host_seconds) or max_host_seconds <= 0):
            raise ValueError('development_host_budget_invalid')
        self._wall = wall_clock
        self._started = self._wall()
        self._host_seconds = 0.0
        self._waiting_since = None
        self._sequence = 0
        self._limit = max_host_seconds
        self._directory = Path(run_directory) / 'development-host-clock'
        # This intentionally cannot restart a dead process with a fresh clock.
        self._directory.mkdir(exist_ok=False)
        write_new_json(self._directory / 'policy.json', dict(mode=TIMING_MODE,
            max_host_seconds=max_host_seconds, process_restart_allowed=False,
            qualification_adopted=False, excludes='Only explicit host gates and case readiness.'))

    def __call__(self):
        now = self._wall()
        pending = 0 if self._waiting_since is None else now - self._waiting_since
        return now - self._started - self._host_seconds - pending

    def before_send(self):
        if self._waiting_since is not None:
            raise ValueError('development_provider_during_host_wait')
        if self._host_seconds >= self._limit:
            raise ValueError('development_host_deadline')

    def _wait(self, binding, callback):
        self.before_send()
        self._sequence += 1
        stem = f'{self._sequence:04d}'
        started = self._wall()
        self._waiting_since = started
        available = self._limit - self._host_seconds
        outcome = 'interrupted'
        try:
            write_new_json(self._directory / (stem + '-waiting.json'), dict(
                binding=binding, active_elapsed_seconds=self(),
                wall_elapsed_seconds=started - self._started,
                remaining_host_seconds=available))
            value = callback(available)
            if self._wall() - started >= available:
                raise ValueError('development_host_deadline')
            outcome = 'returned'  # The existing source gate still decides acceptance.
            return value
        finally:
            finished = self._wall()
            self._host_seconds += finished - started
            self._waiting_since = None
            write_new_json(self._directory / (stem + '-finished.json'), dict(
                outcome=outcome, binding=binding,
                host_elapsed_seconds=finished - started,
                cumulative_host_seconds=self._host_seconds,
                active_elapsed_seconds=self(), wall_elapsed_seconds=finished-self._started))

    def adjudicate(self, path, remaining, review):
        if remaining <= 0:
            raise ValueError('role_pair_execution_limit')
        path = Path(path)
        binding = dict(kind='stage', key=path.parent.name, stage=path.stem,
            response_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            remaining_active_seconds=remaining)
        return self._wait(binding, lambda available: review(path, available))

    def await_case(self, directory, row, plan, remaining, ready):
        if remaining <= 0:
            raise ValueError('role_pair_execution_limit')
        binding = dict(kind='case_ready', key=row['key'], request_sha256=row['request_sha256'],
            remaining_active_seconds=remaining)
        return self._wait(binding, lambda available: ready(directory, row, plan, available))

    def summary(self):
        if self._waiting_since is not None:
            raise ValueError('development_host_wait_unfinished')
        return dict(mode=TIMING_MODE, active_elapsed_seconds=self(),
            host_elapsed_seconds=self._host_seconds,
            wall_elapsed_seconds=self._wall()-self._started,
            completed_host_waits=self._sequence, qualification_adopted=False)
