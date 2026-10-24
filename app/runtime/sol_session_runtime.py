"""Candidate-only local replay above provider observation and its shared budget.

Derived Runtime traces contain only new provider IO, not replayed completions.
The durable session's cumulative budget is the task accounting authority.
"""
from dataclasses import replace
import json

from pydantic import TypeAdapter

from app.evaluation import sol_natural_contract as contract
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_stream_bridge import REQUEST, RESPONSE
from app.evaluation.natural_duty_workflow import NaturalDutyWorkflow
from app.evaluation.sol_natural_session import SessionBlocked, SessionPaused, canonical, digest
from app.providers.errors import ProviderError, ProviderResponseError
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.sol_natural_provider import SolNaturalProvider
from app.tools.models import ToolResult
from app.tools.runtime import ToolRuntime

TOOL_RESULT = TypeAdapter(ToolResult)


class SessionBudget(CoachBudgetedProvider):
    def __init__(self, provider, *, session, coach_contract):
        contract = self.contract_module = session.contract_module
        if coach_contract is not contract.CONTRACT or not isinstance(provider, ObservedLLMProvider):
            raise ValueError('session_budget_requires_observed_sol')
        if type(provider._delegate) is not SolNaturalProvider:
            raise ValueError('session_router_type')
        if provider._delegate.contract_module is not contract:
            raise ValueError('session_router_contract')
        if provider._delegate.reviewer.task_directory.resolve() != session.transport_root:
            raise ValueError('session_transport_root_binding')
        if session.binding.get('fixture_only') is not True and session.review_gate is None:
            raise ValueError('session_native_review_gate_required')
        super().__init__(provider, coach_contract=coach_contract)
        self.session, self.router = session, provider._delegate
        self._exchange = None

    @property
    def last_exchange(self):
        return None if self.stopped else self._exchange

    def _provider_for_request(self, request):
        self.session.capture_attempt(self.calls+1,
            self.contract_module.request_bytes(request).decode('utf-8'), self.snapshot(),
            retry_pending=self.router._retry_request is not None)
        return super()._provider_for_request(request)

    def snapshot(self):
        router = self.router
        value = dict(calls=self.calls, tokens=self.tokens, reserved_tokens=self.reserved_tokens,
            stopped=self.stopped, router_calls=router._calls, logical=router._logical,
            retries=router._retries, failed=router._failed, attempts=router.attempts)
        if router._retry_request is not None:
            value['retry_issued_raw'] = self.contract_module.request_bytes(router._retry_request).decode('utf-8')
        return value

    def restore(self, value):
        self.calls, self.tokens = value['calls'], value['tokens']
        self.reserved_tokens, self.stopped = value['reserved_tokens'], value['stopped']
        router = self.router
        router._calls, router._logical = value['router_calls'], dict(value['logical'])
        router._retries, router._failed = value['retries'], value['failed']
        router.attempts = list(value['attempts'])
        router._retry_request = None
        if value.get('retry_issued_raw') is not None:
            from app.runtime.sol_session_receipts import request_from_raw
            router._retry_request = request_from_raw(value['retry_issued_raw'])
        if hasattr(router.generator, '_failed'):
            router.generator._failed = False
        # The derived trace starts its own new-IO ordinals at one. Only the
        # transport router keeps task-global ordinals across process restarts.
        if hasattr(router.generator, '_calls'):
            router.generator._calls = self.calls
        self.started = self.clock() - self.session.active_seconds

    def chat(self, request):
        contract = self.contract_module
        self._exchange = None
        # AgentLoop shortens its timeout on each run. Preserve every business
        # byte and retain the original actually issued timeout in the receipt.
        if not 0 < request.timeout_s <= contract.CONTRACT.descriptor()['execution_timeout_s']:
            raise SessionBlocked('session_request_timeout')
        normalized = json.loads(REQUEST.dump_json(replace(request, timeout_s=300.0)))

        def send():
            self.started = self.clock() - self.session.active_seconds
            try:
                response = super(SessionBudget, self).chat(request)
            except ProviderError as error:
                value = dict(ok=False, error_provider=error.provider, error_code=error.code,
                             budget=self.snapshot())
                issued = getattr(self, '_last_issued', None)
                if (contract.CONTRACT.descriptor().get('transport_retry_mode') == 'manual-reaped-timeout-v1'
                        and issued is not None and self.router._failed):
                    role = contract.role_for_request(issued)
                    selected = self.router.reviewer if role == 'review' else self.router.generator
                    if callable(getattr(selected, 'retryable', None)) and selected.retryable(error, issued):
                        value['reaped_timeout'] = dict(role=role, ordinal=self.calls,
                            issued_raw=contract.request_bytes(issued).decode('utf-8'),
                            receipt_sha256=selected.last_failure['receipt_sha256'])
                return value
            exchange = self.provider.last_exchange
            if not isinstance(exchange, Exchange) or exchange.response is not response:
                raise SessionBlocked('session_exchange_missing')
            return dict(ok=True, response_raw=RESPONSE.dump_json(response).decode('utf-8'),
                issued_raw=contract.request_bytes(exchange.issued_request).decode('utf-8'),
                receipt_request_sha256=exchange.receipt_request_sha256, budget=self.snapshot())

        while True:
            value, replayed = self.session.operation('model', normalized, send)
            if replayed:
                self.restore(value['budget'])
            if value.get('reaped_timeout') is None:
                break
            self._manual_retry(value)
        if not value['ok']:
            raise ProviderResponseError(provider=value['error_provider'], code=value['error_code'])
        response = RESPONSE.validate_json(value['response_raw'])
        issued = REQUEST.validate_json(value['issued_raw'])
        # Pydantic normalizes integer-valued floats; transport hashes bind the
        # original JSON numbers (300 versus 300.0), so retain their exact form.
        original = json.loads(value['issued_raw'])
        issued = replace(issued, **{k: original[k] for k in ('timeout_s', 'temperature', 'top_p')})
        if ((response.provider, response.model) != contract.request_identity(issued)
                or contract.request_sha(issued) != value['receipt_request_sha256']):
            raise SessionBlocked('session_response_identity')
        self._exchange = Exchange(issued, response, value['receipt_request_sha256'])
        return response

    def _manual_retry(self, failed):
        """Append one human-triggered decision, then replay the same logical call.

        The failure was classified while its original exception and immutable
        receipt were available. Session inventory pins those bytes throughout
        recovery. No missing/unknown receipt can acquire this classification.
        """
        session, router = self.session, self.router
        previous = session.root/'operations'/f'{session.cursor:04d}-result.json'
        bound = dict(failed_result_sha256=digest(previous.read_bytes()),
            timeout=failed['reaped_timeout'], budget=failed['budget'])
        next_path = session.root/'operations'/f'{session.cursor+1:04d}-intent.json'
        if not next_path.exists():
            if session.read_only or not session.manual_retry:
                raise SessionPaused('session_timeout_awaiting_manual_retry')
            limits = self.contract_module.CONTRACT.descriptor()
            from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
            from app.runtime.sol_session_receipts import request_from_raw
            request = request_from_raw(bound['timeout']['issued_raw'])
            reservation = estimate_runtime_request_input_ceiling(request) + request.max_tokens
            if (self.calls >= limits['max_calls'] or router._retries >= limits['transport_retries']
                    or self.tokens+self.reserved_tokens+reservation > limits['total_tokens']
                    or session.active_seconds >= limits['execution_timeout_s']):
                raise SessionPaused('session_retry_budget_extension_required')

        def approve():
            from app.runtime.sol_session_receipts import request_from_raw
            # Consume the manual flag once, even if this attempt times out too.
            session.manual_retry = False
            router._retry_request = request_from_raw(bound['timeout']['issued_raw'])
            router._retries += 1
            router._failed = self.stopped = False
            if hasattr(router.generator, '_failed'):
                router.generator._failed = False
            return dict(budget=self.snapshot(), automatic=False, same_stage=True)

        decision, replayed = session.operation('manual-retry', bound, approve)
        if replayed:
            self.restore(decision['budget'])


