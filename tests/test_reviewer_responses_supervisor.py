"""Offline real-process coverage for the isolated reviewer Responses supervisor."""
import copy
import json
from pathlib import Path
import socket
import sys
import time

import pytest

from scripts import prepare_reviewer_profile_screen as screen
from scripts import reviewer_responses_process as process
from scripts.reviewer_responses_transport import Profile


USAGE = dict(input_tokens=1, output_tokens=2, total_tokens=3,
             cached_input_tokens=0, reasoning_tokens=0)
SECRET = 'SUPERVISOR_PRIVATE_API_KEY_SENTINEL'
BODY = 'SUPERVISOR_PRIVATE_BUSINESS_SENTINEL'

# All private inputs arrive through stdin; the command contains no interpolated
# input, secret or directory. These workers never create a network connection.
PRELUDE = '''
import json, sys, time
from pathlib import Path
import httpx
from scripts.stream_observation import StreamObservation
payload = json.load(sys.stdin)
directory = Path(payload['directory'])
usage = dict(input_tokens=1, output_tokens=2, total_tokens=3,
             cached_input_tokens=0, reasoning_tokens=0)
def write(name, value):
    with (directory / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream)
def observed(phase='closed'):
    observer = StreamObservation(directory / 'observation', interval=.05)
    observer.on_request(httpx.Request('POST', 'https://example.invalid/responses'))
    observer.update(response_status=200, phase=phase,
                    eof=phase == 'closed', closed=phase == 'closed')
    observer.close()
def result(ok=True):
    write('worker-result.json', dict(ok=ok, code='ok' if ok else 'worker_failed',
        usage=usage, public_tool_call=dict(id='call-test', name='submit_report_review',
                                         arguments={}) if ok else None))
'''


def worker(body):
    return [sys.executable, '-c', PRELUDE + '\n' + body]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('supervisor test attempted network')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture
def business():
    return json.loads((screen.PACKAGE / 'requests' / 'r01-facts.json').read_text(encoding='utf-8'))


@pytest.fixture
def launches(monkeypatch):
    original = process.subprocess.Popen
    seen = []

    def tracked(command, *args, **kwargs):
        child = original(command, *args, **kwargs)
        seen.append((list(command), kwargs, child))
        return child

    monkeypatch.setattr(process.subprocess, 'Popen', tracked)
    return seen


def run(business, directory, **kwargs):
    return process.run_once(business, profile=Profile(group='GPT-pro'),
                            api_key=SECRET, directory=directory, **kwargs)


def assert_reaped(receipt, launches):
    assert receipt['reaped'] is True
    assert len(launches) == 1
    assert launches[0][2].poll() is not None


@pytest.mark.parametrize('phase', ['waiting_for_raw_bytes', 'closing'])
def test_hard_deadline_reaps_worker_blocked_in_read_or_close(tmp_path, business, launches, phase):
    directory = tmp_path / 'deadline'
    command = worker(f"observed({phase!r})\ntime.sleep(60)")
    started = time.monotonic()
    receipt = run(business, directory, command=command, timeout_s=2)
    elapsed = time.monotonic() - started
    assert not receipt['ok'] and receipt['code'] == 'deadline_exceeded'
    assert receipt['usage'] is None and receipt['usage_state'] == 'unknown'
    assert receipt['http_requests'] == 1
    observation = json.loads((directory / 'observation' / 'observation.json').read_text())
    assert observation['phase'] == phase and not observation['closed']
    assert elapsed < 8, 'hard deadline did not stop the blocked child promptly'
    assert_reaped(receipt, launches)


def test_cancel_before_send_never_launches_child(tmp_path, business, launches):
    receipt = run(business, tmp_path / 'cancel-before', cancel=lambda: True,
                  command=worker("raise AssertionError('must not launch')"))
    assert not receipt['ok'] and receipt['code'] == 'cancelled'
    assert receipt['http_requests'] == 0
    assert receipt['usage'] is None and receipt['usage_state'] == 'not_sent'
    assert not launches


def test_hard_deadline_also_bounds_blocked_stdin_writer(tmp_path, business, launches):
    large = copy.deepcopy(business)
    large['messages'][0]['content'] += 'X' * 2_000_000
    # This child intentionally never consumes stdin, so a full request blocks
    # the parent's pipe writer before any model IO could begin.
    command = [sys.executable, '-c', 'import time; time.sleep(60)']
    started = time.monotonic()
    receipt = run(large, tmp_path / 'blocked-stdin', command=command, timeout_s=1)
    assert time.monotonic() - started < 8
    assert not receipt['ok'] and receipt['code'] == 'deadline_exceeded'
    assert receipt['usage'] is None and receipt['usage_state'] == 'unknown'
    assert receipt['http_requests'] is None
    assert_reaped(receipt, launches)


