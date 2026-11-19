"""Explicit six-call candidate factory; no settings loading or execution entry."""
from app.evaluation.golden_stream_bridge import NATURAL_FLASH_TRANSPORT_ID, NATURAL_REVIEW_TRANSPORT_ID
from app.evaluation.natural_duty_contract import NaturalDutyProvider
from app.runtime.receipted_provider_factory import RoleReceiptedStreamProvider, RunScopedRoleReceiptedProviderFactory


class NaturalDutyProviderFactory(RunScopedRoleReceiptedProviderFactory):
    """Use one task ordinal and create-only receipt namespace for both models."""

    def _build(self, directory):
        generator = RoleReceiptedStreamProvider(settings=self._generator_settings,
            directory=directory / "generation", task_directory=directory,
            transport_id=NATURAL_FLASH_TRANSPORT_ID)
        reviewer = RoleReceiptedStreamProvider(settings=self._reviewer_settings,
            directory=directory / "review", task_directory=directory,
            transport_id=NATURAL_REVIEW_TRANSPORT_ID)
        return NaturalDutyProvider(generator, reviewer, source_projection=self._source_projection)
