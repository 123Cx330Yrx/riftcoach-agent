"""Product-facing contracts and trusted request compilers."""

from .recent_review import (
    ConversationRecentReviewRequest,
    ProductRequestCompilationError,
    RecentReviewProductRequest,
    RecentReviewRuntimeRequestCompiler,
)
from .recent_review_service import (
    RecentReviewApplicationError,
    RecentReviewApplicationResult,
    RecentReviewApplicationService,
    RecentReviewRuntime,
    RecentReviewSummaryBuilder,
)
from .run_query import (
    RecentAveragesView,
    RecentComparisonRowView,
    RecentSummaryView,
    RecentWinLossComparisonView,
    RunQueryError,
    RunQueryService,
    RunView,
    SingleMatchReviewView,
)
from .run_receipts import (
    ApiRunReceipt,
    FileRunReceiptStore,
    RunReceiptReference,
    RunReceiptWriter,
)

__all__ = [
    "ProductRequestCompilationError",
    "ConversationRecentReviewRequest",
    "ApiRunReceipt",
    "FileRunReceiptStore",
    "LatestProfileReview",
    "LatestProfileReviewRepositoryError",
    "LatestProfileReviewRepositoryPort",
    "LatestProfileReviewResult",
    "LatestProfileReviewService",
    "LatestProfileReviewServiceError",
    "RecentReviewApplicationError",
    "RecentReviewApplicationResult",
    "RecentReviewApplicationService",
    "RecentReviewProductRequest",
    "RecentReviewRuntime",
    "RecentReviewRuntimeRequestCompiler",
    "RecentReviewSummaryBuilder",
    "RecentAveragesView",
    "RecentComparisonRowView",
    "RecentSummaryView",
    "RecentWinLossComparisonView",
    "RunQueryError",
    "RunQueryService",
    "RunReceiptReference",
    "RunReceiptWriter",
    "RunView",
    "SingleMatchReviewView",
]


_LAZY_LATEST_REVIEW_EXPORTS = frozenset(
    {
        "LatestProfileReview",
        "LatestProfileReviewRepositoryError",
        "LatestProfileReviewRepositoryPort",
        "LatestProfileReviewResult",
        "LatestProfileReviewService",
        "LatestProfileReviewServiceError",
    }
)


def __getattr__(name: str):
    # ``app.tasks.models`` imports ``app.product.recent_review``.  Keeping the
    # locator export lazy avoids making that established import path depend on
    # the task enums before their module has finished initializing.
    if name in _LAZY_LATEST_REVIEW_EXPORTS:
        from . import latest_review

        return getattr(latest_review, name)
    raise AttributeError(name)
