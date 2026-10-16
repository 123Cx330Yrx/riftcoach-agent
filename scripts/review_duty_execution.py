"""One fixed-report development chain with native judgments and one shared budget.

Dependency-injected execution core, not a paid entrypoint. No credentials,
provider factory, authorization issuer, restart or product registration.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
import re
from pathlib import Path
import time

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import _mapping
from app.evaluation.source_patch_editor import report_inputs
from app.providers.models import ChatResponse
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.runtime import _ReceiptForwardingCoachBudgetedProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.reviewer_roles import ROLE_COMPOSITION_ID, ROLE_PROFILE_ID
from scripts import review_duty_composition as duty
from scripts.review_duty_host_gate import NativeGate, sha
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.role_development_host_clock import DevelopmentHostClock
from scripts.review_independence_contract import canonical_json, freeze_v2_identity, MODE_V2, FINAL_POLICY

VERSION = 'complementary-review-development-chain-v1'
ROOT = Path(__file__).resolve().parents[1]
LIMITS = dict(max_calls=5, total_tokens=483840, execution_timeout_s=2700,
              request_timeout_s=600, max_input_tokens=64000, max_output_tokens=32768)
SLOTS = ('facts-initial', 'completion-initial', 'edit', 'facts-fresh', 'completion-fresh')


def request_bytes(request):
    return json.dumps(request, default=_mapping, ensure_ascii=False, allow_nan=False).encode('utf-8')


def check_issued(prepared, issued):
    metadata = dict(issued.metadata)
    if metadata.pop('coach_budget_contract', None) not in (None, 'coach-bounded-review-v2'):
        raise ValueError('duty_execution_budget_marker')
    if (not 0 < issued.timeout_s <= prepared.timeout_s
            or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared):
        raise ValueError('duty_execution_request_changed')
    return request_bytes(issued)


def model_for(request):
    marker = request.metadata[duty.MARKER]
    if marker['version'] != duty.VERSION:
        raise ValueError('duty_execution_version')
    return 'glm-5.3-flash' if marker['duty'] == 'editor' else 'glm-5.3'


def public_response(response):
    return dict(provider=response.provider, model=response.model,
        content=response.content, finish_reason=response.finish_reason,
        tool_calls=[dict(id=t.id,name=t.name,arguments=dict(t.arguments)) for t in response.tool_calls],
        usage=dict(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens))


def write_response(path, response):
    # Preserve tool-argument insertion order: the exact opinion string is later
    # embedded in compatibility/edit inputs. Sorting here breaks durable replay.
    with path.open('xb') as file:
        file.write(json.dumps(public_response(response),ensure_ascii=False,
            allow_nan=False,separators=(',',':')).encode('utf-8'))
        file.flush()
        os.fsync(file.fileno())


class Limits:
    grounded = True
    def descriptor(self):
        return dict(LIMITS)
    @staticmethod
    def request_identity(request):
        return 'zhipu', model_for(request)


class BoundProvider:
    """Actual sender must return its issued request, response and receipt SHA."""
    provider_name = 'zhipu'
    model_name = ROLE_COMPOSITION_ID
    thinking_profile_id = ROLE_PROFILE_ID
    sdk_max_retries = 0
    runtime_profile = None
    capabilities = frozenset()

    def __init__(self, send, before_send):
        self.send, self.before_send = send, before_send
        self.prepared = self.folder = self.last_exchange = None

    def chat(self, request):
        check_issued(self.prepared, request)
        self.before_send()
        raw = request_bytes(request)
        with (self.folder / 'issued-request.json').open('xb') as file:
            file.write(raw)
        try:
            exchange = self.send(request, self.folder)
        except BaseException as error:
            response = getattr(error, 'observed_response', None)
            if isinstance(response, ChatResponse):
                write_response(self.folder/'response.json', response)
            raise
        if not isinstance(exchange, Exchange):
            raise ValueError('duty_execution_receipt_required')
        # Retain complete public output even when its receipt/identity is rejected.
        if isinstance(exchange.response, ChatResponse):
            write_response(self.folder/'response.json', exchange.response)
        receipt = exchange.receipt_request_sha256
        write_new_json(self.folder/'receipt.json', dict(
            issued_request_sha256=hashlib.sha256(request_bytes(exchange.issued_request)).hexdigest(),
            receipt_request_sha256=receipt if isinstance(receipt,str) and re.fullmatch(r'[0-9a-f]{64}',receipt) else None,
            response_sha256=sha(self.folder/'response.json') if (self.folder/'response.json').exists() else None))
        if (exchange.issued_request != request or request_bytes(exchange.issued_request) != raw
                or exchange.receipt_request_sha256 != hashlib.sha256(raw).hexdigest()):
            error = ValueError('duty_execution_receipt_changed')
            error.observed_response = exchange.response
            raise error
        self.last_exchange = exchange
        return exchange.response


def preparation(inputs, *, primary, independent):
    plan = freeze_v2_identity(dict(kind=VERSION, host_review_submission_mode=MODE_V2,
        host_review_evidence_policy=FINAL_POLICY, input_sha256=digest(inputs.data_json),
        report_sha256=digest(inputs.source.report), limits=LIMITS, maximum_host_seconds=86400,
        slots=SLOTS, execution_ready=False, execution_authorized=False,
        initial_requests={d:duty.request_sha(duty.review_request(inputs, d)) for d in duty.DUTIES}),
        root_thread_id=primary, primary_id=primary, independent_id=independent)
    plan['source_sha256'] = {p:sha(ROOT/p) for p in (
        'scripts/review_duty_execution.py', 'scripts/review_duty_host_gate.py',
        'scripts/review_duty_composition.py', 'scripts/host_review_workspace.py',
        'scripts/host_review_task_checkpoint.py', 'scripts/codex_review_event_source.py',
        'scripts/review_independence_contract.py', 'scripts/role_development_host_clock.py',
        'scripts/report_block_keyed_editor.py', 'app/runtime/coach_budget.py',
        'scripts/review_duty_transport.py', 'scripts/review_duty_replay.py',
        'scripts/full_chain_modules.py', 'scripts/full_chain_observed_transport.py',
        'scripts/stream_observation.py', 'app/evaluation/golden_stream_bridge.py')}
    return json.loads(canonical_json(plan))


class DevelopmentChain:
    def __init__(self, *, directory, answers, observations, inputs, plan, event_source,
                 send, observe, judge, before_send, wall_clock=time.monotonic):
        self.directory = Path(directory).absolute()
        self.observations = Path(observations).absolute()
        self.workspace = HostReviewWorkspace(cwd=ROOT, python=__import__('sys').executable,
            answers=answers, evidence_roots=(ROOT/'data/runs', self.directory))
        paths = (self.directory, self.workspace.answers, self.observations)
        if any(p.resolve() != p for p in paths) or any(a.is_relative_to(b) or b.is_relative_to(a)
                for n,a in enumerate(paths) for b in paths[n+1:]):
            raise ValueError('duty_execution_paths')
        if self.observations.is_relative_to(ROOT/'data/runs'):
            raise ValueError('duty_execution_observation_path')
        self.inputs, self.plan = inputs, deepcopy(plan)
        self.pin = hashlib.sha256(canonical_json(plan)).hexdigest()
        self.gate = NativeGate(self.plan, self.workspace, event_source)
        self.send, self.observe, self.judge, self.before = send, observe, judge, before_send
        self.wall_clock = wall_clock
        self.handles, self.attempts, self.inventory = [], [], {}
        self.started = self.stopped = False
        self.failure = None
        self.budget = None
        self._validate_plan()

    def _validate_plan(self):
        if not getattr(self, '_prepared_checked', False):
            expected = preparation(self.inputs,
                primary=self.plan['review_principals']['primary']['principal_id'],
                independent=self.plan['review_principals']['independent']['principal_id'])
            if self.plan != expected:
                raise ValueError('duty_execution_plan_changed')
            self._prepared_checked = True
        if (hashlib.sha256(canonical_json(self.plan)).hexdigest() != self.pin
                or self.plan['input_sha256'] != digest(self.inputs.data_json)
                or self.plan['report_sha256'] != digest(self.inputs.source.report)
                or any(sha(ROOT/p) != pin for p,pin in self.plan['source_sha256'].items())):
            raise ValueError('duty_execution_plan_changed')

    def snapshot(self):
        result = {}
        for root in (self.directory, self.workspace.answers, self.observations):
            if root.resolve() != root or root.is_symlink():
                raise ValueError('duty_execution_linked_evidence_root')
            if root.exists():
                for p in root.rglob('*'):
                    if p.resolve() != p.absolute() or p.is_symlink() or p.is_file() and p.stat().st_nlink != 1:
                        raise ValueError('duty_execution_linked_evidence')
                    if root == self.directory:
                        relative = p.relative_to(root).as_posix()
                        allowed = {'plan.json', 'result.json', 'closure.json', 'development-host-clock'}
                        allowed.update(SLOTS)
                        allowed.update('host-'+k for k in (*SLOTS, 'compatibility'))
                        valid = (relative in allowed or re.fullmatch(
                            r'development-host-clock/(policy|[0-9]{4}-(waiting|finished))\.json', relative)
                            or any(relative == s+'/'+f for s in SLOTS for f in
                                ('prepared-request.json','issued-request.json','response.json','receipt.json','call-state.json'))
                            or any(relative in (s+'/transport',s+'/transport/stream-001') or
                                relative in {s+'/transport/stream-001/'+f for f in
                                    ('reservation.json','result.json','progress.json','progress.tmp','failure.json','rejected-tool-output.json')}
                                for s in SLOTS)
                            or any(relative == 'host-'+s+'/'+f for s in (*SLOTS,'compatibility') for f in
                                ('material.json','independent-task.json','task-checkpoint.json','dispatch.txt','submission.json')))
                        if not valid:
                            raise ValueError('duty_execution_unexpected_file')
                    result[str(p)] = sha(p) if p.is_file() else 'directory'
        return result

    def _pin(self):
        current = self.snapshot()
        if any(current.get(p) != h for p,h in self.inventory.items()):
            raise ValueError('duty_execution_existing_evidence_changed')
        self.inventory = current

    def check(self, *, allow_new=()):
        self.workspace.validate_paths()
        self._validate_plan()
        current = self.snapshot()
        if (any(current.get(p) != h for p,h in self.inventory.items())
                or not set(current).difference(self.inventory).issubset({str(p) for p in allow_new})):
            raise ValueError('duty_execution_inventory_changed')
        for attempt in self.attempts:
            if attempt['complete'] or attempt.get('observation_verified'):
                checked = self.observe(Path(attempt['folder']), self.observations,
                    complete_required=attempt['complete'] or attempt.get('response_present',False))
                if checked != attempt['observation']:
                    raise ValueError('duty_execution_observation_changed')
        expected = {}
        for attempt in self.attempts:
            if attempt.get('complete') or attempt.get('observation_verified'):
                expected.update(attempt['observation'])
        actual = {str(p):sha(p) for p in self.observations.rglob('*') if p.is_file()}
        if actual != expected or any(not any(Path(f).is_relative_to(p) for f in actual)
                for p in self.observations.rglob('*') if p.is_dir()):
            raise ValueError('duty_execution_observation_inventory')
        for handle in self.handles:
            self.gate.replay(handle)  # Refetch real native events, never trust saved acceptance alone.

    def _before(self):
        if self.stopped:
            raise ValueError('duty_execution_stopped')
        self.check()
        self.clock.before_send()
        self.before()
        self.check()

    def _call(self, slot, prepared):
        self._before()
        folder = self.directory / slot
        folder.mkdir(exist_ok=False)
        (folder/'prepared-request.json').write_bytes(request_bytes(prepared))
        attempt = dict(slot=slot, folder=str(folder), complete=False)
        self.attempts.append(attempt)
        self.adapter.prepared, self.adapter.folder = prepared, folder
        self._pin()
        started = self.clock()
        before = dict(calls=self.budget.calls, known_tokens=self.budget.tokens,
            unknown_reserved_tokens=self.budget.reserved_tokens)
        try:
            exchange = SharedBudgetReviewSender(self.budget)(prepared)
        finally:
            write_new_json(folder/'call-state.json', dict(before=before,
                after=dict(calls=self.budget.calls, known_tokens=self.budget.tokens,
                    unknown_reserved_tokens=self.budget.reserved_tokens),
                active_started=started, active_finished=self.clock()))
        # Complete responses always require valid observations, even if later parsing fails.
        attempt.update(complete=True, observation=self.observe(folder, self.observations, complete_required=True))
        self._pin()
        return exchange

    def _host(self, key, kind, stage, material, request_sha, response_sha, report):
        self._before()
        bound = dict(plan_sha256=self.pin, key=key, stage=stage,
            request_sha256=request_sha, response_sha256=response_sha, report_sha256=digest(report))
        handle = self.gate.publish(self.directory / ('host-'+key), bound, kind, material)
        self._pin()
        # The callback only supplies the root's own decision and an event locator.
        # NativeGate imports the independent final and checks the author's file.
        def callback(available):
            self._pin()  # The owned clock just published this wait's receipt.
            decision, event_id = self.judge(handle, available)
            # Only the designated external author file may have appeared during judgment.
            answer = self.workspace.answer_path(Path(handle['folder'])/'task-checkpoint.json', handle['checkpoint_sha256'])
            current = self.snapshot()
            extra = set(current)-set(self.inventory)
            if any(current.get(p) != h for p,h in self.inventory.items()) or extra != {str(answer)}:
                raise ValueError('duty_execution_host_inventory_changed')
            accepted = self.gate.submit(handle, decision, event_id)
            after = self.snapshot()
            if (set(after)-set(current) != {str(Path(handle['folder'])/'submission.json')}
                    or any(after.get(p) != h for p,h in current.items())):
                raise ValueError('duty_execution_native_mutation')
            self.handles.append(handle)
            return accepted
        accepted = self.clock._wait(bound, callback)
        self._pin()
        self.check()
        return accepted

    def _review(self, duty_name, stage, inputs):
        slot = duty_name+'-'+stage
        prepared = duty.review_request(inputs, duty_name, stage)
        exchange = self._call(slot, prepared)
        response = exchange.response
        if (response.provider != 'zhipu' or response.model != 'glm-5.3'
                or response.finish_reason != 'tool_calls' or (response.content or '').strip()
                or len(response.tool_calls) != 1 or response.tool_calls[0].name != 'submit_report_review'):
            raise ValueError('duty_execution_review_channel')
        raw = compact(dict(response.tool_calls[0].arguments))
        opinion = duty.bind(inputs, duty_name, stage, raw)
        folder = self.directory/slot
        material = dict(kind='opinion', duty=duty_name, review_stage=stage,
            report=inputs.source.report, current_input_json=inputs.data_json,
            request=json.loads(request_bytes(exchange.issued_request)), response=json.loads((folder/'response.json').read_bytes()))
        accepted = self._host(slot, 'opinion', 'initial' if stage=='initial' else 'final', material,
            sha(folder/'issued-request.json'), sha(folder/'response.json'), inputs.source.report)
        return opinion, accepted

    def run(self):
        if self.started or any(p.exists() for p in (self.directory,self.workspace.answers,self.observations)):
            raise ValueError('duty_execution_already_started')
        self.started = True
        self.directory.mkdir(parents=True, exist_ok=False)
        self.observations.mkdir(parents=True, exist_ok=False)
        self.workspace.answers.mkdir(parents=True, exist_ok=False)
        write_new_json(self.directory/'plan.json', self.plan)
        self.clock = DevelopmentHostClock(self.directory, max_host_seconds=86400,
            wall_clock=self.wall_clock, plan_sha256=self.pin)
        self.adapter = BoundProvider(self.send, self._before)
        self.budget = _ReceiptForwardingCoachBudgetedProvider(self.adapter,
            clock=self.clock, coach_contract=ROLE_COACH_CONTRACT)
        # Instance-only development envelope; public production registry stays unchanged.
        self.budget.contract = Limits()
        self._pin()
        outcome, error = 'hard_failure', None
        try:
            outcome = self._run_chain()
        except BaseException as exc:
            self.failure = exc
            error = type(exc).__name__  # Never persist SDK text or private reasoning.
            self.stopped = self.budget.stopped = True
            if self.attempts and not self.attempts[-1]['complete']:
                tail = self.attempts[-1]
                tail['response_present'] = (Path(tail['folder'])/'response.json').exists()
                try:
                    tail['observation'] = self.observe(Path(tail['folder']), self.observations,
                        complete_required=tail['response_present'])
                    tail['observation_verified'] = True
                except Exception:
                    tail['observation_verified'] = False
        self.stopped = self.budget.stopped = True
        result = dict(kind=VERSION, outcome=outcome, error_type=error,
            calls=self.budget.calls, known_tokens=self.budget.tokens,
            unknown_reserved_tokens=self.budget.reserved_tokens,
            attempts=deepcopy(self.attempts), host_handles=deepcopy(self.handles),
            timing=self.clock.summary(), production_admitted=False, restart_allowed=False)
        write_new_json(self.directory/'result.json', result)
        try:
            self._pin()
            # The caller must retain this digest outside the run. Replayers must
            # receive it explicitly, never accept a newly computed trust root.
            write_new_json(self.directory/'closure.json', dict(kind='review-duty-closure-v1',
                plan_sha256=self.pin, directory=str(self.directory), answers=str(self.workspace.answers),
                observations=str(self.observations), python=str(self.workspace.python), files=self.inventory))
            self.closure_sha256 = sha(self.directory/'closure.json')
            self._pin()
        except ValueError:
            if outcome != 'hard_failure':
                raise
        return result

    def _run_chain(self):
        opinions = []
        for name in duty.DUTIES:
            opinion, accepted = self._review(name, 'initial', self.inputs)
            opinions.append(opinion)
            if not accepted or duty.validate(opinion.raw, self.inputs, name).verdict == 'fail':
                return 'initial_rejected'
        context = duty.pair(self.inputs, opinions, 'initial')
        if context['all_duties_pass']:
            return 'initial_both_pass_no_edit'
        material = dict(report=self.inputs.source.report, current_input_json=self.inputs.data_json,
            duty_reviews=context, policies={d:duty.review_request(self.inputs,d).messages[0].content for d in duty.DUTIES})
        # Both complete raw Provider opinions are bound, without either Host's judgment.
        pair_sha = hashlib.sha256(canonical_json(material)).hexdigest()
        if not self._host('compatibility','compatibility','initial',material,pair_sha,pair_sha,self.inputs.source.report):
            return 'incompatible_opinions'
        prepared = duty.edit_request(self.inputs, opinions, conflict_status='clear')
        exchange = self._call('edit', prepared)
        assembly = duty.inspect_edit(prepared,exchange,self.inputs,opinions,conflict_status='clear')
        material = dict(original_report=self.inputs.source.report, actual_report=assembly.report,
            current_input_json=self.inputs.data_json, journal=assembly.journal,
            request=json.loads(request_bytes(exchange.issued_request)),
            response=json.loads((self.directory/'edit/response.json').read_bytes()))
        if not self._host('edit','edit','revision',material,sha(self.directory/'edit/issued-request.json'),
                sha(self.directory/'edit/response.json'),assembly.report):
            return 'edit_rejected'
        revised = report_inputs(self.inputs,assembly.report)
        fresh = []
        for name in duty.DUTIES:
            opinion, accepted = self._review(name,'fresh',revised)
            fresh.append(opinion)
            if not accepted or duty.validate(opinion.raw,revised,name).verdict != 'pass':
                return 'fresh_rejected'
        duty.pair(revised,fresh,'fresh')
        return 'development_chain_pass'

    def replay(self):
        if not self.stopped or not (self.directory/'result.json').exists():
            raise ValueError('duty_execution_not_closed')
        self.check()
        return json.loads((self.directory/'result.json').read_bytes())
