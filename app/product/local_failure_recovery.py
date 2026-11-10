"""Explicit relocation of a receipted pre-review local failure.

This administrative operation sends nothing. It creates a new attempt directory
for the SAME task/run, retaining the failed directory and exact committed prefix.
Ordinary owner resume and Worker execution remain the only dispatch path.
"""
import json
from pathlib import Path
import zipfile

from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import CandidateSession, digest, tree
from app.product import sol_contract
from app.product.session_usage import session_accounting

VERSION = "sol-product-local-failure-recovery-v1"


def _read(path):
    return json.loads(Path(path).read_bytes())


def _safe(path):
    path = Path(path).absolute()
    if path.resolve() != path or path.is_symlink():
        raise ValueError("local_recovery_unsafe_path")
    return path


def _session(run, reference, *, read_only=True, sink=lambda value: None):
    private = run / ".continuation"
    return CandidateSession(private / "session", binding=reference["binding"],
        transport_root=private / "transport" / run.name, journal_root=private / "journal",
        guard_sha=reference.get("guard_sha256"), checkpoint_sha=reference.get("checkpoint_sha256"),
        contract_module=sol_contract, worker_product=True, read_only=read_only,
        max_new_models=0, checkpoint_sink=sink)


def inspect_parent(run, reference):
    """Only complete generation prefixes, before knowledge storage/reviews."""
    run = _safe(run)
    if reference["profile"] != sol_contract.WORKER_PROFILE:
        raise ValueError("local_recovery_profile")
    binding = reference["binding"]
    if run.name != binding["run_id"]:
        raise ValueError("local_recovery_run_identity")
    receipt = _read(run / "api_run_receipt.json")
    if (receipt.get("run_id") != run.name or receipt.get("runtime_status") != "failed"
            or receipt.get("terminal_reason") != "harness_execution_failed"
            or receipt.get("report_available") is not False
            or receipt.get("publication_status") is not None):
        raise ValueError("local_recovery_not_local_failure")
    trace = receipt["trace_reference"]
    if (trace.get("relative_path") != "runtime_trace.json"
            or digest((run / "runtime_trace.json").read_bytes()) != trace["sha256"]):
        raise ValueError("local_recovery_trace_changed")
    signals = [event["signal"]["kind"] for event in _read(run / "runtime_trace.json")["events"]]
    if "knowledge_ready" in signals:
        raise ValueError("local_recovery_past_generation")
    with _session(run, reference) as session:
        if ((session.root / "terminal.json").exists() or (session.root / "seal.json").exists()
                or tree(session.journal_root)
                or (run / "knowledge/retrieval_evidence.json").exists()):
            raise ValueError("local_recovery_past_generation")
        accounting = session_accounting(session)
        if accounting != reference["accounting"] or accounting["unresolved_intents"]:
            raise ValueError("local_recovery_pending_or_accounting_changed")
        intents = sorted((session.root / "operations").glob("*-intent.json"))
        models = 0
        last_kind = None
        for ordinal, path in enumerate(intents, 1):
            intent = _read(path)
            result_path = path.with_name(path.name.replace("-intent", "-result"))
            result = _read(result_path)
            if (intent["ordinal"] != ordinal or path.name != f"{ordinal:04d}-intent.json"
                    or result["intent_sha256"] != digest(path.read_bytes())):
                raise ValueError("local_recovery_prefix_binding")
            last_kind, value = intent["kind"], result["value"]
            if last_kind == "model":
                from app.runtime.sol_session_receipts import request_from_raw, recover_success
                request = request_from_raw(value["issued_raw"])
                if sol_contract.role_for_request(request) != "generation" or value.get("ok") is not True:
                    raise ValueError("local_recovery_not_generation_success")
                models += 1
                attempt = _read(session.root / "operations" / f"attempt-{models:03d}.json")
                # Validate real transport/usage receipts, not only session claims.
                recovered, _, _ = recover_success(session.transport_root, intent, attempt,
                                                  contract_module=sol_contract)
                if (recovered["response_raw"] != value["response_raw"]
                        or recovered["budget"] != value["budget"]):
                    raise ValueError("local_recovery_response_changed")
            elif last_kind not in {"source", "publication-source", "memory", "memory-manifest", "tool"}:
                raise ValueError("local_recovery_unexpected_operation")
        if (last_kind != "model" or not models or accounting["requests_observed"] != models
                or accounting["requests_reserved"] != models or accounting["retries"]
                or accounting["unknown_token_reservation"]):
            raise ValueError("local_recovery_incomplete_generation")
        response = json.loads(value["response_raw"])
        if response["finish_reason"] != "stop" or not response.get("content"):
            raise ValueError("local_recovery_generation_not_final")
        return dict(accounting=accounting, active_seconds=session.active_before,
                    operations=len(intents), binding=binding)


