"""Private prospective relation worker with mandatory body-free observation."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import time

from scripts.document_sampling_screening import load_private
from scripts.stream_observation import StreamObservation
from app.evaluation import golden_stream_bridge as legacy

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'document-relation-repair-observed-v1'
TRANSPORT = 'golden-glm53-relation-repair-observed-time600-high-32768-v1'
OBSERVATION_ROOT = Path('C:/Users/33502/Documents/Agent/outputs/riftcoach-relation-repair-20261013/observations')
_identity = load_private(ROOT / 'scripts/document_relation_request.py', 'scripts._repair_relation_identity')
_identity.VERSION, _identity.TRANSPORT = VERSION, TRANSPORT
_identity.MARKER = 'document_relation_repair_comparison'
MARKER = _identity.MARKER
_bytes = _identity.request_bytes


def request_bytes(request, *, transport_id=TRANSPORT):
    return _bytes(request, transport_id=transport_id)


_identity.request_bytes = request_bytes
prepare_request, projection, request_sha = _identity.prepare_request, _identity.projection, _identity.request_sha
BASELINE, CANDIDATE, VARIANTS = _identity.BASELINE, _identity.CANDIDATE, _identity.VARIANTS


def route_record(environ):
    # Record only the effective route contract, never proxy addresses or secrets.
    # os.environ lookups are case-insensitive on Windows. Inspect the emitted
    # child environment's actual keys, matching route_environment's contract.
    environ = dict(environ)
    proxies = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')
    bypass = environ.get('NO_PROXY') == 'open.bigmodel.cn' and 'no_proxy' not in environ
    if any(environ.get(k) for k in proxies) or not bypass:
        raise ValueError('repair_observation_requires_direct_route')
    if environ.get('LLM_BASE_URL', '').rstrip('/') != 'https://open.bigmodel.cn/api/paas/v4':
        raise ValueError('repair_observation_endpoint')
    return dict(route='direct', destination_host='open.bigmodel.cn', process_proxy_present=False,
                no_proxy_matches_host=True, system_network_path_proven=False)


def outside_runs(path):
    path = Path(path).resolve()
    if path.is_relative_to(ROOT / 'data/runs'):
        raise ValueError('repair_observation_inside_run')
    return path


def isolated_bridge(*, observation_root=None):
    # Pydantic resolves postponed observation field annotations through this
    # module's registered namespace, as the existing isolated bridge does.
    name = 'scripts._repair_observed_bridge'
    spec = importlib.util.spec_from_file_location(name, legacy.__file__)
    bridge = importlib.util.module_from_spec(spec)
    sys.modules[name] = bridge
    spec.loader.exec_module(bridge)
    old = bridge.TIMED_REVIEW_TRANSPORT_ID
    for field in ('TRANSPORTS', 'REVIEW_TRANSPORTS', 'TIMED_TRANSPORTS'):
        setattr(bridge, field, tuple(TRANSPORT if x == old else x for x in getattr(bridge, field)))
    bridge.TIMED_REVIEW_TRANSPORT_ID, bridge.validate_request = TRANSPORT, request_bytes
    child = bridge.run_child
    root = outside_runs(observation_root if observation_root is not None else OBSERVATION_ROOT)

    def run_child(command, raw, **kwargs):
        route = route_record(kwargs['environ'])
        stream = Path(kwargs['directory']).resolve()
        destination = root / hashlib.sha256(str(stream).encode()).hexdigest()
        destination.mkdir(parents=True, exist_ok=False)
        bridge.write_new_json(destination / 'binding.json', dict(version=VERSION,
            transport_id=TRANSPORT, request_sha256=hashlib.sha256(raw).hexdigest(),
            worker_directory=str(stream), route=route))
        command = list(command)
        at = command.index('-m') + 1
        if command[at] != 'app.evaluation.golden_stream_bridge':
            raise ValueError('repair_observation_worker_entrypoint')
        command[at] = 'scripts.document_relation_observed_request'
        command += ['--observation', str(destination / 'sampling')]
        started = time.monotonic()
        complete = False
        try:
            response = child(command, raw, **kwargs)
            complete = True
            return response
        finally:
            import json
            def read_optional(path):
                try:
                    return json.loads(path.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    return None
            snapshot = destination / 'sampling/observation.json'
            value = read_optional(snapshot)
            failure = destination / 'sampling/failure.json'
            elapsed = round((time.monotonic() - started) * 1000)
            # Worker observation begins after process startup. Use a parent
            # receipt time written by the child rather than equating their clocks.
            anchor = destination / 'sampling/anchor.json'
            anchor_value = read_optional(anchor)
            try:
                age = (round((time.monotonic() - anchor_value['parent_clock_started']) * 1000)
                       - value['observed_ms']) if value and anchor_value else None
            except (KeyError, TypeError, OverflowError):
                age = None
            valid = bool(value and anchor_value and not failure.exists() and age is not None
                         and -1000 <= age <= 3000 and value.get('http_requests') == 1)
            bridge.write_new_json(destination / 'parent-audit.json', dict(
                transport_complete=complete, elapsed_ms=elapsed, observation_present=value is not None,
                observation_age_ms=age, observation_valid=valid, observation_failure=failure.exists(),
                files={p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in destination.rglob('*') if p.is_file()}))
            if complete and not valid:
                raise ValueError('repair_observation_incomplete')
    bridge.run_child = run_child
    return bridge


def verify_observation(stream, raw, *, observation_root=None, complete_required=False):
    """Read-only sidecar verification, including stopped/incomplete attempts."""
    import json
    stream = Path(stream).resolve()
    root = outside_runs(observation_root if observation_root is not None else OBSERVATION_ROOT)
    directory = root / hashlib.sha256(str(stream).encode()).hexdigest()
    binding, audit = directory / 'binding.json', directory / 'parent-audit.json'
    if not binding.exists() or not audit.exists():
        if complete_required:
            raise ValueError('repair_observation_missing')
        return dict(state='unavailable', worker_directory=str(stream))
    bound = json.loads(binding.read_text(encoding='utf-8'))
    expected = dict(version=VERSION, transport_id=TRANSPORT,
        request_sha256=hashlib.sha256(raw).hexdigest(), worker_directory=str(stream),
        route=dict(route='direct', destination_host='open.bigmodel.cn', process_proxy_present=False,
                   no_proxy_matches_host=True, system_network_path_proven=False))
    if bound != expected:
        raise ValueError('repair_observation_binding_changed')
    record = json.loads(audit.read_text(encoding='utf-8'))
    actual = {p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for p in directory.rglob('*') if p.is_file() and p != audit}
    if actual != record['files']:
        raise ValueError('repair_observation_evidence_changed')
    if complete_required and (record['transport_complete'] is not True or record['observation_valid'] is not True):
        raise ValueError('repair_observation_incomplete')
    return dict(state='valid' if record['observation_valid'] else 'incomplete',
                worker_directory=str(stream), files={**actual,
                'parent-audit.json':hashlib.sha256(audit.read_bytes()).hexdigest()})


def worker(args):
    import openai
    route_record(os.environ)
    observer = StreamObservation(outside_runs(args.observation))
    legacy.write_new_json(observer.directory / 'anchor.json', dict(parent_clock_started=observer.started))
    original = openai.OpenAI

    def observed_client(**kwargs):
        client = kwargs['http_client']
        client.event_hooks['request'].append(observer.on_request)
        client.event_hooks['response'].append(observer.on_response)
        return original(**kwargs)
    openai.OpenAI = observed_client
    bridge = isolated_bridge()
    try:
        bridge.worker(args.worker, args.started, args.deadline, args.transport_id,
                      stream_tool_arguments=not args.buffered_tools)
    except BaseException as error:
        bridge.write_new_json(args.worker / 'failure.json', dict(
            category='assembly_rejected' if isinstance(error, bridge.StreamAdapterError) else 'worker_failed',
            assembly_code=error.code if isinstance(error, bridge.StreamAdapterError) else None,
            provider_code=error.code if isinstance(error, bridge.ProviderError)
                and error.code in bridge.SAFE_PROVIDER_FAILURE_CODES else None))
        raise SystemExit(1) from None
    finally:
        openai.OpenAI = original
        observer.close()
        if observer.failure:
            bridge.write_new_json(observer.directory / 'failure.json', dict(code=observer.failure))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', required=True, type=Path)
    parser.add_argument('--observation', required=True, type=Path)
    parser.add_argument('--started', required=True, type=float)
    parser.add_argument('--deadline', required=True, type=float)
    parser.add_argument('--transport-id', required=True, choices=(TRANSPORT,))
    parser.add_argument('--buffered-tools', action='store_true')
    worker(parser.parse_args())


if __name__ == '__main__':
    main()