@pytest.mark.parametrize('known_usage', [False, True])
def test_cancel_after_send_preserves_known_or_unknown_usage(tmp_path, business, launches, known_usage):
    directory = tmp_path / 'cancel-after'
    code = "observed('waiting_for_raw_bytes')\n"
    if known_usage:
        code += "write('usage.json', usage)\n"
    code += "write('ready.json', True)\ntime.sleep(60)"
    receipt = run(business, directory, command=worker(code), timeout_s=10,
                  cancel=lambda: (directory / 'ready.json').exists())
    assert not receipt['ok'] and receipt['code'] == 'cancelled'
    assert receipt['http_requests'] == 1
    assert receipt['usage'] == (USAGE if known_usage else None)
    assert receipt['usage_state'] == ('known' if known_usage else 'unknown')
    assert json.loads((directory / 'receipt.json').read_text()) == receipt
    assert_reaped(receipt, launches)


def test_deadline_preserves_usage_received_before_blocked_close(tmp_path, business, launches):
    receipt = run(business, tmp_path / 'known-deadline', timeout_s=2,
                  command=worker("observed('closing')\nwrite('usage.json', usage)\nresult()\ntime.sleep(60)"))
    assert not receipt['ok'] and receipt['code'] == 'deadline_exceeded'
    assert receipt['usage'] == USAGE and receipt['usage_state'] == 'known'
    assert_reaped(receipt, launches)


def test_keyboard_interrupt_reaps_child_and_preserves_usage_receipt(tmp_path, business, launches):
    directory = tmp_path / 'keyboard-interrupt'

    def interrupted():
        if (directory / 'ready.json').exists():
            raise KeyboardInterrupt
        return False

    receipt = run(business, directory, cancel=interrupted, timeout_s=10,
                  command=worker("observed('closing')\nwrite('usage.json', usage)\n"
                                 "write('ready.json', True)\ntime.sleep(60)"))
    assert not receipt['ok'] and receipt['code'] == 'cancelled'
    assert receipt['usage'] == USAGE and receipt['usage_state'] == 'known'
    assert json.loads((directory / 'receipt.json').read_text()) == receipt
    assert_reaped(receipt, launches)


def test_keyboard_interrupt_at_final_acceptance_still_writes_failed_receipt(
        tmp_path, business, launches, monkeypatch):
    directory = tmp_path / 'final-interrupt'
    original = process.subprocess.Popen
    exited = []

    def observe_exit(*args, **kwargs):
        child = original(*args, **kwargs)
        poll = child.poll

        def observed_poll():
            code = poll()
            if code is not None:
                exited.append(True)
            return code

        child.poll = observed_poll
        return child

    def interrupted():
        if exited:
            raise KeyboardInterrupt
        return False

    monkeypatch.setattr(process.subprocess, 'Popen', observe_exit)
    receipt = run(business, directory, cancel=interrupted, timeout_s=10,
                  command=worker("observed()\nwrite('usage.json', usage)\nresult()"))
    assert not receipt['ok'] and receipt['code'] == 'cancelled'
    assert receipt['usage'] == USAGE and receipt['usage_state'] == 'known'
    assert json.loads((directory / 'receipt.json').read_text()) == receipt
    assert_reaped(receipt, launches)


@pytest.mark.parametrize('body', [
    "observed()\nwrite('usage.json', usage)\nresult()\nsys.exit(7)",
    "observed()\nwrite('usage.json', usage)",
    "observed()\nwrite('usage.json', usage)\nwrite('worker-result.json', {'ok': True})",
])
def test_child_failure_missing_or_malformed_result_cannot_succeed(tmp_path, business, launches, body):
    receipt = run(business, tmp_path / 'bad-child', command=worker(body), timeout_s=10)
    assert not receipt['ok']
    assert receipt['usage'] == USAGE and receipt['usage_state'] == 'known'
    assert_reaped(receipt, launches)


def test_child_without_observation_does_not_invent_zero_usage(tmp_path, business, launches):
    receipt = run(business, tmp_path / 'unobserved', command=worker('sys.exit(7)'), timeout_s=10)
    assert not receipt['ok']
    assert receipt['usage'] is None and receipt['usage_state'] == 'unknown'
    assert receipt['http_requests'] is None
    assert_reaped(receipt, launches)