def prepare_local_failure_recovery(*, parent_run, destination_root, reference):
    """Create-only copy; original guard/checkpoints are retained, never rewritten."""
    parent_run, destination_root = _safe(parent_run), _safe(destination_root)
    child = destination_root / parent_run.name
    if (child.exists() or child.is_relative_to(parent_run) or parent_run.is_relative_to(child)):
        raise ValueError("local_recovery_destination_not_new")
    state = inspect_parent(parent_run, reference)
    before = tree(parent_run)
    pins = []
    child_reference = dict(binding=state["binding"])
    with _session(child, child_reference, read_only=False, sink=pins.append) as session:
        # Imported budget stays inside the original results; the clock also
        # starts at the parent's recorded active time rather than zero.
        session.active_before = state["active_seconds"]
        for original, target in (
                (parent_run / ".continuation/session/operations", session.root / "operations"),
                (parent_run / ".continuation/transport" / parent_run.name, session.transport_root)):
            for name in tree(original):
                output = target / name
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open("xb") as stream:
                    stream.write((original / name).read_bytes())
        # Archive original failure/session evidence within the new run's normal
        # private-data deletion boundary as well as keeping the original root.
        archive = child / ".continuation/failed-parent.zip"
        # A container avoids recreating the already-deep failed segment paths
        # beneath an additional archive directory on Windows.
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in before:
                bundle.writestr(name, (parent_run / name).read_bytes())
        session._checkpoint("local_failure_prefix_imported")
        if session_accounting(session) != state["accounting"]:
            raise ValueError("local_recovery_accounting_changed")
    if tree(parent_run) != before:
        raise ValueError("local_recovery_parent_changed")
    proof = dict(version=VERSION, parent_run=str(parent_run), destination_root=str(destination_root),
        parent_inventory=before, parent_reference=reference, **state,
        child_checkpoint={**pins[-1], "checkpoint": Path(pins[-1]["checkpoint"]).name},
        child_inventory=tree(child), new_model_requests=0)
    proof_path = destination_root / (parent_run.name + "-recovery.json")
    write_new_json(proof_path, proof)
    return proof_path, digest(proof_path.read_bytes())


def verify_local_failure_recovery(proof_path, proof_sha256, *, runs_root):
    proof_path = _safe(proof_path)
    raw = proof_path.read_bytes()
    if digest(raw) != proof_sha256:
        raise ValueError("local_recovery_proof_changed")
    proof = json.loads(raw)
    root = _safe(runs_root)
    if (proof["version"] != VERSION or str(root) != proof["destination_root"]
            or proof["new_model_requests"] != 0):
        raise ValueError("local_recovery_proof_binding")
    parent = _safe(proof["parent_run"])
    if tree(parent) != proof["parent_inventory"]:
        raise ValueError("local_recovery_parent_changed")
    state = inspect_parent(parent, proof["parent_reference"])
    if any(proof[key] != value for key, value in state.items()):
        raise ValueError("local_recovery_parent_state_changed")
    child = root / proof["binding"]["run_id"]
    if tree(child) != proof["child_inventory"]:
        raise ValueError("local_recovery_child_changed")
    private = child / ".continuation"
    with zipfile.ZipFile(private / "failed-parent.zip") as archive:
        names = archive.namelist()
        if (len(names) != len(set(names))
                or {name: digest(archive.read(name)) for name in names} != proof["parent_inventory"]):
            raise ValueError("local_recovery_archive_changed")
    for relative in ("session/operations", "transport"):
        if tree(private / relative) != tree(parent / ".continuation" / relative):
            raise ValueError("local_recovery_prefix_changed")
    reference = dict(binding=proof["binding"], **proof["child_checkpoint"])
    with _session(child, reference) as session:
        if (session_accounting(session) != proof["accounting"]
                or session.active_before < proof["active_seconds"]):
            raise ValueError("local_recovery_budget_changed")
    return proof
