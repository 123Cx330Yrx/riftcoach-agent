"""Replay closed plan identity while still validating rebuilt requests and budgets."""
import hashlib
import json

from app.evaluation.golden_review_experiment import compact, digest


def bind_closed_plan(plan, evidence_path, evidence_sha):
    if not evidence_path.exists():
        return plan
    raw = evidence_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence_sha:
        raise ValueError("closed_preview_evidence_changed")
    receipt = json.loads(raw)["public_json_contents"]["plan.json"]
    frozen = receipt["preparation_plan"]
    # Source code may evolve after closure. All reconstructed business inputs,
    # serialized request hashes, parameters and budgets must still match.
    rebuilt = dict(plan, source_sha256={key: frozen["source_sha256"][key]
                                      for key in plan["source_sha256"]})
    if rebuilt != frozen:
        raise ValueError("closed_preview_request_or_plan_changed")
    if digest(compact(rebuilt)) != receipt["declared_approved_plan_sha256"]:
        raise ValueError("closed_preview_plan_identity")
    return rebuilt
