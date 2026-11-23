"""Read cumulative usage from the original pinned session operations."""
import json
from app.tasks.continuation import SessionAccounting


def session_accounting(session):
    """Read pinned original budget facts; reservations are not claimed HTTPs."""
    budget = dict(calls=0, tokens=0, reserved_tokens=0, retries=0, attempts=[])
    pending = 0
    not_sent = set()
    for intent in sorted((session.root / "operations").glob("*-intent.json")):
        result = intent.with_name(intent.name.replace("-intent", "-result"))
        if not result.exists():
            pending += 1
            continue
        value = json.loads(result.read_bytes())["value"]
        if isinstance(value, dict) and "budget" in value:
            budget = value["budget"]
            if value.get("not_sent_ordinal") is not None:
                not_sent.add(value["not_sent_ordinal"])
    calls, unknown = budget["calls"], budget["reserved_tokens"]
    attempts = sorted((session.root / "operations").glob("attempt-*.json"))
    if attempts:
        last = json.loads(attempts[-1].read_bytes())
        if last["ordinal"] > calls and last["ordinal"] not in not_sent:
            from app.runtime.sol_session_receipts import request_from_raw
            from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
            request = request_from_raw(last["issued_raw"])
            calls = last["ordinal"]
            unknown += estimate_runtime_request_input_ceiling(request) + request.max_tokens
    return SessionAccounting(requests_reserved=calls,
        requests_observed=len(budget["attempts"]), known_tokens=budget["tokens"],
        unknown_token_reservation=unknown, retries=budget["retries"],
        unresolved_intents=pending).model_dump(mode="json")
