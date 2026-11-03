"""Verify frozen development evidence; this does not grade generated prose."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1] / "data/evaluation/datasets/golden_quality_counterexamples_v1.json"


def check_evidence(dataset: dict) -> dict:
    if dataset["schema_version"] != "golden-quality-counterexamples-v1":
        raise ValueError("unsupported evidence version")
    rows = dataset["samples"]
    if len(rows) != 5 or any(r["included_in_aggregate"] is not True for r in rows):
        raise ValueError("source cohort changed")
    if any(type(r["win"]) is not bool for r in rows):
        raise ValueError("invalid outcome")
    if [r["role"] for r in rows].count("MIDDLE") != 4 or [r["role"] for r in rows].count("UTILITY") != 1:
        raise ValueError("source role composition changed")

    def average(metric: str, *, win: bool, role: str | None = None) -> Decimal:
        selected = [r for r in rows if r["win"] is win and (role is None or r["role"] == role)]
        return sum(Decimal(str(r[metric])) for r in selected) / len(selected)

    mixed_win = average("cs_per_min", win=True)
    mixed_loss = average("cs_per_min", win=False)
    mid_win = average("cs_per_min", win=True, role="MIDDLE")
    mid_loss = average("cs_per_min", win=False, role="MIDDLE")
    if not (mixed_loss < mixed_win and mid_loss > mid_win):
        raise ValueError("documented cross-role direction reversal no longer holds")
    if (mid_win, mid_loss) != (Decimal("8.805"), Decimal("9.01")):
        raise ValueError("source middle-lane CS evidence changed")
    if (average("damage_per_min", win=True, role="MIDDLE"), average("damage_per_min", win=False, role="MIDDLE")) != (Decimal("1286.755"), Decimal("617.52")):
        raise ValueError("source middle-lane damage evidence changed")
    if [r["vision_score"] for r in rows if r["role"] == "UTILITY"] != [90]:
        raise ValueError("source vision observation changed")
    cases = dataset["cases"]
    if len(cases) != 10 or len({c["id"] for c in cases}) != 10:
        raise ValueError("counterexample coverage changed")
    if sum(c["expected"] == "reject" for c in cases) != 5 or sum(c["expected"] == "accept" for c in cases) != 5:
        raise ValueError("positive and negative controls required")
    return {
        "status": "development_evidence_verified",
        "cases": len(cases), "human_labeled": True, "model_evaluated": False,
        "mid_win_cs_per_min": str(mid_win), "mid_loss_cs_per_min": str(mid_loss),
        "mixed_role_cs_direction_reverses": True,
        "automatic_quality_fix_verified": False,
    }


if __name__ == "__main__":
    print(json.dumps(check_evidence(json.loads(DATASET.read_text(encoding="utf-8"))), ensure_ascii=False))
