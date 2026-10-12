"""Separate developer waiting from active execution time in opted-in runs.

The same process may wait through a conversation interruption. A sealed,
interrupted run can retain its completed prefix; its clock is never restarted.
"""
from pathlib import Path
import hashlib
import json
import math
import time

from app.evaluation.golden_journal import write_new_json

TIMING_MODE = 'separate-development-host-clock-v1'
TIMING_SCHEMA = 'development-host-clock-receipt-v1'


class DevelopmentHostClock:
    def __init__(self, run_directory, *, max_host_seconds, wall_clock=time.monotonic,
                 qualification_adopted=False, plan_sha256=None):
        if (type(max_host_seconds) not in (int, float)
                or not math.isfinite(max_host_seconds) or max_host_seconds <= 0):
            raise ValueError('development_host_budget_invalid')
        self._wall = wall_clock
        self._started = self._wall()
        self._host_seconds = 0.0
        self._waiting_since = None
        self._sequence = 0
        self._limit = max_host_seconds
        self._adopted = qualification_adopted is True
        if self._adopted and (not isinstance(plan_sha256, str)
                              or len(plan_sha256) != 64
                              or any(c not in '0123456789abcdef' for c in plan_sha256)):
            raise ValueError('development_host_plan_binding_invalid')
        self._plan_sha256 = plan_sha256
        self._directory = Path(run_directory) / 'development-host-clock'
        # This intentionally cannot restart a dead process with a fresh clock.
        self._directory.mkdir(exist_ok=False)
        write_new_json(self._directory / 'policy.json', dict(schema_version=TIMING_SCHEMA,
            mode=TIMING_MODE,
            max_host_seconds=max_host_seconds, process_restart_allowed=False,
            qualification_adopted=self._adopted, plan_sha256=plan_sha256,
            excludes='Only explicit host gates and case readiness.'))

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
            completed_host_waits=self._sequence, qualification_adopted=self._adopted,
            plan_sha256=self._plan_sha256)


