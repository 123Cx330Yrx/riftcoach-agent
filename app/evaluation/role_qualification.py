"""Frozen review coverage and receipt replay for the explicitly adopted roles.

Preparation is offline. Old results cannot qualify a new composition; this
module never enables a live entry or establishes production admission.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path

from app.evaluation import golden_native_partitioned_tool_review as review
from app.evaluation.golden_explicit_source_projection import VERSION as PROJECTION_VERSION
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_notes import RoleNoteReviewWorkflow
from app.evaluation.golden_role_tool_delivery import DELIVERY_ID
from app.evaluation.golden_role_clarity import (
    RoleClarityReviewWorkflow as RoleReviewWorkflow, RoleClarityReview, CLARITY_ID, review_policy,
)
from app.evaluation.golden_stream_bridge import (
    REQUEST, RESPONSE, CapacityBridgeObservation, validate_request,
)
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling as size
from app.harness.steps import EvaluationRequest, EvaluationVerdict, KnowledgeCitation, KnowledgeEvidence, RevisionRequest
from app.runtime.coach_contract import ROLE_COACH_CONTRACT
from app.runtime.reviewer_roles import ROLE_COMPOSITION_ID, role_descriptor, role_for_request

ROOT = Path(__file__).resolve().parents[2]
VERSION = "flash-glm-role-qualification-v1"
COVERAGE = Path("data/evaluation/results/golden_native_partitioned_tool_coverage_v2.json")
ASSETS = Path("examples/runtime_profiles/flash_glm_review_v1")
DATASETS = {suite: Path("data/evaluation/datasets") / name for suite, name in (
    ("observed", "golden_observed_review_controls_v1.json"),
    ("attribution", "golden_native_product_attribution_controls_v1.json"),
    ("scope", "golden_native_scope_resolution_controls_v1.json"),
    ("claim-scope", "golden_native_claim_scope_controls_v1.json"),
)}


def _read(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _source(path):
    saved = _read(path)
    raw = saved["evaluation_request"]
    k = raw["knowledge"]
    knowledge = KnowledgeEvidence(context=k["context"], source_ids=tuple(k["source_ids"]),
        citations=tuple(KnowledgeCitation(**c) for c in k["citations"]), abstained=k["abstained"])
    source = EvaluationRequest(**dict(raw, knowledge=knowledge))
    if "source_input_sha256" in saved and digest(review.native.build_inputs(source).data_json) != saved["source_input_sha256"]:
        raise ValueError("role_qualification_fixture_source_changed")
    if "raw" in saved and digest(saved["raw"]) != saved["raw_sha256"]:
        raise ValueError("role_qualification_fixture_raw_changed")
    return source


def frozen_cases(*, root=ROOT):
    """Restore the original 15, including old completed cases, without data/runs."""
    coverage = _read(root / COVERAGE)
    sources = {
        "other": _source(root / "tests/fixtures/native_missing_block_reassessment.json"),
        "observed": _source(root / "tests/fixtures/native_heading_recheck_failure.json"),
    }
    cases = []
    for frozen in coverage["completed"] + coverage["cases"]:
        path = root / DATASETS[frozen["suite"]]
        if _sha(path) != frozen["manifest_sha256"]:
            raise ValueError("role_qualification_dataset_changed")
        data = _read(path)
        case = data["cases"][frozen["index"] - 1]
        source = sources["observed" if frozen["suite"] == "observed" else "other"]
        req = replace(source, report=case["report"], user_utterance=data["user_utterance"])
        inputs = review.native.build_inputs(req)
        if (case["id"] != frozen["id"] or case["expected_report"] != frozen["expected_initial"]
                or digest(req.report) != frozen["report_sha256"]
                or digest(inputs.data_json) != frozen["input_sha256"]):
            raise ValueError("role_qualification_frozen_input_changed")
        cases.append((dict(frozen, key=f'{frozen["suite"]}:{frozen["index"]}'), req))
    if (coverage["required_distinct_inputs"] != 15
            or len(cases) != 15 or len({c[0]["key"] for c in cases}) != 15
            or len({c[0]["input_sha256"] for c in cases}) != 15):
        raise ValueError("role_qualification_coverage_invalid")
    by_key = {c[0]["key"]: c[0] for c in cases}
    for alias in coverage["aliases"]:
        suite, index = alias["alias"].split(":")
        data = _read(root / DATASETS[suite])
        source = sources["observed" if suite == "observed" else "other"]
        req = replace(source, report=data["cases"][int(index) - 1]["report"], user_utterance=data["user_utterance"])
        if digest(review.native.build_inputs(req).data_json) != alias["input_sha256"] or alias["input_sha256"] != by_key[alias["canonical"]]["input_sha256"]:
            raise ValueError("role_qualification_alias_changed")
    return cases, deepcopy(coverage["aliases"])


def candidate_identity(*, root=ROOT):
    descriptor = ROLE_COACH_CONTRACT.descriptor()
    manifest_path = root / ASSETS / "prompt_programs/recent-form-review/manifest.json"
    manifest = _read(manifest_path)
    if any(manifest[k] != descriptor[k] for k in ("program_version", "skill_version", "evaluation_contract_version")):
        raise ValueError("role_qualification_program_identity_mismatch")
    # Include all declared component fingerprints, plus actual role assets.
    # The composition root independently verifies fingerprints before preview/run.
    return dict(composition=ROLE_COMPOSITION_ID, contract=ROLE_COACH_CONTRACT.snapshot().model_dump(),
        program_sha256=manifest["program_sha256"], manifest_sha256=_sha(manifest_path),
        asset_sha256={name: _sha(root / ASSETS / name) for name in (
            "skills/recent-form-review/SKILL.md", "skills/recent-form-review/manifest.yaml")},
        source_projection=PROJECTION_VERSION, request_delivery=DELIVERY_ID, review_output=CLARITY_ID, roles=role_descriptor(),
        policy_sha256=digest(review_policy()),
        schema_sha256=digest(compact(RoleClarityReview.model_json_schema())))


def prepare_qualification(*, root=ROOT):
    cases, aliases = frozen_cases(root=root)
    identity = candidate_identity(root=root)
    rows, requests = [], {}
    for frozen, req in cases:
        request = RoleReviewWorkflow.make_request(review.native.build_inputs(req))
        raw = validate_request(request, transport_id=identity["roles"]["review"]["transport_id"])
        requests[frozen["key"]] = raw
        rows.append({k: frozen[k] for k in ("key", "suite", "index", "id", "manifest_sha256", "input_sha256", "report_sha256", "expected_initial")}
            | dict(status="pending", request_sha256=hashlib.sha256(raw).hexdigest(), first_input_ceiling=size(request)))
    plan = dict(qualification_version=VERSION, identity=identity, source_coverage_sha256=_sha(root / COVERAGE),
        required_distinct_inputs=15, cases=rows, aliases=aliases, completed=[],
        per_case_budget=dict(max_calls=5, max_revisions=1, max_tokens=401920, max_seconds=900,
            max_output_per_call=32768, max_seconds_per_call=300, sdk_retries=0),
        review_controls_qualified=False, actual_product_task_qualified=False,
        production_admitted=False, execution_enabled=False, labels_sent_to_model=False)
    return plan, requests


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError("role_receipt_usage_invalid")
    return value


def read_role_calls(directory):
    """Check the global call namespace and bind each returned raw artifact.

    No recursive counting: model paths and stream ordinals come from the shared
    reservation. A reserved call with no observed usage remains unknown.
    """
    directory = Path(directory).resolve()
    files = sorted(p for p in directory.glob("call-*.json") if not p.name.startswith("call-result-"))
    result_files = {p.name for p in directory.glob("call-result-*.json")}
    expected_results = set()
    calls = []
    roles = role_descriptor()
    for ordinal, file in enumerate(files, 1):
        record = _read(file)
        if file.name != f"call-{ordinal:03d}.json" or type(record.get("ordinal")) is not int or record["ordinal"] != ordinal:
            raise ValueError("role_receipt_ordinal_mismatch")
        role = record.get("role")
        # The concrete transport fixes profile body/SDK retries, while these
        # identity fields are carried by each existing raw stream reservation.
        if role not in roles or any(record.get(k) != roles[role][k] for k in (
                "provider", "model", "thinking_profile_id", "transport_id")):
            raise ValueError("role_receipt_model_mismatch")
        raw_dir = "review" if role == "review" else "generation"
        if record.get("raw_directory") != raw_dir or record.get("state") != "reserved_before_io":
            raise ValueError("role_receipt_path_mismatch")
        model_dir = (directory / raw_dir).resolve()
        if not model_dir.is_relative_to(directory.resolve()):
            raise ValueError("role_receipt_path_mismatch")
        request_path = model_dir / f"request-{ordinal:03d}.json"
        raw = request_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record.get("request_sha256"):
            raise ValueError("role_receipt_request_mismatch")
        wire = strict_json(raw.decode("utf-8"))
        request = REQUEST.validate_json(raw, strict=True)
        # Pydantic widens 300 to 300.0. Restore the original JSON numeric
        # representation before the unchanged receipt validator hashes it;
        # never replace a raw request hash with a reserialized approximation.
        request = replace(request, **{k: wire[k] for k in ("temperature", "timeout_s", "top_p")})
        if role_for_request(request) != role or validate_request(request, transport_id=record["transport_id"]) != raw:
            raise ValueError("role_receipt_request_identity_mismatch")
        stream = model_dir / f"stream-{ordinal:03d}"
        reservation_path = stream / "reservation.json"
        if reservation_path.exists():
            reservation = _read(reservation_path)
            if (reservation.get("state") != "reserved_before_io" or type(reservation.get("ordinal")) is not int
                    or reservation["ordinal"] != ordinal or reservation.get("transport_id") != record["transport_id"]
                    or reservation.get("request_sha256") != record["request_sha256"]
                    or reservation.get("stream_tool_arguments") != bool(request.tools)
                    or reservation.get("model", record["model"]) != record["model"]
                    or reservation.get("thinking_profile_id", record["thinking_profile_id"]) != record["thinking_profile_id"]):
                raise ValueError("role_receipt_reservation_mismatch")
            if role == "review" and (reservation.get("model") != record["model"] or reservation.get("thinking_profile_id") != record["thinking_profile_id"]):
                raise ValueError("role_receipt_reservation_model_missing")
        response_path = model_dir / f"response-{ordinal:03d}.json"
        response = RESPONSE.validate_json(response_path.read_bytes()) if response_path.exists() else None
        if response is not None and (response.provider != record["provider"] or response.model != record["model"]):
            raise ValueError("role_receipt_response_model_mismatch")
        result_path = directory / f"call-result-{ordinal:03d}.json"
        terminal_path = stream / "result.json"
        terminal = _read(terminal_path) if terminal_path.exists() else None
        if terminal is not None and terminal.get("transport_id") != record["transport_id"]:
            raise ValueError("role_receipt_terminal_mismatch")
        completed = result_path.exists()
        if completed:
            expected_results.add(result_path.name)
            result = _read(result_path)
            if (response is None or not reservation_path.exists() or terminal is None or terminal.get("state") != "complete"
                    or any(result.get(k) != v for k, v in record.items() if k != "state")
                    or result.get("state") != "complete" or result.get("response_sha256") != _sha(response_path)
                    or any(_count(result.get(k)) != getattr(response.usage, k) for k in ("input_tokens", "output_tokens"))):
                raise ValueError("role_receipt_result_mismatch")
        usage = ({k: getattr(response.usage, k) for k in ("input_tokens", "output_tokens")} if response else None)
        progress_path = stream / "progress.json"
        if usage is None and progress_path.exists():
            progress = CapacityBridgeObservation.model_validate(_read(progress_path))
            if progress.input_tokens is not None and progress.output_tokens is not None:
                usage = dict(input_tokens=progress.input_tokens, output_tokens=progress.output_tokens)
        artifacts = [file, request_path] + [p for p in (response_path, reservation_path, terminal_path, result_path, progress_path) if p.exists()]
        calls.append(dict(binding=record, request=request, response=response, completed=completed, usage=usage,
            artifact_sha256={p.relative_to(directory).as_posix(): _sha(p) for p in artifacts}))
    if result_files != expected_results:
        raise ValueError("role_receipt_orphan_result")
    return calls


def summarize_role_calls(directory):
    calls = read_role_calls(directory)
    return dict(reserved_calls=len(calls), completed_calls=sum(c["completed"] for c in calls),
        unknown_usage_calls=sum(c["usage"] is None for c in calls),
        observed_unaccepted_calls=sum(not c["completed"] and c["usage"] is not None for c in calls),
        input_tokens=sum(c["usage"]["input_tokens"] for c in calls if c["usage"] is not None),
        output_tokens=sum(c["usage"]["output_tokens"] for c in calls if c["usage"] is not None),
        calls=[dict(c["binding"], completed=c["completed"], usage=c["usage"]) for c in calls])


def _within(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("role_qualification_artifact_outside_root")
    return path


def replay_case(frozen, source, calls):
    """Current qualification always reconstructs the current request delivery."""
    return _replay_case(frozen, source, calls, workflow_type=RoleReviewWorkflow)


def replay_legacy_note_case(frozen, source, calls):
    """Explicit historical replay; never used by current validate_qualification."""
    return _replay_case(frozen, source, calls, workflow_type=RoleNoteReviewWorkflow)


def _replay_case(frozen, source, calls, *, workflow_type):
    """Reconstruct review -> actual revision -> final review from raw exchanges."""
    iterator = iter(calls)
    used, journals = [], []
    def send(prepared):
        call = next(iterator, None)
        if call is None:
            raise ValueError("role_qualification_missing_actual_call")
        issued = call["request"]
        # The shared budget may cap timeout and annotate its receipt, but
        # may not change content, model role, schema, or decoding settings.
        metadata = dict(issued.metadata)
        metadata.pop("coach_budget_contract", None)
        if replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared or issued.timeout_s > prepared.timeout_s:
            raise ValueError("role_qualification_replayed_request_mismatch")
        used.append(call)
        return Exchange(issued, call["response"], call["binding"]["request_sha256"])
    workflow = workflow_type(send)
    initial = workflow.evaluate(source)
    journals.append(deepcopy(workflow.last_journal))
    verdict = "accept" if initial.verdict is EvaluationVerdict.PASS else "reject"
    minimum_score = ROLE_COACH_CONTRACT.descriptor()["minimum_score"]
    if (verdict != frozen["expected_initial"] or initial.verdict is EvaluationVerdict.FAIL
            or (initial.verdict is EvaluationVerdict.PASS and initial.score < minimum_score)):
        raise ValueError("role_qualification_initial_semantics_failed")
    final_report = source.report
    if initial.verdict is EvaluationVerdict.NEEDS_REVISION:
        draft = workflow.revise(RevisionRequest(source.player_summary, source.deterministic_report, source.knowledge, source.report, initial))
        final_report = draft.report
        final = workflow.evaluate(replace(source, report=final_report))
        journals.append(deepcopy(workflow.last_journal))
        if final.verdict is not EvaluationVerdict.PASS or final.score < minimum_score:
            raise ValueError("role_qualification_final_review_failed")
    if next(iterator, None) is not None:
        raise ValueError("role_qualification_unused_actual_call")
    return dict(final_report_sha256=digest(final_report),
        journals_sha256=[digest(compact(j)) for j in journals],
        artifact_sha256=[c["artifact_sha256"] for c in used])


def validate_qualification(result, *, evidence_root, root=ROOT):
    """Replay 15 raw workflows and verify host review of those exact journals.

    Passing proves only this frozen review set. Actual generation/tool/product
    qualification and production admission are separate, still closed gates.
    """
    plan, _ = prepare_qualification(root=root)
    if (result.get("qualification_version") != VERSION or result.get("identity") != plan["identity"]
            or result.get("plan_sha256") != digest(compact(plan))):
        raise ValueError("role_qualification_identity_mismatch")
    rows = result.get("cases", [])
    expected = {c["key"]: c for c in plan["cases"]}
    if (not isinstance(rows, list) or len(rows) != 15 or not all(isinstance(c, dict) for c in rows)
            or {c.get("key") for c in rows} != set(expected)):
        raise ValueError("role_qualification_case_inventory_mismatch")
    sources = dict((f["key"], req) for f, req in frozen_cases(root=root)[0])
    evidence_root = Path(evidence_root)
    for row in rows:
        frozen = expected[row["key"]]
        if any(row.get(k) != frozen[k] for k in ("input_sha256", "report_sha256", "request_sha256")):
            raise ValueError("role_qualification_case_identity_mismatch")
        directory = _within(evidence_root, row["transport_directory"])
        calls = read_role_calls(directory)
        if not calls or len(calls) > 5 or not all(c["completed"] for c in calls):
            raise ValueError("role_qualification_incomplete_receipts")
        if sum(c["usage"]["input_tokens"] + c["usage"]["output_tokens"] for c in calls) > 401920:
            raise ValueError("role_qualification_budget_exceeded")
        replayed = replay_case(frozen, sources[row["key"]], calls)
        host_path = _within(evidence_root, row["host_review_file"])
        if _sha(host_path) != row.get("host_review_sha256"):
            raise ValueError("role_qualification_host_review_hash_mismatch")
        host = _read(host_path)
        bindings = dict(candidate_sha256=digest(compact(plan["identity"])), input_sha256=frozen["input_sha256"],
            initial_request_sha256=calls[0]["binding"]["request_sha256"], **replayed)
        if (any(host.get(k) != v for k, v in bindings.items()) or host.get("semantic_acceptance") is not True
                or not isinstance(host.get("reviewer"), str) or not host["reviewer"].strip()
                or not isinstance(host.get("source_review"), str) or not host["source_review"].strip()):
            raise ValueError("role_qualification_host_review_binding_mismatch")
    return dict(review_controls_qualified=True, accepted_inputs=15, actual_product_task_qualified=False,
        production_admitted=False, execution_enabled=False)