@pytest.mark.parametrize('changes', [
    {'closed': False}, {'eof': False}, {'http_requests': 2}, {'response_status': 500},
])
def test_success_result_requires_single_successful_closed_http_observation(tmp_path, business, launches, changes):
    code = f"""
observed()
path = directory / 'observation' / 'observation.json'
value = json.loads(path.read_text())
value.update({changes!r})
path.write_text(json.dumps(value), encoding='utf-8')
write('usage.json', usage)
result()
"""
    receipt = run(business, tmp_path / 'bad-observation', command=worker(code), timeout_s=10)
    assert not receipt['ok']
    assert receipt['usage'] == USAGE and receipt['usage_state'] == 'known'
    assert_reaped(receipt, launches)


def test_disagreeing_usage_receipts_cannot_succeed(tmp_path, business, launches):
    code = """
observed()
write('usage.json', usage)
usage = dict(usage, output_tokens=3, total_tokens=4)
result()
"""
    receipt = run(business, tmp_path / 'usage-conflict', command=worker(code), timeout_s=10)
    assert not receipt['ok']
    assert_reaped(receipt, launches)


def test_missing_usage_checkpoint_preserves_worker_usage_but_rejects_success(tmp_path, business, launches):
    directory = tmp_path / 'missing-usage-checkpoint'
    receipt = run(business, directory, command=worker('observed()\nresult()'), timeout_s=10)
    assert not receipt['ok']
    assert receipt['usage'] == USAGE and receipt['usage_state'] == 'known'
    assert not (directory / 'usage.json').exists()
    assert json.loads((directory / 'receipt.json').read_text()) == receipt
    assert_reaped(receipt, launches)


def test_existing_directory_prevents_second_child(tmp_path, business, launches):
    directory = tmp_path / 'once'
    command = worker("observed()\nwrite('usage.json', usage)\nresult()")
    receipt = run(business, directory, command=command, timeout_s=10)
    assert receipt['ok'] and receipt['usage'] == USAGE
    original = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    with pytest.raises(FileExistsError):
        run(business, directory, command=command, timeout_s=10)
    assert len(launches) == 1
    assert {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()} == original


def test_receipt_write_failure_returns_failed_with_usage(tmp_path, business, launches, monkeypatch, capfd):
    directory = tmp_path / 'receipt-failure'
    original = Path.open

    def fail_receipt(path, *args, **kwargs):
        if path == directory / 'receipt.json':
            raise OSError(SECRET)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', fail_receipt)
    receipt = run(business, directory, timeout_s=10,
                  command=worker("observed()\nwrite('usage.json', usage)\nresult()"))
    assert not receipt['ok'] and receipt['code'] == 'receipt_write_failed'
    assert receipt['usage'] == USAGE and receipt['usage_state'] == 'known'
    assert SECRET not in json.dumps(receipt)
    output = capfd.readouterr()
    assert SECRET not in output.out + output.err
    assert_reaped(receipt, launches)


def test_private_inputs_never_enter_argv_output_or_receipt(tmp_path, business, launches, capfd):
    sensitive = copy.deepcopy(business)
    sensitive['messages'][0]['content'] += '\n' + BODY
    directory = tmp_path / 'private'
    code = """
print(payload['api_key'], flush=True)
print(payload['business']['messages'][0]['content'], file=sys.stderr, flush=True)
observed()
write('usage.json', usage)
result()
"""
    receipt = run(sensitive, directory, command=worker(code), timeout_s=10)
    assert receipt['ok']
    output = capfd.readouterr()
    public = json.dumps(launches[0][0]) + output.out + output.err + json.dumps(receipt)
    public += (directory / 'receipt.json').read_text()
    public += (directory / 'profile.json').read_text()
    public += (directory / 'observation' / 'observation.json').read_text()
    assert SECRET not in public and BODY not in public
    assert SECRET not in (directory / 'request.json').read_text()
    assert_reaped(receipt, launches)


@pytest.mark.parametrize('timeout', [0, -1, 301, float('inf'), float('nan'), True])
def test_invalid_timeout_never_launches_child(tmp_path, business, launches, timeout):
    with pytest.raises((ValueError, TypeError)):
        run(business, tmp_path / 'invalid-timeout', timeout_s=timeout,
            command=worker("raise AssertionError('must not launch')"))
    assert not launches
