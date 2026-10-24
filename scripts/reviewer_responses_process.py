"""One research call in an owned process; no live batch/authorization launcher.

Callers must separately establish authorization, frozen material, group/account
binding, network route and semantic review. This module never loads a secret.
The deadline covers SDK startup/read/close; reaping has a separate five-second
grace and cannot turn a deadline/cancellation into success.
"""
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from scripts.reviewer_responses_transport import Profile, TransportError, build_wire, collect, digest

ROOT = Path(__file__).resolve().parents[1]


def response_contract(mode):
    if mode == 'stream':
        return build_wire, collect
    if mode in ('nonstream-tool-v1', 'natural-sol-v1', 'necessity-candidate-v1', 'natural-sol-necessity-v1'):
        from scripts import reviewer_responses_nonstream as nonstream
        return nonstream.build_wire, nonstream.collect
    if mode in ('nonstream-tool-message-v2', 'natural-sol-necessity-v2'):
        from functools import partial
        from scripts import reviewer_responses_nonstream as nonstream
        return nonstream.build_wire, partial(nonstream.collect, output_policy=nonstream.TOOL_WITH_MESSAGE)
    raise ValueError('response_mode_invalid')


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + '\n')
        handle.flush()
        os.fsync(handle.fileno())


def read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def valid_saved_usage(value):
    if not isinstance(value, dict) or set(value) != {
            'input_tokens', 'output_tokens', 'total_tokens', 'cached_input_tokens', 'reasoning_tokens'}:
        return False
    if any(type(value[k]) is not int or value[k] < 0
           for k in ('input_tokens', 'output_tokens', 'total_tokens')):
        return False
    return (value['total_tokens'] == value['input_tokens'] + value['output_tokens'] and
        all(value[key] is None or type(value[key]) is int and 0 <= value[key] <= value[limit]
            for key, limit in [('cached_input_tokens', 'input_tokens'), ('reasoning_tokens', 'output_tokens')]))