def validate_adopted_timing(run_directory, plan, *, saved_plan_sha256,
                            allow_unfinished_tail=False):
    """Validate the durable host clock before a result can enter qualification.

    The validator intentionally derives all totals from immutable wait/finish
    receipts.  A summary flag, an adopted marker, or a larger timeout alone
    cannot make an unbound wait valid.
    """
    timing = plan.get('host_review_timing')
    if (not isinstance(timing, dict) or timing.get('mode') != TIMING_MODE
            or timing.get('adopted') is not True):
        raise ValueError('role_observation_unadopted_host_timing')
    max_host = timing.get('max_host_seconds')
    if (type(max_host) not in (int, float) or not math.isfinite(max_host)
            or max_host <= 0):
        raise ValueError('role_observation_host_timing_budget_invalid')
    directory = Path(run_directory) / 'development-host-clock'
    policy_path = directory / 'policy.json'
    try:
        policy = json.loads(policy_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('role_observation_host_timing_policy_missing') from exc
    if (policy.get('schema_version') != TIMING_SCHEMA
            or policy.get('mode') != TIMING_MODE
            or policy.get('qualification_adopted') is not True
            or policy.get('process_restart_allowed') is not False
            or policy.get('max_host_seconds') != max_host
            or policy.get('plan_sha256') != saved_plan_sha256):
        raise ValueError('role_observation_host_timing_policy_mismatch')
    waiting = sorted(directory.glob('*-waiting.json'))
    finished = sorted(directory.glob('*-finished.json'))
    if not waiting or len(waiting) != len(finished) and not (
            allow_unfinished_tail and len(waiting) == len(finished) + 1):
        raise ValueError('role_observation_host_timing_receipt_inventory')
    unfinished_tail = None
    if len(waiting) == len(finished) + 1:
        unfinished_tail = json.loads(waiting[-1].read_text(encoding='utf-8'))
        binding = unfinished_tail.get('binding')
        if (not allow_unfinished_tail or waiting[-1].name != f'{len(waiting):04d}-waiting.json'
                or not isinstance(binding, dict) or binding.get('kind') != 'case_ready'):
            raise ValueError('role_observation_host_timing_receipt_inventory')
        tail_values = [unfinished_tail.get('active_elapsed_seconds'),
                       unfinished_tail.get('wall_elapsed_seconds'),
                       unfinished_tail.get('remaining_host_seconds')]
        if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
               for value in tail_values):
            raise ValueError('role_observation_host_timing_elapsed_invalid')
    previous_host = 0.0
    previous_active = 0.0
    for index, (start_path, end_path) in enumerate(
            zip(waiting[:len(finished)], finished, strict=True), 1):
        if start_path.name != f'{index:04d}-waiting.json' or end_path.name != f'{index:04d}-finished.json':
            raise ValueError('role_observation_host_timing_sequence')
        try:
            start = json.loads(start_path.read_text(encoding='utf-8'))
            end = json.loads(end_path.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError('role_observation_host_timing_receipt_invalid') from exc
        binding = start.get('binding')
        if not isinstance(binding, dict) or end.get('binding') != binding:
            raise ValueError('role_observation_host_timing_binding')
        values = [start.get('active_elapsed_seconds'), start.get('wall_elapsed_seconds'),
                  start.get('remaining_host_seconds'), end.get('host_elapsed_seconds'),
                  end.get('cumulative_host_seconds'), end.get('active_elapsed_seconds'),
                  end.get('wall_elapsed_seconds')]
        if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
               for value in values):
            raise ValueError('role_observation_host_timing_elapsed_invalid')
        host_elapsed = end['host_elapsed_seconds']
        cumulative = end['cumulative_host_seconds']
        if (abs(start['active_elapsed_seconds'] - end['active_elapsed_seconds']) > .01
                or abs(start['wall_elapsed_seconds']
                       - (start['active_elapsed_seconds'] + previous_host)) > .01
                or abs(host_elapsed - (cumulative - previous_host)) > .01
                or abs(end['wall_elapsed_seconds']
                       - (end['active_elapsed_seconds'] + cumulative)) > .01
                or end['wall_elapsed_seconds'] < start['wall_elapsed_seconds']
                or end['active_elapsed_seconds'] < previous_active
                or cumulative > max_host + .01):
            raise ValueError('role_observation_host_timing_clock_inconsistent')
        key = binding.get('key')
        case_rows = {}
        for row in plan.get('cases', []):
            if isinstance(row, dict) and isinstance(row.get('key'), str):
                case_rows[row['key']] = row
                case_rows[row['key'].replace(':', '-')] = row
        row = case_rows.get(key)
        if row is None:
            raise ValueError('role_observation_host_timing_case_binding')
        remaining_active = binding.get('remaining_active_seconds')
        batch_max = plan.get('batch_budget', {}).get('max_seconds')
        if (type(remaining_active) not in (int, float)
                or not math.isfinite(remaining_active) or remaining_active <= 0
                or type(batch_max) not in (int, float) or not math.isfinite(batch_max)
                or batch_max <= 0 or remaining_active > batch_max + .01):
            raise ValueError('role_observation_host_timing_active_budget')
        if binding.get('kind') == 'stage':
            stage = binding.get('stage')
            response = Path(run_directory) / str(key) / f'{stage}.json'
            if (stage not in {'initial', 'revision', 'final'} or not response.is_file()
                    or hashlib.sha256(response.read_bytes()).hexdigest() != binding.get('response_sha256')):
                raise ValueError('role_observation_host_timing_stage_binding')
        elif binding.get('kind') == 'case_ready':
            if binding.get('request_sha256') != row.get('request_sha256'):
                raise ValueError('role_observation_host_timing_case_request_binding')
        else:
            raise ValueError('role_observation_host_timing_binding_kind')
        previous_host = cumulative
        previous_active = end['active_elapsed_seconds']
    result = dict(mode=TIMING_MODE, waits=len(finished), host_elapsed_seconds=previous_host,
                active_elapsed_seconds=previous_active,
                wall_elapsed_seconds=previous_active + previous_host)
    if unfinished_tail is not None:
        _validate_unfinished_case_wait(Path(run_directory), plan, saved_plan_sha256,
            unfinished_tail, previous_active, previous_host)
        result['unfinished_tail'] = unfinished_tail['binding']
        result['unfinished_wait_elapsed_seconds'] = None
    return result


