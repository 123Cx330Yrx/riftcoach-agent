"""Use the Runtime's existing budget and transport receipt for native review."""
from app.evaluation.golden_integrated_runtime import Exchange
from app.runtime.coach_budget import CoachBudgetedProvider


class SharedBudgetReviewSender:
    def __init__(self, provider: CoachBudgetedProvider):
        if not isinstance(provider, CoachBudgetedProvider):
            raise TypeError("review requires the Runtime's budgeted provider")
        self.provider = provider

    def __call__(self, request):
        previous = getattr(self.provider, "last_exchange", None)
        response = self.provider.chat(request)
        exchange = getattr(self.provider, "last_exchange", None)
        if not isinstance(exchange, Exchange) or exchange is previous or exchange.response is not response:
            raise ValueError("integrated_fresh_transport_receipt_required")
        return exchange
