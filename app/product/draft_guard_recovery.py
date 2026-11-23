"""Create-only recovery of a Chat draft rejected before its first review.

The failed terminal remains archived and the generation prefix is replayed,
never regenerated. This preparation does not authorize any provider request.
"""
import json
from pathlib import Path
import zipfile

from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, digest, tree
from app.product import sol_chat_contract as contract
from app.product.local_failure_recovery import _safe
from app.product.session_usage import session_accounting
from app.report_validation import COACH_REPORT_HEADINGS, report_headings

VERSION = "chat-draft-heading-recovery-v1"
MARKER = "draft-guard-recovery.json"
SCOPE = dict(role="review", max_output_tokens=16384, timeout_seconds=300)


def read(path):
    return json.loads(Path(path).read_bytes())


def session_at(run, reference, *, read_only=True, sink=lambda value: None):
    private = run / ".continuation"
    return CandidateSession(private / "session", binding=reference["binding"],
        transport_root=private / "transport" / run.name, journal_root=private / "journal",
        guard_sha=reference.get("guard_sha256"), checkpoint_sha=reference.get("checkpoint_sha256"),
        contract_module=contract, worker_product=True, read_only=read_only,
        max_new_models=0, checkpoint_sink=sink)


def inspect(parent, reference):
    parent = _safe(parent)
    binding = reference["binding"]
    if (reference["profile"] != contract.WORKER_PROFILE or parent.name != binding["run_id"]
            or reference.get("draft_guard_recovery") is not None):
        raise ValueError("draft_recovery_identity")
    with session_at(parent, reference) as session:
        terminal = read(session.root / "terminal.json")["value"]
        if (terminal.get("terminal_reason") != "draft_safety_failed"
                or terminal.get("run_id") != parent.name or (session.root / "seal.json").exists()
                or tree(session.journal_root)):
            raise ValueError("draft_recovery_not_pre_review")
        segment = parent / ".continuation/segments" / str(terminal["segment"]) / parent.name
        for name in ("manifest.json", "runtime_trace.json", "api_run_receipt.json"):
            if (segment / name).read_bytes() != (parent / name).read_bytes():
                raise ValueError("draft_recovery_projection_changed")
        receipt, manifest = read(parent / "api_run_receipt.json"), read(parent / "manifest.json")
        if (receipt.get("terminal_reason") != "draft_safety_failed"
                or receipt.get("runtime_status") != "completed" or receipt.get("report_available") is not False
                or receipt.get("publication_status") != "rejected"
                or manifest.get("failure_code") != "report_missing_headings"
                or manifest.get("status") != "rejected" or manifest.get("revision_count") != 0
                or any(a["kind"] not in {"player_summary", "deterministic_report", "retrieval_evidence"}
                       for a in manifest["artifacts"])):
            raise ValueError("draft_recovery_not_heading_rejection")
        trace = receipt["trace_reference"]
        if trace["relative_path"] != "runtime_trace.json" or digest((parent / "runtime_trace.json").read_bytes()) != trace["sha256"]:
            raise ValueError("draft_recovery_trace_changed")
        for artifact in manifest["artifacts"]:
            path = _safe(parent / artifact["path"])
            if not path.is_relative_to(parent) or digest(path.read_bytes()) != artifact["sha256"]:
                raise ValueError("draft_recovery_artifact_changed")
        accounting = session_accounting(session)
        if (accounting != reference["accounting"] or accounting["unresolved_intents"]
                or accounting["retries"] or accounting["unknown_token_reservation"]):
            raise ValueError("draft_recovery_accounting")
        from app.runtime.sol_session_receipts import request_from_raw, recover_success
        intents = sorted((session.root / "operations").glob("*-intent.json"))
        models = 0
        last_kind, value = None, None
        for ordinal, path in enumerate(intents, 1):
            intent = read(path)
            result = read(path.with_name(path.name.replace("-intent", "-result")))
            if (intent["ordinal"] != ordinal or path.name != f"{ordinal:04d}-intent.json"
                    or result["intent_sha256"] != digest(path.read_bytes())):
                raise ValueError("draft_recovery_prefix_binding")
            last_kind, value = intent["kind"], result["value"]
            if last_kind == "model":
                if value.get("ok") is not True or contract.role_for_request(request_from_raw(value["issued_raw"])) != "generation":
                    raise ValueError("draft_recovery_not_successful_generation")
                models += 1
                attempt = read(session.root / "operations" / f"attempt-{models:03d}.json")
                recovered, _, _ = recover_success(session.transport_root, intent, attempt, contract_module=contract)
                if any(recovered[k] != value[k] for k in ("response_raw", "budget", "issued_raw", "receipt_request_sha256")):
                    raise ValueError("draft_recovery_receipt_changed")
            elif last_kind not in {"source", "publication-source", "memory", "memory-manifest", "tool"}:
                raise ValueError("draft_recovery_unexpected_operation")
        if (last_kind != "model" or not models or accounting["requests_observed"] != models
                or accounting["requests_reserved"] != models
                or len(list((session.root / "operations").glob("attempt-*.json"))) != models):
            raise ValueError("draft_recovery_incomplete_generation")
        response = json.loads(value["response_raw"])
        report = response.get("content")
        if response["finish_reason"] != "stop" or not isinstance(report, str):
            raise ValueError("draft_recovery_no_final_draft")
        # Passing structure only permits a first review. It never approves content.
        if tuple(h.identity for h in report_headings(report) if h.identity is not None) != COACH_REPORT_HEADINGS:
            raise ValueError("draft_recovery_structure_still_invalid")
        return dict(binding=binding, accounting=accounting, active_seconds=session.active_before,
                    operations=len(intents), report_sha256=digest(report.encode()))


