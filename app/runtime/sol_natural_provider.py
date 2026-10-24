"""Run-scoped mixed transport with public receipts and bounded timeout recovery."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from app.evaluation import sol_natural_contract as contract
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_stream_bridge import NATURAL_FLASH_TRANSPORT_ID
from app.providers.models import ChatResponse, TokenUsage, ToolCall
from app.providers.errors import ProviderResponseError, ProviderTimeoutError
from app.providers.zhipu import ZhipuProvider
from app.runtime.reviewer_roles import RoleRoutedProvider
from app.runtime.receipted_provider_factory import RoleReceiptedStreamProvider
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.reviewer_responses_process import run_once, read_json, write_json, valid_saved_usage
from scripts.reviewer_responses_nonstream import build_wire
from scripts.reviewer_responses_transport import Profile, digest


def inventory(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def selected_contract(value=None):
    from app.evaluation import sol_necessity_contract, sol_completion_contract
    if value is None or value is contract:
        return contract
    if value in (sol_necessity_contract, sol_completion_contract):
        return value
    raise ValueError('sol_unsupported_contract')


class RecoverableFlashProvider(RoleReceiptedStreamProvider):
    """Reuse the existing supervisor; only its reaped deadline can recover."""

    last_failure = None

    def chat_at_ordinal(self, request, *, ordinal, role):
        self.last_failure = None
        try:
            return super().chat_at_ordinal(request, ordinal=ordinal, role=role)
        except ProviderTimeoutError as error:
            directory = self._directory / f'stream-{ordinal:03d}'
            terminal = read_json(directory / 'result.json') or {}
            reservation = read_json(directory / 'reservation.json') or {}
            pin = hashlib.sha256(contract.request_bytes(request, transport_id=self.transport_id)).hexdigest()
            # run_child writes deadline only after wait and pipe cleanup succeed.
            if (error.code == 'stream_deadline' and terminal.get('state') == 'deadline'
                    and terminal.get('transport_id') == self.transport_id
                    and reservation.get('request_sha256') == pin
                    and reservation.get('ordinal') == ordinal
                    and reservation.get('model') == self.model_name
                    and reservation.get('transport_id') == self.transport_id):
                self.last_failure = dict(error=error, request=request, directory=self._task_directory,
                    inventory=inventory(self._task_directory), receipt_sha256=hashlib.sha256(
                        (directory / 'result.json').read_bytes()).hexdigest())
            raise

    def retryable(self, error, request):
        failure = self.last_failure
        return bool(failure and failure['error'] is error and failure['request'] == request
                    and inventory(failure['directory']) == failure['inventory'])


class SolReviewProvider:
    provider_name, model_name = contract.REVIEW_PROVIDER, contract.REVIEW_MODEL
    thinking_profile_id, transport_id = 'sol-high-nonstream-v1', contract.REVIEW_TRANSPORT
    sdk_max_retries, runtime_profile = 0, None
    capabilities = ZhipuProvider.capabilities

    def __init__(self, *, api_key, directory, task_directory, sender=run_once, contract_module=None):
        self.contract_module = selected_contract(contract_module)
        self.transport_id = self.contract_module.REVIEW_TRANSPORT
        self.response_mode = getattr(self.contract_module, 'RESPONSE_MODE', 'natural-sol-v1')
        self._key, self.directory, self.task_directory = api_key, Path(directory), Path(task_directory)
        self.sender = sender
        self.profile = getattr(self.contract_module, 'REVIEW_PROFILE', Profile(group='GPT-pro', route='proxy-12000'))
        self.last_exchange = self.last_failure = None

    def chat_at_ordinal(self, request, *, ordinal, role):
        return self._consume(request, ordinal=ordinal, role=role, read_only=False)

    def read_completed_at_ordinal(self, request, *, ordinal, role):
        """Validate original completed evidence without creating or sending anything."""
        return self._consume(request, ordinal=ordinal, role=role, read_only=True)

    def _consume(self, request, *, ordinal, role, read_only):
        contract = self.contract_module
        self.last_exchange = self.last_failure = None
        raw = contract.request_bytes(request, transport_id=self.transport_id)
        if role != 'review' or type(ordinal) is not int or not 1 <= ordinal <= contract.CONTRACT.descriptor()['max_calls']:
            raise ValueError('sol_ordinal')
        if not read_only:
            self.task_directory.mkdir(parents=True, exist_ok=True)
            self.directory.mkdir(parents=True, exist_ok=True)
        directory = self.directory / f'call-{ordinal:03d}'
        pin = hashlib.sha256(raw).hexdigest()
        reservation = dict(ordinal=ordinal, role=role, provider=self.provider_name,
            model=self.model_name, request_sha256=pin, state='reserved_before_io')
        if read_only:
            if read_json(self.task_directory / f'call-{ordinal:03d}.json') != reservation:
                raise ValueError('sol_saved_reservation_binding')
        else:
            write_json(self.task_directory / f'call-{ordinal:03d}.json', reservation)
        business = visible(json_value(request))
        context = request.metadata[contract.CONTEXT]
        receipt = (read_json(directory / 'receipt.json') if read_only else
            self.sender(business, profile=self.profile, api_key=self._key, directory=directory,
                timeout_s=request.timeout_s, response_mode=self.response_mode, validation_context=context))
        if not receipt or read_only and receipt.get('ok') is not True:
            raise ValueError('sol_saved_complete_receipt_required')
        saved = read_json(directory / 'receipt.json')
        observation = read_json(directory / 'observation/observation.json')
        bound = (saved == receipt and receipt.get('request_sha256') == digest(business)
            and receipt.get('wire_sha256') == digest(build_wire(business))
            and receipt.get('validation_context_sha256') == digest(context)
            and receipt.get('profile') == asdict(self.profile)
            and receipt.get('response_mode') == self.response_mode
            and read_json(directory / 'request.json') == business
            and read_json(directory / 'validation-context.json') == context)
        if not bound:
            raise ProviderResponseError(provider=self.provider_name, code='sol_receipt_binding')
        if receipt.get('ok') is not True:
            error = ProviderResponseError(provider=self.provider_name, code='sol_call_failed')
            self.last_failure = dict(error=error, directory=directory, receipt_sha256=hashlib.sha256(
                (directory / 'receipt.json').read_bytes()).hexdigest(), request=request,
                inventory=inventory(self.task_directory))
            # Never manufacture a ChatResponse to settle a failed request.
            # Known failed usage is carried separately by the trusted adapter.
            usage = self.failure_usage(error, request)
            if usage is not None:
                error.observed_usage = TokenUsage(input_tokens=usage['input_tokens'],
                    output_tokens=usage['output_tokens'],
                    cached_input_tokens=usage['cached_input_tokens'] or 0)
                error.observed_usage_identity = (self.provider_name, self.model_name)
                error.observed_usage_conflict = False
            raise error
        worker = read_json(directory / 'worker-result.json')
        usage = receipt.get('usage')
        expected_profile = self.expected_profile(request)
        observed_contract = (observation or {}).get('response_contract')
        if (receipt.get('code') != 'ok' or receipt.get('reaped') is not True or receipt.get('worker_exit') != 0
                or receipt.get('usage_state') != 'known' or receipt.get('usage_conflict') is not False
                or not valid_saved_usage(usage) or receipt.get('http_requests') != 1
                or not 0 <= receipt.get('elapsed_s', -1) <= request.timeout_s
                or read_json(directory / 'profile.json') != expected_profile
                or read_json(directory / 'usage.json') != usage or not worker
                or worker.get('usage') != usage or worker.get('ok') is not True
                or worker.get('business_validated') is not True or worker.get('semantic_approval') is not False
                or not observation or observation.get('http_requests') != 1
                or observation.get('response_status') != 200 or observation.get('eof') is not True
                or observation.get('closed') is not True or observation.get('exception_type') is not None
                or not observed_contract or worker.get('response_observation') != observed_contract
                or observed_contract.get('terminal_status') != 'completed'
                or observed_contract.get('function_calls') != 1 or observed_contract.get('model_matches') is not True):
            raise ProviderResponseError(provider=self.provider_name, code='sol_incomplete_evidence')
        tool = worker['public_tool_call']
        contract.validate_business(business, context)(tool['arguments'])
        response = ChatResponse(provider=self.provider_name, model=self.model_name, content=None,
            tool_calls=(ToolCall(id=tool.get('call_id') or tool.get('id') or f'local-review-{ordinal}',
                name=tool['name'], arguments=json.loads(tool['arguments'])),), finish_reason='tool_calls',
            usage=TokenUsage(input_tokens=usage['input_tokens'], output_tokens=usage['output_tokens'],
                cached_input_tokens=usage['cached_input_tokens'] or 0))
        result = dict(state='complete',
            request_sha256=pin, receipt_sha256=hashlib.sha256((directory / 'receipt.json').read_bytes()).hexdigest(),
            input_tokens=usage['input_tokens'], output_tokens=usage['output_tokens'])
        result_path = self.task_directory / f'call-result-{ordinal:03d}.json'
        if read_only:
            if result_path.exists() and read_json(result_path) != result:
                raise ValueError('sol_saved_result_binding')
        else:
            write_json(result_path, result)
        self.last_exchange = Exchange(request, response, pin)
        return response

    def expected_profile(self, request):
        return dict(**asdict(self.profile), reasoning_effort='high', api='responses',
            max_output_tokens=16384, max_retries=0, timeout_s=request.timeout_s,
            group_verified=False, upstream_identity_verified=False, response_mode=self.response_mode)

    def failure_usage(self, error, request):
        failure = self.last_failure
        if (not failure or failure['error'] is not error or failure['request'] != request
                or inventory(self.task_directory) != failure['inventory']):
            return None
        directory = failure['directory']
        path = directory / 'receipt.json'
        if hashlib.sha256(path.read_bytes()).hexdigest() != failure['receipt_sha256']:
            return None
        receipt = read_json(path) or {}
        usage = receipt.get('usage')
        observation = read_json(directory / 'observation/observation.json') or {}
        response = observation.get('response_contract')
        # A receipt can retain usage from a rejected, different model. Only
        # matching response evidence can attribute those numbers to this route.
        # This remains a channel claim, never verified upstream identity.
        if (receipt.get('reaped') is not True or receipt.get('usage_state') != 'known'
                or receipt.get('usage_conflict') is not False or not valid_saved_usage(usage)
                or receipt.get('http_requests') != 1
                or read_json(directory / 'profile.json') != self.expected_profile(request)
                or observation.get('http_requests') != 1 or observation.get('response_status') != 200
                or observation.get('eof') is not True or not isinstance(response, dict)
                or response.get('response_received') is not True or response.get('model_matches') is not True):
            return None
        checkpoint_path, worker_path = directory / 'usage.json', directory / 'worker-result.json'
        checkpoint, worker = read_json(checkpoint_path), read_json(worker_path)
        if checkpoint_path.exists() and checkpoint != usage:
            return None
        if worker_path.exists() and (not worker or worker.get('usage') != usage
                or worker.get('usage_conflict') is not False
                or worker.get('response_observation') != response):
            return None
        if checkpoint is None and worker is None:
            return None
        return usage

    def retryable(self, error, request):
        failure = self.last_failure
        if not failure or failure['error'] is not error or failure['request'] != request:
            return False
        directory = failure['directory']
        actual = inventory(self.task_directory)
        if actual != failure['inventory']:
            return False
        if hashlib.sha256((directory / 'receipt.json').read_bytes()).hexdigest() != failure['receipt_sha256']:
            return False
        r = read_json(directory / 'receipt.json')
        obs = read_json(directory / 'observation/observation.json') or {}
        if (obs.get('schema_version') != 'stream-observation-v1' or obs.get('body_free') is not True
                or type(obs.get('http_requests')) is not int or obs['http_requests'] not in (0, 1)
                or obs.get('phase') not in ('before_request', 'awaiting_response_headers',
                    'response_headers_received', 'waiting_for_raw_bytes', 'sdk_consuming_bytes',
                    'response_headers_failed', 'read_failed', 'closed')
                or obs.get('exception_type') not in (None, 'connect_timeout', 'read_timeout')):
            return False
        if obs.get('response_status') == 200 and obs.get('eof') is True:
            # Parsing or close can hang after all HTTP bytes arrived, before
            # response_contract/worker-result is persisted. It is not an IO timeout.
            return False
        # The supervisor can reach its deadline after a worker has already
        # persisted a rejection (or a complete response). That timeout must
        # never hide a structural/identity failure and buy another response.
        timeout_codes = ('request_failed', 'http_status_408', 'http_status_504', 'http_status_524')
        if (r.get('worker_code') not in (None, *timeout_codes)
                or obs.get('response_contract') is not None
                or obs.get('response_status') not in (None, 200, 408, 504, 524)):
            return False
        if r.get('worker_code') == 'request_failed' and r.get('failure_category') not in (
                'connect_timeout', 'read_timeout'):
            return False
        # Only a reaped process and an explicit timeout, never a bad output,
        # auth error, missing observation, schema rejection or usage conflict.
        return (r.get('reaped') is True and r.get('usage_conflict') is False and r.get('ok') is False
            and (r.get('code') == 'deadline_exceeded' or
                 (r.get('code') == 'worker_rejected' and r.get('worker_exit') == 0
                  and r.get('worker_code') in timeout_codes
                  and (obs.get('response_status') in (408, 504, 524)
                       or r.get('failure_category') in ('connect_timeout', 'read_timeout')))))

    def recoverable_format(self, error, request):
        """A complete, identity-matched response may pause for format repair.

        This never approves the retained opinion or silently sends a retry.
        Multiple/unknown tools, business-invalid patches and identity failures
        are not classified as formatting. Original usage and receipts survive.
        """
        if (self.contract_module.CONTRACT.descriptor().get('output_recovery_mode')
                != 'manual-reaped-format-v1' or self.response_mode not in (
                    'natural-sol-necessity-v2', 'natural-sol-completion-necessity-v1')
                or self.failure_usage(error, request) is None):
            return False
        failure = self.last_failure
        directory = failure['directory']
        receipt = read_json(directory / 'receipt.json') or {}
        worker = read_json(directory / 'worker-result.json') or {}
        observation = read_json(directory / 'observation/observation.json') or {}
        response = observation.get('response_contract') or {}
        counts = response.get('output_type_counts') or {}
        code = worker.get('code')
        return bool(receipt.get('code') == 'worker_rejected' and receipt.get('worker_exit') == 0
            and receipt.get('worker_code') == code and worker.get('ok') is False
            and worker.get('business_validated') is False
            and worker.get('public_tool_call') is None
            and observation.get('closed') is True and observation.get('exception_type') is None
            and response.get('terminal_status') == 'completed'
            and response.get('reasoning_echo') not in ('conflict', 'malformed')
            and (response.get('decode') or {}).get('identity_fields_equal') is True
            and counts.get('other') == 0
            and ((code == 'single_tool_required' and counts.get('function_call') == 0)
                 or (code == 'tool_schema_invalid' and counts.get('function_call') == 1)))


class SolNaturalProvider(RoleRoutedProvider):
    provider_name, model_name, thinking_profile_id = contract.PROVIDER, contract.MODEL, contract.PROFILE
    role_for_request = staticmethod(contract.role_for_request)
    request_identity = staticmethod(contract.request_identity)
    validate_request = staticmethod(contract.request_bytes)

    def __init__(self, generator, reviewer, *, contract_module=None):
        contract = self.contract_module = selected_contract(contract_module)
        if reviewer.contract_module is not contract:
            raise ValueError('sol_reviewer_contract_binding')
        self.role_for_request = contract.role_for_request
        self.request_identity = contract.request_identity
        self.validate_request = contract.request_bytes
        from app.evaluation.golden_coarse_source_projection import VERSION
        self.source_projection = VERSION
        self.require_selected_provider(generator, 'generation')
        self.require_selected_provider(reviewer, 'review')
        self.generator, self.reviewer = generator, reviewer
        self.capabilities = generator.capabilities
        if generator is reviewer or generator.capabilities != reviewer.capabilities:
            raise ValueError('sol_capabilities')
        self.last_exchange, self.attempts = None, []
        self._calls, self._failed, self._retries = 0, False, 0
        self._logical = {'generation': 0, 'review': 0}
        if contract.CONTRACT.descriptor().get('control_logical_calls'):
            self._logical['control'] = 0
        self._retry_request = None

    def require_selected_provider(self, provider, role):
        contract = self.contract_module
        if role == 'generation':
            contract.legacy.NaturalDutyProvider.require_selected_provider(self, provider, role)
        elif ((provider.provider_name, provider.model_name, provider.thinking_profile_id, provider.sdk_max_retries,
               provider.runtime_profile, provider.transport_id) != (contract.REVIEW_PROVIDER, contract.REVIEW_MODEL,
               'sol-high-nonstream-v1', 0, None, contract.REVIEW_TRANSPORT)):
            raise ValueError('sol_child_identity')

    def transport_for_role(self, role):
        contract = self.contract_module
        return NATURAL_FLASH_TRANSPORT_ID if role == 'generation' else contract.REVIEW_TRANSPORT

    def chat(self, request):
        role = self.role_for_request(request)
        context = request.metadata.get(self.contract_module.CONTEXT, {})
        logical_role = 'control' if context.get('control_case') is not None else role
        limit = (self.contract_module.CONTRACT.descriptor().get('control_logical_calls', 0)
                 if logical_role == 'control' else 2 if role == 'generation' else 4)
        if self._retry_request is None:
            self._logical[logical_role] += 1
        else:
            # The shared budget may shorten timeout, but no business byte changes.
            from dataclasses import replace
            if replace(request, timeout_s=self._retry_request.timeout_s) != self._retry_request:
                raise ValueError('sol_retry_request_changed')
            self._retry_request = None
        if self._logical[logical_role] > limit:
            raise ProviderResponseError(provider=self.provider_name, code='sol_logical_call_limit')
        return super().chat(request)

    def prepare_retry(self, error, request):
        contract = self.contract_module
        # The necessity candidate pauses in its durable session. Never turn a
        # manual retry allowance into an automatic second provider request.
        if contract.CONTRACT.descriptor().get('transport_retry_mode') == 'manual-reaped-timeout-v1':
            return False
        if (self._retries >= contract.CONTRACT.descriptor()['transport_retries'] or not self._failed
                or (self.reviewer.task_directory/'retry-decision.json').exists()):
            return False
        role = self.role_for_request(request)
        selected = self.reviewer if role == 'review' else self.generator
        if (role == 'generation' and type(selected) is not RecoverableFlashProvider
                or not selected.retryable(error, request)):
            return False
        write_json(self.reviewer.task_directory / 'retry-decision.json', dict(
            reason='verified_transport_timeout', previous_ordinal=self._calls,
            role=role, prior_receipt_sha256=selected.last_failure['receipt_sha256'],
            same_stage=True, max_retries=contract.CONTRACT.descriptor()['transport_retries'], previous_unknown_reservation_retained=True))
        self._retries += 1
        self._failed = False
        if role == 'generation':
            selected._failed = False
        self._retry_request = request
        return True

    def failure_usage(self, error, request):
        usage = self.reviewer.failure_usage(error, request)
        return usage['total_tokens'] if usage is not None else None


class SolNaturalProviderFactory:
    def __init__(self, *, generator_settings, api_key, transport_root, contract_module=None):
        self.contract_module = selected_contract(contract_module)
        self.settings, self._key, self.root = generator_settings, api_key, Path(transport_root)
        self.descriptor = self._build(self.root / '_identity_only')

    def _build(self, folder):
        return SolNaturalProvider(RecoverableFlashProvider(settings=self.settings,
            directory=folder / 'generation', task_directory=folder, transport_id=NATURAL_FLASH_TRANSPORT_ID),
            SolReviewProvider(api_key=self._key, directory=folder / 'review', task_directory=folder,
                contract_module=self.contract_module), contract_module=self.contract_module)

    def __call__(self, run_id):
        from app.harness.run_ids import normalize_run_id
        return self._build(self.root / normalize_run_id(run_id))
