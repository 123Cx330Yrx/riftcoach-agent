"""Create-only golden run reservation and durable pre-I/O attempt counters."""
import json
import os
from pathlib import Path


def write_new_json(path: Path, value):
    data = (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


class GoldenCallJournal:
    def __init__(self, directory: Path, *, identity, limits):
        directory.mkdir(parents=True, exist_ok=False)
        self.directory = directory
        self.limits = dict(limits)
        self.counts = {key: 0 for key in limits}
        write_new_json(directory / "reservation.json", {"identity": identity, "limits": self.limits})

    def reserve(self, source):
        if source not in self.limits or self.counts[source] >= self.limits[source]:
            raise ValueError("golden_source_budget_exceeded")
        ordinal = self.counts[source] + 1
        write_new_json(self.directory / f"{source}-{ordinal:03d}.json", {
            "source": source, "ordinal": ordinal, "state": "attempt_reserved_before_io",
        })
        self.counts[source] = ordinal

    def finish(self, state):
        if state not in ("degraded", "failed", "interrupted"):
            raise ValueError("golden_terminal_state_invalid")
        write_new_json(self.directory / "terminal.json", {"state": state, "attempt_counts": self.counts})


class JournaledProvider:
    def __init__(self, delegate, journal):
        self.delegate, self.journal = delegate, journal

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def chat(self, request):
        self.journal.reserve("provider")
        return self.delegate.chat(request)
