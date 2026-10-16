"""Explicit task-control adapter for frozen opt-in Coach compositions.

The ordinary RuntimeCompositionRoot already constructs DispatchAwareRuntime.
Historical native builders remain byte-for-byte bound to their manifests. A
caller adopting this runtime-only change wraps the built service here before
using it. This is not candidate admission or a change to model/quality policy.
"""
from app.runtime.dispatch_runtime import DispatchAwareRuntime
from .recent_review_service import RecentReviewApplicationService


def with_dispatch_trace(application: RecentReviewApplicationService) -> RecentReviewApplicationService:
    """Construct a new service with the same dependencies and dispatch adapter.

    Use the returned service. Neither the supplied service nor its Runtime is
    patched, and arbitrary service/runtime subclasses are deliberately refused.
    """
    if type(application) is not RecentReviewApplicationService:
        raise TypeError("dispatch adapter requires the exact recent-review service")
    return RecentReviewApplicationService(
        summary_builder=application._summary_builder,
        compiler=application._compiler,
        runtime=DispatchAwareRuntime.from_core(application._runtime),
        receipt_writer=application._receipt_writer,
        report_renderer=application._report_renderer,
        publication_sources=application._publication_sources,
        publication_writer=application._publication_writer,
        publication_report_renderer=application._publication_report_renderer,
        allow_legacy_without_publication=application._allow_legacy_without_publication,
    )
