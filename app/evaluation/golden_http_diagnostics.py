"""Body-free, bounded HTTP phase observations for the golden candidate only."""

import time

from app.evaluation.golden_journal import write_new_json


_PHASES = {
    "connection.connect_tcp", "connection.start_tls",
    "http11.send_request_headers", "http11.send_request_body",
    "http11.receive_response_headers", "http11.receive_response_body",
    "http11.response_closed",
    "http2.send_request_headers", "http2.send_request_body",
    "http2.receive_response_headers", "http2.receive_response_body",
    "http2.response_closed",
    "proxy.start_tls",
}
_EVENTS = frozenset(f"{phase}.{state}" for phase in _PHASES
                    for state in ("started", "complete", "failed"))


class GoldenHttpDiagnostics:
    """One synchronous Provider attempt at a time; never inspect trace info.

    An HTTP phase is a client observation, not an upstream causal diagnosis.
    Missing events remain unknown (including connections reused from a pool).
    """

    def __init__(self, journal, *, clock=time.monotonic):
        self.journal = journal
        self.clock = clock
        self.active = None

    def begin(self, ordinal):
        if self.active is not None:
            raise ValueError("golden_http_attempt_already_active")
        self.active = {"ordinal": ordinal, "started": self.clock(),
                       "http_requests": 0, "events": [], "dropped_events": 0}

    def on_request(self, request):
        if self.active is None:
            raise ValueError("golden_http_attempt_not_reserved")
        self.active["http_requests"] += 1
        request.extensions["trace"] = self.on_trace

    def on_trace(self, name, info):
        # info can contain credentials, request/response bodies and exceptions.
        # Do not serialize it, stringify it, or derive fields from it.
        if self.active is None or name not in _EVENTS:
            return
        if len(self.active["events"]) >= 64:
            self.active["dropped_events"] += 1
            return
        self.active["events"].append({"event": name, "elapsed_ms": self._elapsed()})

    def _elapsed(self):
        return max(0, round((self.clock() - self.active["started"]) * 1000))

    def finish(self, outcome):
        if outcome not in {"response", "failed", "interrupted"}:
            raise ValueError("golden_http_outcome_invalid")
        row = {"schema_version": "1.0", "body_free": True,
               "provider_ordinal": self.active["ordinal"],
               "outcome": outcome, "elapsed_ms": self._elapsed(),
               "http_requests": self.active["http_requests"],
               "events": self.active["events"],
               "dropped_events": self.active["dropped_events"]}
        self.active = None
        write_new_json(self.journal.directory / f"http-{row['provider_ordinal']:03d}.json", row)
