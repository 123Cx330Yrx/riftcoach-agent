"""Recompute calibration evidence, never classify prose or claim model success."""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/datasets/golden_stability_calibration_v1.json"
SOURCE = ROOT / "data/evaluation/datasets/golden_quality_counterexamples_v1.json"


def check_evidence(data: dict, source_bytes: bytes) -> dict:
    if data["schema_version"] != "golden-stability-calibration-v1":
        raise ValueError("unsupported calibration version")
    if hashlib.sha256(source_bytes).hexdigest() != data["source_dataset_sha256"]:
        raise ValueError("source evidence changed")
    rows = json.loads(source_bytes)["samples"]
    wins = [r for r in rows if r["role"] == "MIDDLE" and r["win"] is True]
    losses = [r for r in rows if r["role"] == "MIDDLE" and r["win"] is False]
    if (len(wins), len(losses)) != (2, 2):
        raise ValueError("selected cohort changed")
    facts = {}
    for metric in ("gold_per_min", "damage_per_min"):
        w = [Decimal(str(r[metric])) for r in wins]
        l = [Decimal(str(r[metric])) for r in losses]
        facts[metric] = {"win_mean": str(sum(w) / len(w)),
                         "loss_mean": str(sum(l) / len(l)),
                         "all_selected_losses_below_all_selected_wins": max(l) < min(w)}
        if not facts[metric]["all_selected_losses_below_all_selected_wins"]:
            raise ValueError("sample-local direction no longer supported")
    cases = data["cases"]
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("duplicate case identity")
    counts = Counter(c["expected"] for c in cases)
    if counts != {"accept": 4, "reject": 4, "clarify": 4}:
        raise ValueError("three-way calibration incomplete")
    if any(not c["claim"].strip() or not c["rationale"].strip() for c in cases):
        raise ValueError("missing human annotation")
    return {"status": "offline_calibration_evidence_verified", "label_counts": dict(counts),
            "facts": facts, "model_evaluated": False, "semantic_fix_verified": False,
            "held_out": False}


if __name__ == "__main__":
    print(json.dumps(check_evidence(json.loads(DATASET.read_text(encoding="utf-8")), SOURCE.read_bytes())))
