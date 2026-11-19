"""Rebuild the no-network GLM-5.3 hardened V3 budget proof."""

from __future__ import annotations

from pathlib import Path

from app.evaluation.glm53_bounded_revision_budget_reachability import (
    REPORT_PATH,
    build_v3_budget_reachability_report,
    canonical_v3_budget_reachability_bytes,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = (root / REPORT_PATH).resolve()
    report = build_v3_budget_reachability_report(project_root=root)
    content = canonical_v3_budget_reachability_bytes(report)
    if output.exists():
        if output.read_bytes() != content:
            raise RuntimeError("frozen V3 budget reachability report has drifted")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
    print(
        f"case_tokens={report.case_token_limit} "
        f"domain_tokens={report.domain_token_limit} "
        "external_provider_calls=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