def run_once(business, *, profile, api_key, directory, cancel=lambda: False,
             timeout_s=300, command=None, response_mode='stream', validation_context=None):
    """Explicit caller credential is passed by stdin, never argv or a file.

    A directory is a create-only single-call claim, not a batch retry token.
    `command` is a process-test seam. No shell is used, and child output is not
    captured: diagnostic records contain fixed codes and counters only.
    """
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 300:
        raise ValueError('timeout_invalid')
    if not isinstance(profile, Profile):
        raise ValueError('profile_required')
    make_wire, _ = response_contract(response_mode)
    if response_mode == 'natural-sol-v1':
        from app.evaluation.sol_natural_contract import validate_business
        validate_business(business, validation_context)
    elif response_mode in ('natural-sol-necessity-v1', 'natural-sol-necessity-v2'):
        from app.evaluation.sol_necessity_contract import validate_business, REVIEW_PROFILE
        if profile != REVIEW_PROFILE:
            raise ValueError('necessity_natural_profile_binding')
        validate_business(business, validation_context)
    elif response_mode == 'necessity-candidate-v1':
        from scripts.review_necessity_candidate import validate_business
        validate_business(business, validation_context)
    elif validation_context is not None:
        raise ValueError('unexpected_validation_context')
    if response_mode != 'stream' and profile.route != 'proxy-12000':
        raise ValueError('nonstream_explicit_proxy_required')
    wire = make_wire(business)
    directory = Path(directory).resolve()
    if directory.is_relative_to(ROOT/'data/runs'):
        raise ValueError('research_output_must_be_outside_runs')
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory/'request.json', business)
    if validation_context is not None:
        write_json(directory/'validation-context.json', validation_context)
    saved_profile = dict(**asdict(profile), reasoning_effort='high',
        api='responses', max_output_tokens=wire['max_output_tokens'], max_retries=0, timeout_s=timeout_s,
        group_verified=False, upstream_identity_verified=False)
    if response_mode != 'stream':
        saved_profile['response_mode'] = response_mode
    write_json(directory/'profile.json', saved_profile)
    started = time.monotonic()
    deadline = started + timeout_s
    code, process, writer = 'cancelled', None, None
    reaped, write_failed = True, []
    try:
        if not cancel():
            code = 'worker_failed'
            process = subprocess.Popen(command or [sys.executable, '-m',
                'scripts.reviewer_responses_process', '--worker'], cwd=ROOT,
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            reaped = False
            data = json.dumps(dict(business=business, profile=asdict(profile), api_key=api_key,
                directory=str(directory), timeout_s=timeout_s,
                response_mode=response_mode, validation_context=validation_context), ensure_ascii=True).encode('utf-8')

            def send_input():
                try:
                    process.stdin.write(data)
                    process.stdin.close()
                except (OSError, ValueError):
                    write_failed.append(True)

            # A blocked stdin pipe must not defeat the same deadline either.
            writer = threading.Thread(target=send_input, daemon=True)
            writer.start()
            while True:
                if cancel():
                    code = 'cancelled'
                    break
                if time.monotonic() >= deadline:
                    code = 'deadline_exceeded'
                    break
                if process.poll() is not None:
                    code = 'worker_finished'
                    break
                time.sleep(min(.02, max(0, deadline - time.monotonic())))
    except KeyboardInterrupt:
        code = 'cancelled'
    except Exception:
        code = 'supervisor_failed'
    finally:
        if process is not None:
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                reaped = True
            except (OSError, subprocess.TimeoutExpired):
                code = 'worker_not_reaped'
            if writer is not None:
                writer.join(timeout=.5)
                if writer.is_alive():
                    code = 'input_writer_not_stopped'
    worker = read_json(directory/'worker-result.json')
    checkpoint_usage = read_json(directory/'usage.json')
    usage = checkpoint_usage if valid_saved_usage(checkpoint_usage) else None
    worker_usage = worker.get('usage') if worker else None
    usage_conflict = bool(worker and worker.get('usage_conflict') is True or
        valid_saved_usage(usage) and valid_saved_usage(worker_usage) and usage != worker_usage)
    worker_code = worker.get('code') if isinstance(worker, dict) and isinstance(worker.get('code'), str) else None
    failure_category = (worker.get('failure_category')
                        if isinstance(worker, dict) and isinstance(worker.get('failure_category'), str)
                        else None)
    # A failed checkpoint write must not discard already observed totals that
    # survived in the final worker result. It still disqualifies acceptance.
    if usage is None and valid_saved_usage(worker_usage):
        usage = worker_usage
    observation = read_json(directory/'observation/observation.json')
    observed_http = observation.get('http_requests') if observation else None
    # A stale zero after process start cannot prove a request was never sent.
    http_requests = (0 if process is None else observed_http
                     if type(observed_http) is int and observed_http > 0 else None)
    if code == 'worker_finished':
        if process.returncode != 0 or write_failed or not worker:
            code = 'worker_failed'
        elif worker.get('ok') is not True:
            code = 'worker_rejected'
        elif usage_conflict or worker_usage != checkpoint_usage or not valid_saved_usage(checkpoint_usage):
            code = 'usage_receipt_mismatch'
        elif (usage is None or not observation or observation.get('http_requests') != 1 or
              observation.get('response_status') != 200 or observation.get('closed') is not True or
              observation.get('eof') is not True or
              observation.get('exception_type') is not None):
            code = 'observation_or_usage_invalid'
        else:
            try:
                code = ('deadline_exceeded' if time.monotonic() >= deadline else
                        'cancelled' if cancel() else 'ok')
            except KeyboardInterrupt:
                code = 'cancelled'
            except Exception:
                code = 'supervisor_failed'
    receipt = dict(version='research-responses-single-call-v1', ok=code == 'ok', code=code,
        worker_code=worker_code, failure_category=failure_category,
        request_sha256=digest(business), wire_sha256=digest(wire), profile=asdict(profile),
        usage=usage, usage_state='unknown' if usage_conflict else
            'known' if usage is not None else 'not_sent' if process is None else 'unknown',
        usage_conflict=usage_conflict, conflicting_worker_usage=worker_usage if usage_conflict else None,
        usage_basis='channel_reported_unverified_upstream', http_requests=http_requests,
        reaped=reaped, worker_exit=None if process is None else process.returncode,
        elapsed_s=round(time.monotonic() - started, 6), semantic_approval=False,
        group_verified=False, upstream_identity_verified=False, qualified=False)
    if response_mode != 'stream':
        receipt['response_mode'] = response_mode
    if validation_context is not None:
        receipt['validation_context_sha256'] = digest(validation_context)
    try:
        write_json(directory/'receipt.json', receipt)
    except Exception:
        receipt.update(ok=False, code='receipt_write_failed')
    return receipt


def screen_validator(business, *, response_mode='stream'):
    """Bind a single saved screen request and reuse its existing business checks."""
    from app.evaluation.source_patch_editor import report_inputs
    from scripts import prepare_reviewer_profile_screen as screen
    from scripts.review_duty_direct_patch import validate

    matches = []
    for case in ('r01', 'r02'):
        for duty in ('facts', 'completion'):
            path = screen.PACKAGE/'requests'/f'{case}-{duty}.json'
            if read_json(path) == business:
                matches.append((case, duty))
    if not matches and response_mode == 'nonstream-tool-v1':
        from scripts.prepare_reviewer_semantic_screen import business_validator
        return business_validator(business)
    if len(matches) != 1:
        raise TransportError('screen_request_binding')
    case, duty = matches[0]
    inputs = report_inputs(screen.source_inputs(), (screen.PACKAGE/f'{case}.md').read_text(encoding='utf-8'))
    if screen.visible(screen.json_value(screen.research_request(inputs, duty))) != business:
        raise TransportError('screen_request_reconstruction')
    return lambda raw: validate(raw, inputs, duty)


def worker():
    """Internal stdin protocol. No API key discovery and no command-line sender."""
    payload = json.load(sys.stdin)
    directory = Path(payload['directory'])
    result = dict(ok=False, code='worker_preflight_failed', usage=None, public_tool_call=None)
    try:
        if payload.get('response_mode') == 'natural-sol-v1':
            from app.evaluation.sol_natural_contract import validate_business
            validate = validate_business(payload['business'], payload['validation_context'])
        elif payload.get('response_mode') in ('natural-sol-necessity-v1', 'natural-sol-necessity-v2'):
            from app.evaluation.sol_necessity_contract import validate_business, REVIEW_PROFILE
            if Profile(**payload['profile']) != REVIEW_PROFILE:
                raise ValueError('necessity_natural_profile_binding')
            validate = validate_business(payload['business'], payload['validation_context'])
        elif payload.get('response_mode') == 'necessity-candidate-v1':
            from scripts.review_necessity_candidate import validate_business
            validate = validate_business(payload['business'], payload['validation_context'])
        else:
            validate = screen_validator(payload['business'], response_mode=payload.get('response_mode', 'stream'))
        _, collect_response = response_contract(payload.get('response_mode', 'stream'))
        result = collect_response(payload['business'], profile=Profile(**payload['profile']),
            api_key=payload['api_key'], observation_dir=directory/'observation',
            timeout_s=payload['timeout_s'],
            on_usage=lambda usage: write_json(directory/'usage.json', usage))
        if result['ok']:
            try:
                validate(result['public_tool_call']['arguments'])
                result['business_validated'] = True
            except Exception:
                result.update(ok=False, code='business_contract_invalid')
    except Exception:
        # Never emit arbitrary exception text, request contents, key or reasoning.
        result['code'] = 'worker_preflight_or_storage_failed'
    write_json(directory/'worker-result.json', result)


if __name__ == '__main__':
    if sys.argv[1:] != ['--worker']:
        raise SystemExit('internal_worker_only')
    worker()
