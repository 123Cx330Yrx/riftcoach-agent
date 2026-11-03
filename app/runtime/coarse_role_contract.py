"""Fingerprint the explicit coarse-source runtime; never reuse old admission."""
import hashlib
from pathlib import Path
from app.evaluation.prompt_context_identity import ComponentFingerprint
from app.runtime.role_coach_contract import component_fingerprints as role_fingerprints


def component_fingerprints(skill):
    rows = {r.component_id:r for r in role_fingerprints(skill)}
    from app.evaluation.golden_coarse_source_projection import VERSION, ROOT_POLICY, ROW_ADDRESS, OLD_ROOT_POLICY
    from app.evaluation.golden_explicit_source_projection import NEW_ADDRESS
    from app.evaluation.golden_role_clarity import review_policy
    from app.evaluation.golden_native_business_policy import REVISION_POLICY
    from app.evaluation.golden_explicit_source_projection import OLD_ADDRESS
    values = {"source_projection": VERSION,
        "initial_review_policy": review_policy().replace(NEW_ADDRESS, ROW_ADDRESS).replace(OLD_ROOT_POLICY, ROOT_POLICY),
        "reassessment_policy": review_policy("prior").replace(NEW_ADDRESS, ROW_ADDRESS).replace(OLD_ROOT_POLICY, ROOT_POLICY),
        "revision_policy": REVISION_POLICY.replace(OLD_ADDRESS, ROW_ADDRESS).replace(OLD_ROOT_POLICY, ROOT_POLICY)}
    for key,value in values.items():
        rows[key] = ComponentFingerprint(component_id=key,source=key,sha256=hashlib.sha256(value.encode()).hexdigest())
    root = Path(__file__).resolve().parents[2]
    for path in ("app/evaluation/golden_role_coarse.py", "app/evaluation/golden_coarse_source_projection.py",
                 "app/runtime/coarse_role_contract.py", "app/evaluation/coarse_role_qualification.py",
                 "app/runtime/receipted_provider_factory.py", "app/product/native_coach_composition.py",
                 "app/prompt_program/resolver.py", "app/prompt_program/models.py",
                 "app/evaluation/golden_review_source_catalog.py"):
        key = path.replace("/", ".").replace(".py", "")
        rows[key] = ComponentFingerprint(component_id=key, source=path,
            sha256=hashlib.sha256((root/path).read_text(encoding="utf-8").encode()).hexdigest())
    return tuple(rows.values())
