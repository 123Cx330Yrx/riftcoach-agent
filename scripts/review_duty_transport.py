"""Isolated, request-pinned development transport. No authorization or execute CLI.

The old stream lifecycle is reused in a private module; no production request
validator, transport registry or historical worker is changed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from app.evaluation import golden_stream_bridge as legacy
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from scripts import full_chain_observed_transport as observed
from scripts.full_chain_modules import private_module
from scripts.review_duty_execution import check_issued, model_for, request_bytes
from scripts.review_duty_host_gate import sha
from scripts.stream_observation import StreamObservation

VERSION = 'review-duty-observed-v1'
REVIEW = 'review-duty-glm53-high-time600-v1'
FLASH = 'review-duty-flash-high-time300-v1'
TRANSPORTS = (REVIEW, FLASH)
STREAM_FILES = frozenset(('reservation.json', 'result.json', 'progress.json',
    'progress.tmp', 'failure.json', 'rejected-tool-output.json'))


def transport_for(request):
    return FLASH if model_for(request) == 'glm-5.3-flash' else REVIEW


def read_prepared(path, expected_sha):
    path = Path(path)
    if (not path.is_absolute() or path.resolve() != path or path.is_symlink()
            or path.stat().st_nlink != 1 or sha(path) != expected_sha):
        raise ValueError('duty_transport_prepared_binding')
    return legacy.REQUEST.validate_json(path.read_bytes())


def isolated_bridge(prepared_path, prepared_sha):
    prepared = read_prepared(prepared_path, prepared_sha)
    bridge = private_module(legacy.__file__, {})
    bridge.TIMED_REVIEW_TRANSPORT_ID, bridge.TIMED_FLASH_TRANSPORT_ID = REVIEW, FLASH
    bridge.REVIEW_TRANSPORTS, bridge.TIMED_TRANSPORTS, bridge.TRANSPORTS = (REVIEW,), TRANSPORTS, TRANSPORTS

    def validate(request, *, transport_id):
        current = read_prepared(prepared_path, prepared_sha)
        raw = check_issued(current, request)
        if (current != prepared or transport_for(request) != transport_id
                or not math.isfinite(request.timeout_s)
                or not 0 < request.timeout_s <= (300 if transport_id == FLASH else 600)
                or request.max_tokens != 32768
                or estimate_runtime_request_input_ceiling(request) > 64000
                or len(raw) > bridge.MAX_BYTES):
            raise ValueError('duty_transport_request_binding')
        return raw

    bridge.validate_request = validate
    return bridge


def destination(root, stream):
    return observed.outside_runs(root) / hashlib.sha256(str(Path(stream).resolve()).encode()).hexdigest()


def direct_environment(environ):
    # A child-only copy: never mutate the caller or the user's proxy settings.
    result = {k:v for k,v in environ.items() if k.lower() not in
        ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
    result['NO_PROXY'] = 'open.bigmodel.cn'
    return result


def attach_observation(bridge, *, root, prepared_path, prepared_sha):
    child = bridge.run_child

    def run_child(command, raw, **kwargs):
        env = direct_environment(kwargs['environ'])
        route = observed.route_record(env)
        stream = Path(kwargs['directory']).resolve()
        side = destination(root, stream)
        side.mkdir(parents=True, exist_ok=False)
        write_new_json(side/'binding.json', dict(version=VERSION,
            transport_id=kwargs['transport_id'], request_sha256=hashlib.sha256(raw).hexdigest(),
            worker_directory=str(stream), route=route))
        command = list(command)
        at = command.index('-m') + 1
        if command[at] != 'app.evaluation.golden_stream_bridge':
            raise ValueError('duty_transport_entrypoint')
        command[at] = 'scripts.review_duty_transport'
        command += ['--observation', str(side/'sampling'), '--prepared', str(prepared_path),
                    '--prepared-sha', prepared_sha]
        started, complete = time.monotonic(), False
        try:
            response = child(command, raw, **{**kwargs, 'environ':env})
            complete = True
            return response
        finally:
            def optional(name):
                try:
                    return json.loads((side/name).read_bytes())
                except (OSError, ValueError):
                    return None
            value, anchor = optional('sampling/observation.json'), optional('sampling/anchor.json')
            failure = (side/'sampling/failure.json').exists()
            age = (round((time.monotonic()-anchor['parent_clock_started'])*1000)
                - value['observed_ms']) if value and anchor else None
            valid = bool(value and anchor and not failure and age is not None
                         and -1000 <= age <= 3000 and value.get('http_requests') == 1)
            write_new_json(side/'parent-audit.json', dict(transport_complete=complete,
                elapsed_ms=round((time.monotonic()-started)*1000), observation_present=value is not None,
                observation_age_ms=age, observation_valid=valid, observation_failure=failure,
                files={p.relative_to(side).as_posix():sha(p) for p in side.rglob('*') if p.is_file()}))
            if complete and not valid:
                error = ValueError('duty_transport_observation_incomplete')
                error.observed_response = response
                raise error

    bridge.run_child = run_child
    return bridge


class Sender:
    """Caller owns authorization, cancellation and the shared budget gate."""
    def __init__(self, *, settings_for_model, observation_root):
        self.settings = settings_for_model
        self.root = observed.outside_runs(observation_root)
        self.used = set()

    def __call__(self, request, folder):
        folder = Path(folder).resolve()
        if folder in self.used or (folder/'transport').exists():
            raise ValueError('duty_transport_no_restart')
        self.used.add(folder)
        path = folder/'prepared-request.json'
        pin = sha(path)
        bridge = attach_observation(isolated_bridge(path, pin), root=self.root,
            prepared_path=path, prepared_sha=pin)
        transport = transport_for(request)
        raw = bridge.validate_request(request, transport_id=transport)
        if (folder/'issued-request.json').read_bytes() != raw:
            raise ValueError('duty_transport_issued_binding')
        provider = bridge.GoldenProcessStreamProvider(settings=self.settings(model_for(request)),
            directory=folder/'transport', transport_id=transport)
        response = provider.chat(request)
        return Exchange(request, response, hashlib.sha256(raw).hexdigest())


def verify(folder, root, *, complete_required):
    folder = Path(folder).resolve()
    stream = folder/'transport/stream-001'
    if not stream.exists():
        if complete_required:
            raise ValueError('duty_transport_missing')
        return {}
    raw = (folder/'issued-request.json').read_bytes()
    request = legacy.REQUEST.validate_json(raw)
    check_issued(read_prepared(folder/'prepared-request.json', sha(folder/'prepared-request.json')), request)
    transport = transport_for(request)
    reservation = json.loads((stream/'reservation.json').read_bytes())
    expected = dict(transport_id=transport,ordinal=1,request_sha256=hashlib.sha256(raw).hexdigest(),
        stream_tool_arguments=bool(request.tools),state='reserved_before_io',
        request_metrics=legacy.request_metrics(request,raw))
    if transport == REVIEW:
        expected.update(model='glm-5.3',thinking_profile_id=legacy.ZHIPU_GLM53_HIGH_REVIEW_DIAGNOSTIC_PROFILE.profile_id)
    if reservation != expected:
        raise ValueError('duty_transport_reservation')
    result = json.loads((stream/'result.json').read_bytes())
    if (result.get('transport_id') != transport or result.get('body_free') is not True
            or type(result.get('elapsed_ms')) is not int or result['elapsed_ms'] < 0
            or result.get('state') not in ('complete','failed','deadline','interrupted','unreaped','cleanup_failed')
            or complete_required and result['state'] != 'complete'):
        raise ValueError('duty_transport_result')
    verifier = private_module(observed.__file__, {})
    verifier.VERSION, verifier.TRANSPORTS = VERSION, TRANSPORTS
    record = verifier.verify_observation(stream, raw, transport_id=transport,
        observation_root=root, complete_required=complete_required)
    side = destination(root, stream)
    allowed = {'binding.json','parent-audit.json','sampling', 'sampling/anchor.json',
               'sampling/observation.json','sampling/failure.json'}
    if not complete_required:
        allowed.add('sampling/observation.tmp')
    for p in side.rglob('*'):
        if (p.relative_to(side).as_posix() not in allowed or p.resolve() != p or p.is_symlink()
                or p.is_file() and p.stat().st_nlink != 1):
            raise ValueError('duty_transport_observation_inventory')
    for p in stream.iterdir():
        if (not p.is_file() or p.name not in STREAM_FILES or p.is_symlink()
                or p.stat().st_nlink != 1 or complete_required and p.name == 'progress.tmp'):
            raise ValueError('duty_transport_stream_inventory')
    return {str(side/name):pin for name,pin in record.get('files',{}).items()}


def worker(args):
    import openai
    observed.route_record(os.environ)
    bridge = isolated_bridge(args.prepared, args.prepared_sha)
    if args.worker.resolve() != args.prepared.parent/'transport/stream-001':
        raise ValueError('duty_transport_worker_path')
    observer = StreamObservation(observed.outside_runs(args.observation))
    write_new_json(observer.directory/'anchor.json', dict(parent_clock_started=observer.started))
    original = openai.OpenAI
    def client(**kwargs):
        kwargs['http_client'].event_hooks['request'].append(observer.on_request)
        kwargs['http_client'].event_hooks['response'].append(observer.on_response)
        return original(**kwargs)
    openai.OpenAI = client
    try:
        bridge.worker(args.worker, args.started, args.deadline, args.transport_id)
    except BaseException as error:
        write_new_json(args.worker/'failure.json', dict(category='worker_failed',
            assembly_code=error.code if isinstance(error, bridge.StreamAdapterError) else None,
            provider_code=error.code if isinstance(error, bridge.ProviderError)
                and error.code in bridge.SAFE_PROVIDER_FAILURE_CODES else None))
        raise SystemExit(1) from None
    finally:
        openai.OpenAI = original
        observer.close()
        if observer.failure:
            write_new_json(observer.directory/'failure.json', dict(code=observer.failure))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', required=True, type=Path)
    parser.add_argument('--observation', required=True, type=Path)
    parser.add_argument('--prepared', required=True, type=Path)
    parser.add_argument('--prepared-sha', required=True)
    parser.add_argument('--started', required=True, type=float)
    parser.add_argument('--deadline', required=True, type=float)
    parser.add_argument('--transport-id', required=True, choices=TRANSPORTS)
    worker(parser.parse_args())


if __name__ == '__main__':
    main()
