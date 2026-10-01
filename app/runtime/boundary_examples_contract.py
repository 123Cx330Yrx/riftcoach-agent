"""Fingerprint the tested examples and their actual application identity."""
import hashlib
from pathlib import Path

from app.evaluation.prompt_context_identity import ComponentFingerprint
from app.runtime.correction_scope_contract import component_fingerprints as baseline_fingerprints


def component_fingerprints(skill):
    from app.evaluation.golden_role_boundary_examples import review_policy
    rows = {r.component_id: r for r in baseline_fingerprints(skill)}
    values = {"initial_review_policy": review_policy(),
              "reassessment_policy": review_policy("prior")}
    root = Path(__file__).resolve().parents[2]
    for path in ("app/evaluation/golden_role_boundary_examples.py",
                 "app/runtime/boundary_examples_contract.py",
                 "app/evaluation/boundary_examples_qualification.py"):
        values[path] = (root / path).read_text(encoding="utf-8")
    for key, value in values.items():
        identity = key.replace("/", ".").replace(".py", "")
        rows[identity] = ComponentFingerprint(component_id=identity, source=key,
            sha256=hashlib.sha256(value.encode()).hexdigest())
    return tuple(rows.values())