def _validate_unfinished_case_wait(run, plan, plan_sha, tail, previous_active, previous_host):
    """Only a never-started next case can follow a fully completed prefix."""
    binding = tail['binding']
    rows = plan.get('cases', [])
    matches = [i for i, row in enumerate(rows) if row.get('key') == binding.get('key')]
    if len(matches) != 1 or matches[0] == 0:
        raise ValueError('role_observation_host_timing_tail_prefix')
    index = matches[0]
    row = rows[index]
    active, wall = tail['active_elapsed_seconds'], tail['wall_elapsed_seconds']
    remaining = binding.get('remaining_active_seconds')
    maximum = plan.get('batch_budget', {}).get('max_seconds')
    if (type(remaining) not in (int, float) or not math.isfinite(remaining)
            or type(maximum) not in (int, float) or not math.isfinite(maximum)
            or remaining <= 0 or active < previous_active or active >= maximum
            or abs(remaining + active - maximum) > .01
            or abs(wall - active - previous_host) > .01
            or abs(tail['remaining_host_seconds'] + previous_host
                   - plan['host_review_timing']['max_host_seconds']) > .01
            or binding.get('request_sha256') != row.get('request_sha256')):
        raise ValueError('role_observation_host_timing_tail_binding')
    for completed in rows[:index]:
        arm = run/completed['key'].replace(':', '-')
        try:
            receipt = json.loads((arm/'case-completed.json').read_bytes())
            measured = receipt['batch_elapsed_seconds']
            if (receipt.get('schema_version') != 'role-case-completion-v1'
                    or receipt.get('plan_sha256') != plan_sha
                    or receipt.get('outcome', {}).get('key') != completed['key']
                    or receipt.get('task_observation_sha256') != hashlib.sha256(
                        (arm/'task-observation.json').read_bytes()).hexdigest()
                    or type(measured) not in (int, float) or not math.isfinite(measured)
                    or not 0 <= measured <= active + .01):
                raise ValueError('invalid completion')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError('role_observation_host_timing_tail_prefix') from exc
    for pending in rows[index:]:
        name = pending['key'].replace(':', '-')
        if (run/name).exists() or (run/'transport'/name).exists():
            raise ValueError('role_observation_host_timing_tail_started')
    name = row['key'].replace(':', '-')
    required_path = run/'handoff'/(name+'-ready-required.json')
    try:
        required = json.loads(required_path.read_bytes())
        if (required.get('schema_version') != 'role-case-ready-required-v1'
                or required.get('key') != row['key'] or required.get('plan_sha256') != plan_sha
                or required.get('request_sha256') != row['request_sha256']
                or required.get('run_directory') != run.resolve().as_posix()
                or required.get('remaining_batch_seconds') != tail['remaining_host_seconds']
                or required.get('signal_file') != name+'-ready.json'):
            raise ValueError('invalid ready handoff')
        signal = required_path.with_name(name+'-ready.json')
        if signal.exists() and json.loads(signal.read_bytes()) != dict(
                schema_version='role-case-ready-v1', ready=True, key=row['key'],
                plan_sha256=plan_sha,
                required_sha256=hashlib.sha256(required_path.read_bytes()).hexdigest()):
            raise ValueError('invalid signal')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('role_observation_host_timing_tail_handoff') from exc
