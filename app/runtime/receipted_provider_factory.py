"""One stream counter, failure flag and receipt directory per trusted run."""
from pathlib import Path

from app.evaluation.golden_integrated_runtime import ReceiptedStreamProvider
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, RESPONSE, validate_request
from app.harness.run_ids import normalize_run_id


class JournaledReceiptedProvider(ReceiptedStreamProvider):
    def chat(self, request):
        self.last_exchange = None
        raw = validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)
        ordinal = self._calls + 1
        self._directory.mkdir(parents=True, exist_ok=True)
        with (self._directory / f'request-{ordinal:03d}.json').open('xb') as stream:
            stream.write(raw)
        response = super().chat(request)
        with (self._directory / f'response-{ordinal:03d}.json').open('xb') as stream:
            stream.write(RESPONSE.dump_json(response))
        return response


class RunScopedReceiptedProviderFactory:
    def __init__(self, *, settings, transport_root):
        self._settings = settings
        self._root = Path(transport_root).resolve()
        # Identity/capability validation only: no directory or request is made.
        self.descriptor = JournaledReceiptedProvider(settings=settings,
            directory=self._root / '_identity_only', transport_id=CAPACITY_TRANSPORT_ID)

    def __call__(self, run_id):
        run_id = normalize_run_id(run_id)
        return JournaledReceiptedProvider(settings=self._settings,
            directory=self._root / run_id, transport_id=CAPACITY_TRANSPORT_ID)

