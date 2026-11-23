def _manual_retry(self, failed, *, format_repair=False):
    """Append one human-triggered decision, then replay the same logical call.

    The failure was classified while its original exception and immutable
    receipt were available. Session inventory pins those bytes throughout
    recovery. No missing/unknown receipt can acquire this classification.
    """
    session, router = self.session, self.router
    previous = session.root/'operations'/f'{session.cursor:04d}-result.json'
    failure_key = 'recoverable_format' if format_repair else 'reaped_timeout'
    bound = dict(failed_result_sha256=digest(previous.read_bytes()),
        **{'format' if format_repair else 'timeout': failed[failure_key]}, budget=failed['budget'])
    attempt = failed[failure_key]
    next_path = session.root/'operations'/f'{session.cursor+1:04d}-intent.json'
    if not next_path.exists():
        if session.read_only or not session.manual_retry:
            raise SessionPaused('session_format_awaiting_manual_retry' if format_repair
                                else 'session_timeout_awaiting_manual_retry')
        limits = self.contract_module.CONTRACT.descriptor()
        from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
        from app.runtime.sol_session_receipts import request_from_raw
        request = request_from_raw(attempt['issued_raw'])
        reservation = estimate_runtime_request_input_ceiling(request) + request.max_tokens
        if (self.calls >= limits['max_calls'] or router._retries >= limits['transport_retries']
                or self.tokens+self.reserved_tokens+reservation > limits['total_tokens']
                or session.active_seconds >= limits['execution_timeout_s']):
            raise SessionPaused('session_retry_budget_extension_required')

    def approve():
        from app.runtime.sol_session_receipts import request_from_raw
        # Consume the manual flag once, even if this attempt times out too.
        session.manual_retry = False
        router._retry_request = request_from_raw(attempt['issued_raw'])
        router._retries += 1
        router._failed = self.stopped = False
        if hasattr(router.generator, '_failed'):
            router.generator._failed = False
        return dict(budget=self.snapshot(), automatic=False, same_stage=True)

    decision, replayed = session.operation('manual-retry', bound, approve)
    if replayed:
        self.restore(decision['budget'])
