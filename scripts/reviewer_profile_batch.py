"""Four-request research controller; no credential discovery or paid CLI.

This is the batch control layer, not an execution authorization. A future live
caller must bind account/group, cost consent, exact checkout/CI and network
preflight in before_send, and explicitly supply the single-call sender. Test
injection is engineering evidence only. Neither mode grants qualification.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
from importlib.metadata import version as installed_version
import math
from pathlib import Path
import subprocess
import sys

from scripts import prepare_reviewer_profile_screen as screen
from scripts.codex_review_event_source import CodexHostReviewEventSource
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.review_duty_host_gate import NativeGate
from scripts.review_independence_contract import FINAL_POLICY, MODE_V2, freeze_v2_identity
from scripts.reviewer_responses_process import read_json, screen_validator, valid_saved_usage, write_json
from scripts.reviewer_responses_transport import Profile, TOOL, build_wire, digest

VERSION = 'reviewer-profile-batch-v1'
KEYS = ('r01-facts', 'r01-completion', 'r02-facts', 'r02-completion')
RESERVATION = 64000 + 32768
ROOT = Path(__file__).resolve().parents[1]
BUDGET = dict(max_requests=4, input_per_request=64000, output_per_request=32768,
              total_tokens=4 * RESERVATION, timeout_s=300, supervisor_seconds=1200)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(folder):
    """Hash regular files and reject redirected evidence, including ancestors."""
    folder = Path(folder).absolute()
    if folder.resolve() != folder:
        raise ValueError('batch_redirected_directory')
    result = {}
    for path in sorted(folder.rglob('*')):
        if path.resolve() != path or path.is_symlink():
            raise ValueError('batch_redirected_evidence')
        if path.is_file():
            if path.stat().st_nlink != 1:
                raise ValueError('batch_linked_evidence')
            result[path.relative_to(folder).as_posix()] = sha(path)
    return result


def source_identity():
    paths = {p for base in ('app', 'scripts') for p in (ROOT / base).rglob('*.py')}
    paths.update(p for base in ('skills', 'examples/runtime_profiles') for p in (ROOT / base).rglob('*')
                 if p.is_file() and p.suffix in ('.md', '.json', '.yaml', '.yml', '.toml', '.txt', '.j2'))
    paths.update(p for name in ('pyproject.toml', 'uv.lock', 'requirements.txt') if (p := ROOT / name).is_file())
    if any(p.resolve() != p or p.stat().st_nlink != 1 for p in paths):
        raise ValueError('batch_linked_source')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
        capture_output=True, text=True).stdout.strip()
    return dict(head=head, files={p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)},
        python=str(Path(sys.executable).resolve()), python_version=sys.version,
        packages={name: installed_version(name) for name in ('openai', 'httpx', 'pydantic', 'jsonschema')})


def prepare(operator, *, group, primary, independent, python=sys.executable):
    """Build an offline proposal without creating directories or selecting a route."""
    operator = Path(operator).absolute()
    if operator.resolve() != operator or operator.is_relative_to(ROOT / 'data/runs'):
        raise ValueError('batch_operator_path')
    if operator.exists():
        raise ValueError('batch_operator_exists')
    if Path(python).resolve() != Path(sys.executable).resolve():
        raise ValueError('batch_actual_interpreter_required')
    profile = Profile(group=group)
    manifest, requests = screen.prepare()
    if read_json(screen.PACKAGE / 'manifest.json') != manifest:
        raise ValueError('batch_manifest_reconstruction')
    rows = []
    for key, original in zip(KEYS, manifest['rows']):
        path = screen.PACKAGE / 'requests' / (key + '.json')
        if original['id'] != key or read_json(path) != requests[key]:
            raise ValueError('batch_request_reconstruction')
        rows.append(dict(key=key, request_file_sha256=sha(path),
            manifest_request_sha256=original['request_sha256'],
            transport_request_sha256=digest(requests[key]),
            wire_sha256=digest(build_wire(requests[key])), report_sha256=original['report_sha256']))
    return freeze_v2_identity(dict(version=VERSION, operator=str(operator),
        package_inventory=inventory(screen.PACKAGE), source_sha256=sha(screen.MATERIAL),
        source_identity=source_identity(),
        profile=asdict(profile), rows=rows, keys=list(KEYS),
        budget=deepcopy(BUDGET),
        workspace=dict(cwd=str(ROOT), python=str(Path(python).resolve()),
            answers=str(operator.with_name(operator.name + '-authors'))),
        host_review_submission_mode=MODE_V2, host_review_evidence_policy=FINAL_POLICY,
        execution_ready=False, execution_authorized=False, qualified=False,
        publication_allowed=False, actual_channel_estimate=None),
        root_thread_id=primary, primary_id=primary, independent_id=independent)


class _CapturingClient:
    """Read through the trusted client; keep native pages in memory, never logs."""
    def __init__(self, client):
        self.client, self.pages = client, []

    def request(self, method, params):
        value = self.client.request(method, params)
        if method == 'thread/turns/list':
            self.pages.append(value)
        return value

    def __getattr__(self, name):
        return getattr(self.client, name)


class ExactNativeGate(NativeGate):
    """Prospective byte check; historical NativeGate behavior is unchanged."""
    def __init__(self, plan, workspace, event_source):
        if not isinstance(event_source, CodexHostReviewEventSource):
            raise ValueError('batch_native_source_required')
        super().__init__(plan, workspace, event_source)

    def _validate(self, handle, submission):
        accepted = super()._validate(handle, submission)
        original = submission['independent']['independent_source_event']
        client = _CapturingClient(self.event_source.client)
        event = CodexHostReviewEventSource(client, self.plan).fetch(
            event_id=original['event_id'], binding=handle['binding'])
        if event != original:
            raise ValueError('batch_native_event_changed')
        _, turn_id, message_id = original['event_id'].split('/')
        texts = [item['text'] for page in client.pages for turn in page['data']
                 if turn['id'] == turn_id for item in turn['items']
                 if item.get('id') == message_id and item.get('type') == 'agentMessage'
                 and item.get('phase') == 'final_answer']
        answer = self.workspace.answer_path(Path(handle['folder']) / 'task-checkpoint.json',
                                            handle['checkpoint_sha256'])
        if len(texts) != 1 or answer.read_bytes() != texts[0].encode('utf-8'):
            raise ValueError('batch_author_native_bytes_mismatch')
        return accepted


class ScreenBatch:
    def __init__(self, plan, event_source, gate_factory):
        self.plan = deepcopy(plan)
        self.operator = Path(plan['operator'])
        self.profile = Profile(**plan['profile'])
        self.workspace = HostReviewWorkspace(**plan['workspace'], evidence_roots=(self.operator,))
        self.gate = gate_factory(plan, self.workspace, event_source)
        self.fixture_only = gate_factory is not ExactNativeGate
        self.checkpoint_sha, self.state = None, None

    @classmethod
    def create(cls, plan, event_source, *, gate_factory=ExactNativeGate):
        instance = cls(plan, event_source, gate_factory)
        instance._sources()
        instance.operator.mkdir(parents=True, exist_ok=False)
        for name in ('checkpoints', 'claims', 'calls', 'reviews'):
            (instance.operator / name).mkdir()
        write_json(instance.operator / 'plan.json', plan)
        instance.state = dict(phase='ready', records=[], reason=None,
            fixture_only=instance.fixture_only, qualified=False, publication_allowed=False)
        instance._save()
        return instance

    @classmethod
    def load(cls, operator, checkpoint_sha, event_source, *, gate_factory=ExactNativeGate):
        plan = read_json(Path(operator) / 'plan.json')
        if not plan or Path(plan['operator']) != Path(operator).absolute():
            raise ValueError('batch_plan_path')
        instance = cls(plan, event_source, gate_factory)
        instance.checkpoint_sha = checkpoint_sha
        instance._check()
        return instance

    def _sources(self):
        if (self.plan['version'] != VERSION or self.plan['keys'] != list(KEYS)
                or self.plan['package_inventory'] != inventory(screen.PACKAGE)
                or self.plan['source_sha256'] != sha(screen.MATERIAL)
                or self.plan['source_identity'] != source_identity()):
            raise ValueError('batch_sources_changed')
        manifest = read_json(screen.PACKAGE / 'manifest.json')
        rows = []
        for key, original in zip(KEYS, manifest['rows']):
            path = screen.PACKAGE / 'requests' / (key + '.json')
            business = read_json(path)
            rows.append(dict(key=key, request_file_sha256=sha(path),
                manifest_request_sha256=original['request_sha256'],
                transport_request_sha256=digest(business), wire_sha256=digest(build_wire(business)),
                report_sha256=original['report_sha256']))
        if (self.plan['budget'] != BUDGET or self.plan['rows'] != rows
                or self.plan['workspace']['cwd'] != str(ROOT)
                or self.plan['workspace']['python'] != str(Path(sys.executable).resolve())
                or any(self.plan[field] is not False for field in
                       ('execution_ready', 'execution_authorized', 'qualified', 'publication_allowed'))):
            raise ValueError('batch_plan_contract')

    def _files(self):
        return {k: v for k, v in inventory(self.operator).items()
                if not k.startswith('checkpoints/')}

    def _pending_files(self):
        paths = sorted((self.operator / 'checkpoints').iterdir())
        files = self._files()
        old = {}
        old_state = None
        if paths:
            if sha(paths[-1]) != self.checkpoint_sha:
                raise ValueError('batch_stale_checkpoint')
            previous = read_json(paths[-1])
            old, old_state = previous['inventory'], previous['state']
            if any(files.get(k) != v for k, v in old.items()):
                raise ValueError('batch_evidence_changed_during_operation')
        allowed = set(old) | {'plan.json', 'seal.json'}
        for index, row in list(enumerate(self.state['records']))[-1:]:
            name = f"{index:02}-{row['key']}"
            if old_state and old_state['phase'] == 'ready' and len(old_state['records']) == index:
                allowed.add('claims/' + name + '.json')
            if old_state and old_state['phase'] == 'in_flight':
                allowed.update('calls/' + name + '/' + tail for tail in (
                    'request.json', 'profile.json', 'receipt.json', 'usage.json',
                    'worker-result.json', 'observation/observation.json'))
                if self.state['phase'] != 'awaiting_review':
                    allowed.add('calls/' + name + '/observation/observation.tmp')
                allowed.update('reviews/' + name + '/' + tail for tail in (
                    'material.json', 'independent-task.json', 'task-checkpoint.json', 'dispatch.txt'))
            if old_state and old_state['phase'] == 'awaiting_review':
                allowed.add('reviews/' + name + '/submission.json')
        if set(files) - allowed:
            raise ValueError('batch_uncheckpointed_evidence')
        return files

    def _save(self):
        files = self._pending_files()
        paths = sorted((self.operator / 'checkpoints').iterdir())
        value = dict(version=VERSION, previous_sha256=self.checkpoint_sha,
            state=self.state, inventory=files)
        path = self.operator / 'checkpoints' / f'{len(paths):03}.json'
        write_json(path, value)
        self.checkpoint_sha = sha(path)

    def _check(self):
        self._sources()
        paths = sorted((self.operator / 'checkpoints').iterdir())
        previous, latest = None, None
        for index, path in enumerate(paths):
            value = read_json(path)
            if (path.name != f'{index:03}.json' or not value or value['version'] != VERSION
                    or value['previous_sha256'] != previous):
                raise ValueError('batch_checkpoint_chain')
            previous, latest = sha(path), value
        if not latest or previous != self.checkpoint_sha:
            raise ValueError('batch_stale_checkpoint')
        if latest['inventory'] != self._files():
            raise ValueError('batch_uncheckpointed_evidence')
        if read_json(self.operator / 'plan.json') != self.plan:
            raise ValueError('batch_plan_changed')
        self.state = deepcopy(latest['state'])
        if self.state['fixture_only'] != self.fixture_only:
            raise ValueError('batch_review_authority_changed')
        for row in self.state['records']:
            if 'review_accepted' in row and self.gate.replay(row['handle']) != row['review_accepted']:
                raise ValueError('batch_review_changed')
        return self.state

    def status(self):
        """Strict read-only replay, including original native judgments and authors."""
        self._check()
        records = self.state['records']
        return dict(phase=self.state['phase'], reason=self.state['reason'],
            next_key=KEYS[len(records)] if self.state['phase'] == 'ready' and len(records) < 4 else None,
            calls=sum(r['usage_state'] != 'not_sent' for r in records), claimed_slots=len(records),
            known_tokens=sum(r['usage']['total_tokens'] for r in records if r['usage_state'] == 'known'),
            unknown_reserved_tokens=sum(RESERVATION for r in records if r['usage_state'] == 'unknown'),
            not_sent=sum(r['usage_state'] == 'not_sent' for r in records),
            unused_slots=4-len(records),
            unreviewed_calls=sum('review_accepted' not in r and r['usage_state'] != 'not_sent' for r in records),
            http_requests_known=sum(r['http_requests'] for r in records if r['http_requests'] is not None),
            http_requests_unknown=sum(r['http_requests'] is None for r in records),
            supervisor_seconds=sum(r['elapsed_s'] for r in records),
            fixture_only=self.fixture_only, qualified=False, publication_allowed=False)

    inspect = status

    def _finish(self, reason):
        self._sources()
        self._pending_files()
        for row in self.state['records']:
            if 'review_accepted' in row and self.gate.replay(row['handle']) != row['review_accepted']:
                raise ValueError('batch_review_changed')
        self.state.update(phase='closed', reason=reason)
        write_json(self.operator / 'seal.json', dict(version=VERSION, reason=reason,
            preceding_checkpoint_sha256=self.checkpoint_sha, records=self.state['records'],
            fixture_only=self.fixture_only, qualified=False, publication_allowed=False))
        self._save()

    def close(self):
        self._check()
        if self.state['phase'] not in ('ready', 'awaiting_review'):
            raise ValueError('batch_not_closable')
        self._finish('operator_stop')
        return self.status()

    def _receipt(self, directory, business, returned, timeout):
        """Validate saved public evidence separately from semantic acceptance."""
        receipt = read_json(directory / 'receipt.json')
        if not receipt or receipt != returned:
            raise ValueError('batch_receipt_missing_or_changed')
        if (receipt.get('version') != 'research-responses-single-call-v1'
                or receipt.get('request_sha256') != digest(business)
                or receipt.get('wire_sha256') != digest(build_wire(business))
                or receipt.get('profile') != asdict(self.profile)
                or read_json(directory / 'request.json') != business):
            raise ValueError('batch_receipt_binding')
        profile = read_json(directory / 'profile.json')
        expected = dict(**asdict(self.profile), reasoning_effort='high', api='responses',
            max_output_tokens=32768, max_retries=0, timeout_s=timeout,
            group_verified=False, upstream_identity_verified=False)
        if profile != expected:
            raise ValueError('batch_profile_binding')
        usage, state, elapsed = receipt.get('usage'), receipt.get('usage_state'), receipt.get('elapsed_s')
        if (state not in ('known', 'unknown', 'not_sent') or
                type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0):
            raise ValueError('batch_usage_or_time_invalid')
        if state == 'known' and (not valid_saved_usage(usage) or receipt.get('usage_conflict') is not False):
            raise ValueError('batch_known_usage_invalid')
        if state == 'not_sent' and (usage is not None or receipt.get('http_requests') != 0
                                   or receipt.get('worker_exit') is not None):
            raise ValueError('batch_not_sent_invalid')
        count = receipt.get('http_requests')
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError('batch_http_count_invalid')
        row = dict(usage_state=state, usage=usage if state == 'known' else None,
                   elapsed_s=elapsed, http_requests=count)
        if receipt.get('ok') is not True:
            return row, 'call_failed'
        if (state != 'known' or usage['input_tokens'] > 64000 or usage['output_tokens'] > 32768
                or elapsed > timeout or receipt.get('code') != 'ok'
                or receipt.get('http_requests') != 1 or receipt.get('reaped') is not True
                or receipt.get('worker_exit') != 0):
            return row, 'call_budget_or_receipt_invalid'
        observation = read_json(directory / 'observation/observation.json')
        worker = read_json(directory / 'worker-result.json')
        if (not observation or observation.get('schema_version') != 'stream-observation-v1'
                or observation.get('body_free') is not True or observation.get('http_requests') != 1
                or observation.get('response_status') != 200 or observation.get('eof') is not True
                or observation.get('closed') is not True or observation.get('exception_type') is not None
                or not worker or worker.get('ok') is not True or worker.get('usage') != usage
                or read_json(directory / 'usage.json') != usage
                or worker.get('business_validated') is not True or worker.get('semantic_approval') is not False):
            return row, 'call_observation_or_worker_invalid'
        tool = worker.get('public_tool_call')
        if (not isinstance(tool, dict) or tool.get('name') != TOOL
                or not tool.get('id') or not tool.get('call_id') or not isinstance(tool.get('arguments'), str)):
            return row, 'call_tool_invalid'
        try:
            screen_validator(business)(tool['arguments'])
        except Exception:
            return row, 'call_business_invalid'
        return row, None

    def send_next(self, sender, *, before_send=None):
        status = self.status()
        if status['phase'] != 'ready' or not status['next_key']:
            raise ValueError('batch_not_ready')
        if not self.fixture_only and before_send is None:
            raise ValueError('batch_live_preflight_required')
        timeout = min(300, 1200 - status['supervisor_seconds'])
        if (timeout <= 0 or status['known_tokens'] + status['unknown_reserved_tokens'] + RESERVATION
                > 4 * RESERVATION):
            self._finish('budget_exhausted')
            return self.status()
        if before_send is not None:
            try:
                before_send()
            except (Exception, KeyboardInterrupt):
                self._finish('preflight_failed')
                raise ValueError('batch_preflight_failed') from None
        self._check()  # Native/source checks may not be cached across preflight.
        index, key = len(self.state['records']), status['next_key']
        name = f'{index:02}-{key}'
        directory = self.operator / 'calls' / name
        if directory.exists():
            raise ValueError('batch_existing_call')
        business = read_json(screen.PACKAGE / 'requests' / (key + '.json'))
        write_json(self.operator / 'claims' / (name + '.json'), dict(key=key,
            checkpoint_sha256=self.checkpoint_sha, request_sha256=digest(business)))
        row = dict(key=key, directory=str(directory), usage_state='unknown', usage=None,
                   elapsed_s=timeout, http_requests=None)
        self.state['records'].append(row)
        self.state['phase'] = 'in_flight'
        self._save()  # Crash after this point cannot return to ready or resend.
        returned = None
        try:
            returned = sender(business, profile=self.profile, directory=directory, timeout_s=timeout)
            account, failure = self._receipt(directory, business, returned, timeout)
            row.update(account)
        except (Exception, KeyboardInterrupt):
            failure = 'call_or_storage_incomplete'  # Never persist arbitrary exception text.
            # A supervisor receipt-write failure must not erase usage already
            # recorded by its worker. Conflicting observations stay unknown.
            saved = [read_json(directory / name) for name in ('usage.json', 'worker-result.json', 'receipt.json')]
            receipts = [v for v in [*saved[1:], returned] if isinstance(v, dict)]
            values = [saved[0], *[v.get('usage') for v in receipts]]
            values = [v for v in values if valid_saved_usage(v)]
            expected_profile = dict(**asdict(self.profile), reasoning_effort='high', api='responses',
                max_output_tokens=32768, max_retries=0, timeout_s=timeout,
                group_verified=False, upstream_identity_verified=False)
            bound = (read_json(directory / 'request.json') == business and
                     read_json(directory / 'profile.json') == expected_profile)
            if (bound and values and all(v == values[0] for v in values)
                    and not any(v.get('usage_conflict') for v in receipts)):
                row.update(usage_state='known', usage=values[0])
        if failure:
            self._finish(failure)
            return self.status()
        worker = read_json(directory / 'worker-result.json')
        binding = dict(plan_sha256=digest(self.plan), key=key, stage='initial',
            response_sha256=sha(directory / 'worker-result.json'),
            report_sha256=self.plan['rows'][index]['report_sha256'], request_sha256=digest(business))
        material = dict(report=(screen.PACKAGE / (key.split('-')[0] + '.md')).read_text(encoding='utf-8'),
            complete_request=business, public_tool_call=worker['public_tool_call'],
            instruction='Review this entire opinion against the complete report, user request, '
                'source data and duty policy, including every issue, correction and preserved claim. '
                'Reject missed errors, false positives and incorrect explanations or repairs. '
                'A newly discovered real error can invalidate a material premise. '
                'Schema validity and score are not evidence of correctness.')
        try:
            row['handle'] = self.gate.publish(self.operator / 'reviews' / name, binding, 'opinion', material)
        except (Exception, KeyboardInterrupt):
            self._finish('review_dispatch_failed')
            return self.status()
        self.state['phase'] = 'awaiting_review'
        self._save()
        return self.status()

    def submit_review(self, primary_decision, event_id):
        self._check()
        if self.state['phase'] != 'awaiting_review':
            raise ValueError('batch_not_awaiting_review')
        row = self.state['records'][-1]
        try:
            row['review_accepted'] = self.gate.submit(row['handle'], primary_decision, event_id)
        except (Exception, KeyboardInterrupt):
            self._finish('review_import_failed')
            raise ValueError('batch_review_import_failed') from None
        if row['review_accepted'] is not True:
            self._finish('semantic_rejection')
        elif len(self.state['records']) == 4:
            self._finish('screen_reviewed')
        else:
            self.state['phase'] = 'ready'
            self._save()
        return self.status()
