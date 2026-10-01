"""Owner-approved whole-context controls, separate from frozen strict labels."""
import json
from pathlib import Path

from app.evaluation.golden_contextual_correction import STANDARD_ID
from app.evaluation.golden_review_experiment import digest

MANIFEST = Path(__file__).resolve().parents[1]/"data/evaluation/datasets/golden_contextual_reports_v2.json"


def select_cases(cases):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["standard_id"] != STANDARD_ID or manifest["schema_version"] != "golden-contextual-reports-v2":
        raise ValueError("contextual_manifest_identity_invalid")
    lookup = {row["id"]: row for row in cases}
    selected, seen = [], set()
    for row in manifest["cases"]:
        if row["id"] in seen or row["source_case_id"] not in lookup:
            raise ValueError("contextual_manifest_cases_invalid")
        source = lookup[row["source_case_id"]]
        if row["report_sha256"] != source["report_sha256"] or digest(source["report"]) != row["report_sha256"]:
            raise ValueError("contextual_source_report_changed")
        selected.append(dict(source, **row))
        seen.add(row["id"])
    if len(selected) != 2 or [c["expected_target"] for c in selected] != ["accept", "reject"]:
        raise ValueError("contextual_manifest_controls_invalid")
    return selected


if __name__ == "__main__":
    from scripts.run_golden_integrated_review import main
    main(full_context=True)
