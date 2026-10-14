"""Fingerprint the actual review responsibility policies and runtime."""
import hashlib
from pathlib import Path

from app.evaluation.prompt_context_identity import ComponentFingerprint
from app.runtime.coarse_role_contract import component_fingerprints as coarse_fingerprints


def component_fingerprints(skill):
    from app.evaluation.golden_role_correction_scope import review_policy
    rows = {r.component_id: r for r in coarse_fingerprints(skill)}
    values = {"initial_review_policy": review_policy(),
              "reassessment_policy": review_policy("prior")}
    root = Path(__file__).resolve().parents[2]
    for path in ("app/evaluation/golden_role_correction_scope.py",
                 "app/runtime/correction_scope_contract.py",
                 "app/evaluation/correction_scope_qualification.py"):
        values[path] = (root / path).read_text(encoding="utf-8")
    for key, value in values.items():
        identity = key.replace("/", ".").replace(".py", "")
        rows[identity] = ComponentFingerprint(component_id=identity, source=key,
            sha256=hashlib.sha256(value.encode()).hexdigest())
    return tuple(rows.values())
