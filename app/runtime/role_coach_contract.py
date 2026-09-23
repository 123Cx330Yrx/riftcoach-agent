"""Source-bound identity for the adopted, unadmitted two-model composition."""
import hashlib
import json
from pathlib import Path

from app.evaluation.prompt_context_identity import ComponentFingerprint
from .native_coach_contract import component_fingerprints as native_fingerprints


def component_fingerprints(skill):
    from app.evaluation import golden_native_partitioned_tool_review as partitioned
    from app.evaluation.golden_native_business_policy import REVISION_POLICY
    from app.evaluation.golden_explicit_source_projection import VERSION, OLD_ADDRESS, NEW_ADDRESS
    from .reviewer_roles import role_descriptor
    rows = {row.component_id: row for row in native_fingerprints(skill)}
    values = {
        "evaluation_schema": json.dumps(partitioned.PartitionedReview.model_json_schema(), sort_keys=True),
        "initial_review_policy": partitioned._review_policy().replace(OLD_ADDRESS, NEW_ADDRESS),
        "reassessment_policy": partitioned._review_policy("prior").replace(OLD_ADDRESS, NEW_ADDRESS),
        "revision_policy": REVISION_POLICY.replace(OLD_ADDRESS, NEW_ADDRESS),
        "source_projection": VERSION,
        "role_descriptor": json.dumps(role_descriptor(), sort_keys=True),
    }
    root = Path(__file__).resolve().parents[2]
    sources = (
        "app/evaluation/golden_role_review.py",
        "app/evaluation/golden_native_partitioned_tool_review.py",
        "app/evaluation/golden_native_tool_review.py",
        "app/evaluation/golden_native_business_policy.py",
        "app/evaluation/golden_explicit_source_projection.py",
        "app/runtime/role_coach_contract.py",
        "app/runtime/coach_contract.py",
        "app/providers/zhipu_profiles.py",
        "app/runtime/reviewer_roles.py",
        "app/runtime/coach_budget.py",
        "app/runtime/coach_context.py",
        "app/runtime/observed_provider.py",
        "app/runtime/recorder.py",
        "app/runtime/runtime.py",
        "app/runtime/models.py",
        "app/model_runtime.py",
    )
    values.update({source: (root/source).read_text(encoding="utf-8") for source in sources})
    for source, value in values.items():
        key = source.replace("/", ".").replace(".py", "")
        rows[key] = ComponentFingerprint(component_id=key, source=source,
            sha256=hashlib.sha256(value.encode()).hexdigest())
    return tuple(rows.values())