class SessionTools(ToolRuntime):
    def __init__(self, registry, *, session):
        super().__init__(registry)
        self.session = session

    def execute(self, tool_name, params, *, metadata=None, timeout_cap_s=None):
        if tool_name != 'knowledge.search':
            raise SessionBlocked('session_tool_not_read_only')
        request = dict(name=tool_name, params=dict(params), metadata=dict(metadata or {}))

        def search():
            result = super(SessionTools, self).execute(tool_name, params,
                metadata=metadata, timeout_cap_s=timeout_cap_s)
            return json.loads(TOOL_RESULT.dump_json(result))

        value, _ = self.session.operation('tool', request, search)
        return TOOL_RESULT.validate_json(json.dumps(value))


class SessionWorkflow(NaturalDutyWorkflow):
    def __init__(self, *args, session, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    def _review(self, inputs, name, stage):
        contract = self.contract_module
        raw, value = super()._review(inputs, name, stage)
        gate = self.session.review_gate
        if gate is not None:
            exchange = self.send.provider.last_exchange
            gate.require(name+'-'+stage, 'opinion', dict(
                complete_source=dict(data_json=inputs.data_json, pack_json=inputs.pack_json),
                report=inputs.source.report,
                request_raw=contract.request_bytes(exchange.issued_request).decode('utf-8'),
                responses=[raw], duty=name, stage=stage), inputs.source.report)
        return raw, value

    def record(self, name, data):
        contract = self.contract_module
        gate = self.session.review_gate
        if name == 'application' and gate is not None:
            gate.verify_prior()
        def save():
            self.journal_root.mkdir(parents=True, exist_ok=True)
            write_new_json(self.journal_root/(name+'.json'), data)
            return dict(recorded=True)
        self.session.operation('journal', dict(name=name, data=data), save)
        if name == 'preview' and gate is not None:
            opinions = [json.loads((self.journal_root/(duty+'-initial.json')).read_bytes())['raw']
                        for duty in ('facts', 'completion')]
            material = dict(complete_source=dict(data_json=self.original.data_json,
                pack_json=self.original.pack_json), original_report=self.original.source.report,
                report=data['report'], patch_journal=data['journal'], responses=opinions)
            requests = []
            for path in sorted((self.session.root/'operations').glob('*-result.json')):
                value = json.loads(path.read_bytes())['value']
                if not isinstance(value, dict) or not value.get('ok') or 'issued_raw' not in value:
                    continue
                issued = json.loads(value['issued_raw'])
                context = issued['metadata'].get(contract.CONTEXT)
                if context and context['stage'] == 'initial':
                    requests.append(value['issued_raw'])
            material['initial_requests_with_complete_policies'] = requests
            gate.require('compatibility', 'compatibility', material, data['report'])
            gate.require('edit', 'edit', material, data['report'])
