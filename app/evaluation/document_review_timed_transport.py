"""Explicit opt-in time600 pair; reuse role dispatch and process receipts."""
from app.evaluation import document_review_timing_adapter as timing
from app.evaluation import golden_stream_bridge as bridge
from app.runtime.reviewer_roles import RoleRoutedProvider, profile_for_role
from app.runtime.receipted_provider_factory import RoleReceiptedStreamProvider, RunScopedRoleReceiptedProviderFactory
from app.providers.errors import ProviderResponseError
from scripts.report_document_view import VERSION as PRESENTATION


class TimedDocumentRouter(RoleRoutedProvider):
    request_timing_identity = timing.TIMED_IDENTITY
    report_presentation = PRESENTATION
    role_for_request = staticmethod(timing.role_for_request)
    request_identity = staticmethod(timing.request_identity)

    @staticmethod
    def transport_for_role(role):
        timing.allowed_timeout(role)
        return bridge.TIMED_REVIEW_TRANSPORT_ID if role == "review" else bridge.TIMED_FLASH_TRANSPORT_ID

    def require_selected_provider(self, provider, role):
        profile = profile_for_role(role)
        if (provider.provider_name != "zhipu" or provider.model_name != profile.model
                or provider.thinking_profile_id != profile.profile_id
                or type(provider.sdk_max_retries) is not int or provider.sdk_max_retries != 0
                or provider.runtime_profile is not None
                or provider.transport_id != self.transport_for_role(role)):
            raise ProviderResponseError(provider="zhipu", code="role_provider_identity_mismatch")

    def __init__(self, generator, reviewer, *, source_projection):
        from app.evaluation.golden_coarse_source_projection import VERSION
        if source_projection != VERSION or generator is reviewer or generator.capabilities != reviewer.capabilities:
            raise ValueError("timed_role_composition")
        self.require_selected_provider(generator, "generation")
        self.require_selected_provider(reviewer, "review")
        self.source_projection = source_projection
        self.generator, self.reviewer = generator, reviewer
        self.capabilities = generator.capabilities
        self.last_exchange = None
        self.attempts = []
        self._calls = 0
        self._failed = False


class TimedDocumentProviderFactory(RunScopedRoleReceiptedProviderFactory):
    def __init__(self, *, generator_settings, reviewer_settings, transport_root, source_projection=None):
        from app.evaluation.golden_coarse_source_projection import VERSION
        super().__init__(generator_settings=generator_settings, reviewer_settings=reviewer_settings,
            transport_root=transport_root, source_projection=VERSION if source_projection is None else source_projection)

    def _build(self, directory):
        generator = RoleReceiptedStreamProvider(settings=self._generator_settings,
            directory=directory / "generation", task_directory=directory,
            transport_id=bridge.TIMED_FLASH_TRANSPORT_ID)
        reviewer = RoleReceiptedStreamProvider(settings=self._reviewer_settings,
            directory=directory / "review", task_directory=directory,
            transport_id=bridge.TIMED_REVIEW_TRANSPORT_ID)
        return TimedDocumentRouter(generator, reviewer, source_projection=self._source_projection)