def prepare(*, parent_run, destination_root, reference):
    parent, root = _safe(parent_run), _safe(destination_root)
    child = root / parent.name
    if child.exists() or child.is_relative_to(parent) or parent.is_relative_to(child):
        raise ValueError("draft_recovery_destination_not_new")
    state, before = inspect(parent, reference), tree(parent)
    pins = []
    with session_at(child, {"binding": state["binding"]}, read_only=False, sink=pins.append) as session:
        session.active_before = state["active_seconds"]
        for part in ("session/operations", "transport"):
            for name in tree(parent / ".continuation" / part):
                target = child / ".continuation" / part / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write((parent / ".continuation" / part / name).read_bytes())
        with zipfile.ZipFile(session.root / "draft-guard-parent.zip", "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in before:
                bundle.writestr(name, (parent / name).read_bytes())
        write_new_json(session.root / MARKER, dict(version=VERSION, parent_reference=reference,
            report_sha256=state["report_sha256"], new_request_scope=SCOPE,
            parent_inventory_sha256=digest(json.dumps(before, sort_keys=True).encode())))
        session._checkpoint("draft_heading_failure_prefix_imported")
        if session_accounting(session) != state["accounting"]:
            raise ValueError("draft_recovery_budget_changed")
    if tree(parent) != before:
        raise ValueError("draft_recovery_parent_changed")
    proof = dict(version=VERSION, parent_run=str(parent), destination_root=str(root),
        parent_reference=reference, parent_inventory=before, **state, new_model_requests=0,
        child_checkpoint={**pins[-1], "checkpoint": Path(pins[-1]["checkpoint"]).name}, child_inventory=tree(child))
    path = root / (parent.name + "-recovery.json")
    write_new_json(path, proof)
    return path, digest(path.read_bytes())


def verify(path, sha, *, runs_root):
    path, root = _safe(path), _safe(runs_root)
    if digest(path.read_bytes()) != sha:
        raise ValueError("draft_recovery_proof_changed")
    proof = read(path)
    if proof["version"] != VERSION or proof["destination_root"] != str(root) or proof["new_model_requests"] != 0:
        raise ValueError("draft_recovery_proof_binding")
    parent, child = _safe(proof["parent_run"]), root / proof["binding"]["run_id"]
    if tree(parent) != proof["parent_inventory"] or tree(child) != proof["child_inventory"]:
        raise ValueError("draft_recovery_inventory")
    state = inspect(parent, proof["parent_reference"])
    if any(proof[k] != v for k, v in state.items()):
        raise ValueError("draft_recovery_state")
    private = child / ".continuation"
    with zipfile.ZipFile(private / "session/draft-guard-parent.zip") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or {n: digest(archive.read(n)) for n in names} != proof["parent_inventory"]:
            raise ValueError("draft_recovery_archive")
    for part in ("session/operations", "transport"):
        if tree(private / part) != tree(parent / ".continuation" / part):
            raise ValueError("draft_recovery_prefix")
    with session_at(child, dict(binding=proof["binding"], **proof["child_checkpoint"])) as session:
        marker = read(session.root / MARKER)
        if ((session.root / "terminal.json").exists() or tree(session.journal_root)
                or marker != dict(version=VERSION, parent_reference=proof["parent_reference"],
                    report_sha256=proof["report_sha256"], new_request_scope=SCOPE,
                    parent_inventory_sha256=digest(json.dumps(proof["parent_inventory"], sort_keys=True).encode()))
                or session_accounting(session) != proof["accounting"] or session.active_before < proof["active_seconds"]):
            raise ValueError("draft_recovery_child_state")
    return proof


def guard_new_request(session, request):
    """Runs only for a NEW model operation, before intent/reservation/provider IO."""
    marker = session.root / MARKER
    try:
        if not marker.exists():
            return
        from app.evaluation.golden_stream_bridge import REQUEST
        bound = read(marker)
        pending = REQUEST.validate_json(json.dumps(request))
        if (bound["version"] != VERSION or bound["new_request_scope"] != SCOPE
                or session.contract_module is not contract or contract.role_for_request(pending) != "review"
                or not 0 < pending.max_tokens <= SCOPE["max_output_tokens"]
                or not 0 < pending.timeout_s <= SCOPE["timeout_seconds"]):
            raise ValueError("outside_scope")
    except (OSError, ValueError, KeyError, TypeError):
        raise SessionBlocked("session_new_request_scope_rejected") from None
