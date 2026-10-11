"""Explicit factory selection, never a default model/profile resolver."""
from app.runtime.receipted_provider_factory import RunScopedRoleReceiptedProviderFactory
from app.runtime.document_review_roles import DocumentRoleRoutedProvider


class DocumentRoleProviderFactory(RunScopedRoleReceiptedProviderFactory):
    router_type = DocumentRoleRoutedProvider

    def __init__(self, *, source_projection=None, **kwargs):
        from app.evaluation.golden_coarse_source_projection import VERSION
        if source_projection not in (None, VERSION):
            raise ValueError('document_factory_projection_required')
        super().__init__(source_projection=VERSION, **kwargs)
