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
from app.evaluation.sol_natural_session import SessionBlocked
from app.providers.errors import ProviderError, ProviderResponseError
from app.runtime.coach_budget import CoachBudgetedProvider
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.sol_natural_provider import SolNaturalProvider
from app.tools.models import ToolResult
from app.tools.runtime import ToolRuntime

TOOL_RESULT = TypeAdapter(ToolResult)


class SessionBudget(CoachBudgetedProvider):
    def __init__(self, provider, *, session, coach_contract):
        if coach_contract is not contract.CONTRACT or not isinstance(provider, ObservedLLMProvider):
            raise ValueError('session_budget_requires_observed_sol')
        if type(provider._delegate) is not SolNaturalProvider:
            raise ValueError('session_router_type')
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
            contract.request_bytes(request).decode('utf-8'), self.snapshot(),
            retry_pending=self.router._retry_request is not None)
        return super()._provider_for_request(request)

    def snapshot(self):
        router = self.router
        return dict(calls=self.calls, tokens=self.tokens, reserved_tokens=self.reserved_tokens,
            stopped=self.stopped, router_calls=router._calls, logical=router._logical,
            retries=router._retries, failed=router._failed, attempts=router.attempts)

    def restore(self, value):
        self.calls, self.tokens = value['calls'], value['tokens']
        self.reserved_tokens, self.stopped = value['reserved_tokens'], value['stopped']
        router = self.router
        router._calls, router._logical = value['router_calls'], dict(value['logical'])
        router._retries, router._failed = value['retries'], value['failed']
        router.attempts = list(value['attempts'])
        router._retry_request = None
        # The derived trace starts its own new-IO ordinals at one. Only the
        # transport router keeps task-global ordinals across process restarts.
        if hasattr(router.generator, '_calls'):
            router.generator._calls = self.calls
        self.started = self.clock() - self.session.active_seconds

    def chat(self, request):
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
                return dict(ok=False, error_provider=error.provider, error_code=error.code,
                            budget=self.snapshot())
            exchange = self.provider.last_exchange
            if not isinstance(exchange, Exchange) or exchange.response is not response:
                raise SessionBlocked('session_exchange_missing')
            return dict(ok=True, response_raw=RESPONSE.dump_json(response).decode('utf-8'),
                issued_raw=contract.request_bytes(exchange.issued_request).decode('utf-8'),
                receipt_request_sha256=exchange.receipt_request_sha256, budget=self.snapshot())

        value, replayed = self.session.operation('model', normalized, send)
        if replayed:
            self.restore(value['budget'])
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
