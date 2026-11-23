"""Browser decoding must cover the event kinds the actual SQL Worker emits."""
from pathlib import Path
import re

from app.tasks.reliable_runtime import TaskLifecycleEventKind


def test_browser_event_kinds_match_backend_contract():
    wire = (Path(__file__).resolve().parents[1] / "web/src/api/wire.ts").read_text(encoding="utf-8")
    declaration = re.search(r"export const TASK_EVENT_KINDS = \[(.*?)\] as const", wire, re.S)
    assert declaration is not None
    values = re.findall(r'"([a-z_]+)"', declaration.group(1))
    assert len(values) == len(set(values))
    assert set(values) == {kind.value for kind in TaskLifecycleEventKind}