class RoleReceiptedStreamProvider(ReceiptedStreamProvider):
    """One concrete model transport addressed by the router's task ordinal.

    The router owns role selection, task budget and the ordinal. This adapter
    never dispatches or retries. Both role adapters reserve the same task-level
    call namespace and keep their unchanged process receipts in distinct paths.
    """

    def __init__(self, *, settings, directory, task_directory, transport_id):
        from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID

        if transport_id not in (CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID):
            raise ValueError("role_transport_identity")
        super().__init__(settings=settings, directory=directory, transport_id=transport_id)
        self._task_directory = Path(task_directory)
        self._identity = (self.provider_name, self.model_name, self.thinking_profile_id,
                          self.transport_id, self.sdk_max_retries)
        self.last_exchange = None
        self.last_response = None

    def _require_identity(self):
        from app.providers.errors import ProviderResponseError

        current = (self.provider_name, self.model_name, self.thinking_profile_id,
                   self.transport_id, self.sdk_max_retries)
        if (current != self._identity or type(self.sdk_max_retries) is not int
                or self.runtime_profile is not None
                or self._settings.model != self.model_name
                or self._settings.base_url.rstrip("/") != "https://open.bigmodel.cn/api/paas/v4"):
            raise ProviderResponseError(provider="zhipu", code="role_transport_identity_mismatch")

    def chat(self, request):
        # A direct chat would silently restart a model-local ordinal.
        from app.providers.errors import ProviderResponseError

        raise ProviderResponseError(provider="zhipu", code="role_transport_ordinal_required")

    def chat_at_ordinal(self, request, *, ordinal, role=None):
        import hashlib

        from app.evaluation.golden_inference_scope_v5 import strict_json
        from app.evaluation.golden_integrated_runtime import Exchange
        from app.evaluation.golden_journal import write_new_json
        from app.evaluation.golden_stream_bridge import GoldenProcessStreamProvider, REVIEW_MODEL_TRANSPORT_ID
        from app.providers.errors import ProviderError, ProviderResponseError
        from app.providers.models import ChatResponse

        self.last_exchange = None
        self.last_response = None
        try:
            self._require_identity()
            expected_roles = ("review",) if self.transport_id == REVIEW_MODEL_TRANSPORT_ID else ("generation", "revision")
            role = expected_roles[0] if role is None else role
            if role not in expected_roles:
                raise ProviderResponseError(provider="zhipu", code="role_transport_identity_mismatch")
            if self._failed:
                raise ProviderResponseError(provider="zhipu", code="stream_bridge_exhausted")
            if type(ordinal) is not int or not self._calls < ordinal <= 9:
                raise ProviderResponseError(provider="zhipu", code="role_transport_ordinal_invalid")
            raw = validate_request(request, transport_id=self.transport_id)
            request_sha256 = hashlib.sha256(raw).hexdigest()
            self._task_directory.mkdir(parents=True, exist_ok=True)
            self._directory.mkdir(parents=True, exist_ok=True)
            # Create-only and shared by both models: a duplicate task/ordinal
            # cannot spend even when its other role's raw directory is empty.
            binding = dict(ordinal=ordinal, role=role, provider=self.provider_name,
                model=self.model_name, thinking_profile_id=self.thinking_profile_id,
                transport_id=self.transport_id, request_sha256=request_sha256,
                raw_directory=self._directory.relative_to(self._task_directory).as_posix(),
                state="reserved_before_io")
            write_new_json(self._task_directory / f"call-{ordinal:03d}.json", binding)
            with (self._directory / f"request-{ordinal:03d}.json").open("xb") as stream:
                stream.write(raw)
            # GoldenProcessStreamProvider already owns subprocess lifetime,
            # timeout, model checks and raw transport reservation. Seed only its
            # next ordinal; do not create another transport implementation.
            self._calls = ordinal - 1
            response = GoldenProcessStreamProvider.chat(self, request)
            if not isinstance(response, ChatResponse):
                raise ProviderResponseError(provider="zhipu", code="invalid_chat_response")
            self.last_response = response
            response_raw = RESPONSE.dump_json(response)
            with (self._directory / f"response-{ordinal:03d}.json").open("xb") as stream:
                stream.write(response_raw)
            self._require_identity()
            if (response.provider, response.model) != self._identity[:2]:
                raise ProviderResponseError(provider="zhipu", code="response_identity_mismatch")
            directory = self._directory / f"stream-{ordinal:03d}"
            try:
                reservation = strict_json((directory / "reservation.json").read_text(encoding="utf-8"))
                terminal = strict_json((directory / "result.json").read_text(encoding="utf-8"))
                actual_request_sha256 = hashlib.sha256(
                    validate_request(request, transport_id=self.transport_id)).hexdigest()
                model_identity_valid = (
                    reservation.get("model") == self.model_name
                    and reservation.get("thinking_profile_id") == self.thinking_profile_id
                ) if self.transport_id == REVIEW_MODEL_TRANSPORT_ID else (
                    reservation.get("model", self.model_name) == self.model_name
                    and reservation.get("thinking_profile_id", self.thinking_profile_id) == self.thinking_profile_id
                )
                valid = (model_identity_valid and self._calls == ordinal
                    and reservation["transport_id"] == self.transport_id
                    and type(reservation["ordinal"]) is int
                    and reservation["ordinal"] == ordinal
                    and reservation["request_sha256"] == request_sha256 == actual_request_sha256
                    and reservation["stream_tool_arguments"] == (self.stream_tool_arguments and bool(request.tools))
                    and terminal["state"] == "complete"
                    and terminal["transport_id"] == self.transport_id)
            except (KeyError, TypeError, ValueError, OSError):
                valid = False
            if not valid:
                raise ProviderResponseError(provider="zhipu", code="integrated_transport_receipt_invalid")
            write_new_json(self._task_directory / f"call-result-{ordinal:03d}.json", {
                **binding, "state": "complete", "response_sha256": hashlib.sha256(response_raw).hexdigest(),
                "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens,
            })
            self.last_exchange = Exchange(request, response, request_sha256)
            return response
        except BaseException as error:
            self._failed = True
            self.last_exchange = None
            # A complete response may precede a failed file write. Normalize
            # ordinary recording errors at this trusted boundary so observation
            # and budget use the same identity-checked response. Preserve the
            # cause privately; no failed receipt becomes an accepted Exchange.
            if isinstance(error, Exception) and self.last_response is not None:
                failure = error if isinstance(error, ProviderError) else ProviderResponseError(
                    provider=self._identity[0], code="role_response_recording_failed")
                failure.observed_response = self.last_response
                failure.observed_usage = self.last_response.usage
                if failure is not error:
                    raise failure from error
            raise


class RunScopedRoleReceiptedProviderFactory:
    """Build the adopted router with two isolated, globally addressed streams."""

    def __init__(self, *, generator_settings, reviewer_settings, transport_root, source_projection=None):
        from app.evaluation.golden_explicit_source_projection import VERSION
        self._source_projection = VERSION if source_projection is None else source_projection
        self._generator_settings = generator_settings
        self._reviewer_settings = reviewer_settings
        self._root = Path(transport_root).resolve()
        # Construct identities without creating files or sending a request.
        self.descriptor = self._build(self._root / "_identity_only")

    def _build(self, directory):
        from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID
        from app.runtime.reviewer_roles import RoleRoutedProvider

        generator = RoleReceiptedStreamProvider(settings=self._generator_settings,
            directory=directory / "generation", task_directory=directory,
            transport_id=CAPACITY_TRANSPORT_ID)
        reviewer = RoleReceiptedStreamProvider(settings=self._reviewer_settings,
            directory=directory / "review", task_directory=directory,
            transport_id=REVIEW_MODEL_TRANSPORT_ID)
        return RoleRoutedProvider(generator, reviewer, source_projection=self._source_projection)

    def __call__(self, run_id):
        return self._build(self._root / normalize_run_id(run_id))
