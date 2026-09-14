"""Offline additive size probe; not a registered runtime or semantic test."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.evaluation.golden_fact_candidate import fact_pack, FactEvaluation
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling
from scripts.check_golden_coverage_requests import measure


def probe(source, report, failure):
    pack = fact_pack(json.loads((source / "inputs/player_summary.json").read_text(encoding="utf-8")))
    extra = json.dumps({k: v for k, v in pack.items() if k != "facts"}, ensure_ascii=False, separators=(",", ":"))
    extra += "\n" + json.dumps(FactEvaluation.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
    ceilings = []

    def estimate(request):
        messages = list(request.messages)
        messages[-1] = replace(messages[-1], content=messages[-1].content + "\n" + extra)
        ceilings.append(estimate_runtime_request_input_ceiling(replace(request, messages=tuple(messages))))
        return estimate_runtime_request_input_ceiling(request)

    with patch("scripts.check_golden_coverage_requests.estimate_runtime_request_input_ceiling", estimate):
        baseline = measure(source, report, scope_v5=True, failed_response=failure)
    return {"baseline": baseline, "candidate_additive_size_probe": ceilings,
            "registry_keys": len(pack["facts"]), "provenance_keys": len(pack["provenance"]),
            "new_policy_included": False, "runtime_integrated": False, "semantic_approval": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--failed-response", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.source_run, args.report, args.failed_response)))
