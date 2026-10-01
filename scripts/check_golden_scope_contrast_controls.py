"""Check source identity, anchors and arithmetic of analyst-authored controls.

This reads local files only. It neither builds a model request nor decides the
meaning of natural-language reports. Frozen labels are checked for provenance,
not automatically established as correct semantic judgments.
"""
import argparse
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/datasets/golden_scope_contrast_controls_v1.json"
SOURCE_SHA256 = "414b5a482786494ecc869a02c035995a51bf0455b1648deced9834107551c841"
METRICS = ("cs_per_min", "gold_per_min")
COHORTS = ("MIDDLE", "selected")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "scope_control_duplicate_json_key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("scope_control_nonfinite_json_number")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=_pairs, parse_constant=_constant)


def load_source():
    require(sha256(DATASET.read_bytes()) == SOURCE_SHA256, "scope_control_source_changed")
    return read_json(DATASET)


def fixture_hash(fixture):
    encoded = json.dumps(fixture, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(encoded)


def _same_json(left, right):
    # Python equality aliases True/1 and False/0; source identity must not.
    encode = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":"), allow_nan=False)
    return encode(left) == encode(right)


def _number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "scope_control_raw_number_invalid")
    return Fraction(str(value))


def _expected_number(value):
    require(isinstance(value, str) and value.strip() == value and bool(value),
            "scope_control_expected_number_invalid")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError("scope_control_expected_number_invalid") from error


def _direction(left, right):
    return "greater" if left > right else "less" if left < right else "equal"


def _display(number):
    with localcontext() as context:
        context.prec = 28
        value = Decimal(number.numerator) / Decimal(number.denominator)
        return format(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def compute(fixture):
    rows = fixture["match_rows"]
    require(isinstance(rows, list) and rows, "scope_control_rows_required")
    refs, ids = [], []
    for row in rows:
        require(type(row.get("evidence_ref")) is int and row["evidence_ref"] > 0,
                "scope_control_reference_invalid")
        require(type(row.get("win")) is bool, "scope_control_outcome_invalid")
        require(row.get("role") in ("MIDDLE", "UTILITY"), "scope_control_role_invalid")
        require(isinstance(row.get("match_id"), str) and row["match_id"],
                "scope_control_match_identity_invalid")
        refs.append(row["evidence_ref"])
        ids.append(row["match_id"])
        for metric in METRICS:
            _number(row[metric])
    require(refs == list(range(1, len(rows) + 1)) and len(ids) == len(set(ids)),
            "scope_control_duplicate_or_unordered_match")
    groups = {}
    for name in COHORTS:
        members = [r for r in rows if name == "selected" or r["role"] == name]
        wins, losses = [r for r in members if r["win"]], [r for r in members if not r["win"]]
        require(wins and losses, "scope_control_outcome_group_empty")
        group = dict(members=[r["evidence_ref"] for r in members],
                     wins=[r["evidence_ref"] for r in wins],
                     losses=[r["evidence_ref"] for r in losses])
        for metric in METRICS:
            w, l = [_number(r[metric]) for r in wins], [_number(r[metric]) for r in losses]
            wm, lm = sum(w) / len(w), sum(l) / len(l)
            pairs = ("greater" if min(w) > max(l) else "less" if max(w) < min(l)
                     else "equal" if len(set(w + l)) == 1 else "overlap")
            group[metric] = dict(win_mean=wm, loss_mean=lm,
                                 mean_direction=_direction(wm, lm), all_pairs=pairs)
        groups[name] = group
    return groups


def _check_derived(expected, actual):
    require(set(expected) == set(COHORTS), "scope_control_cohort_inventory_changed")
    for name, group in actual.items():
        declared = expected[name]
        require(set(declared) == {"members", "wins", "losses", *METRICS},
                "scope_control_derived_fields_changed")
        for field in ("members", "wins", "losses"):
            require(declared[field] == group[field]
                    and all(type(n) is int for n in declared[field]),
                    "scope_control_cohort_members_mismatch")
        for metric in METRICS:
            row, calculated = declared[metric], group[metric]
            loss_fields = ({"loss_mean_exact"} if "loss_mean_exact" in row else
                           {"loss_mean_fraction", "loss_mean_display_2dp"})
            require(set(row) == {"win_mean_exact", "mean_direction", "all_pairs", *loss_fields},
                    "scope_control_derived_fields_changed")
            loss = row.get("loss_mean_exact", row.get("loss_mean_fraction"))
            require(_expected_number(row["win_mean_exact"]) == calculated["win_mean"]
                    and _expected_number(loss) == calculated["loss_mean"],
                    "scope_control_derived_mean_mismatch")
            if "loss_mean_display_2dp" in row:
                require(row["loss_mean_display_2dp"] == _display(calculated["loss_mean"]),
                        "scope_control_rounded_mean_mismatch")
            require(row["mean_direction"] == calculated["mean_direction"]
                    and row["all_pairs"] == calculated["all_pairs"],
                    "scope_control_derived_relation_mismatch")


def _check_case_math(case, actual):
    expected = case["expected"]
    status, metric = expected["target_status"], expected["metric"]
    if status == "supported":
        group = actual[expected["cohort"]]
        relation = {"win_loss_mean": "mean_direction", "all_pairs": "all_pairs"}[expected["operation"]]
        require(expected["relation"] == group[metric][relation], "scope_control_case_relation_mismatch")
        require(expected["required_operand_refs"] == group["members"],
                "scope_control_case_members_mismatch")
    elif "correct_values" in expected:
        group = actual[expected["claimed_cohort"]]
        numbers, row = expected["correct_values"], group[metric]
        require(_expected_number(numbers["win_mean"]) == row["win_mean"]
                and _expected_number(numbers["loss_mean"]) == row["loss_mean"]
                and numbers["relation"] == row["mean_direction"],
                "scope_control_corrected_math_mismatch")
        require(expected["required_operand_refs"] == group["members"],
                "scope_control_case_members_mismatch")
    elif expected.get("decision") == "beyond_sample":
        group = actual[expected["available_observed_cohort"]]
        require(expected["observed_relation"] == group[metric]["all_pairs"]
                and expected["target_cohort"] is None, "scope_control_observed_relation_mismatch")
    elif status == "ambiguous":
        require(expected["cohort"] is None, "scope_control_ambiguity_preselected")
        require([r["cohort"] for r in expected["alternatives"]] == list(COHORTS),
                "scope_control_alternative_inventory_changed")
        # The source-reviewed target says wins > losses. This verifies that
        # analyst-stated arithmetic consequence, not general text entailment.
        for row in expected["alternatives"]:
            direction = actual[row["cohort"]][metric]["mean_direction"]
            require(row["relation"] == direction
                    and row["supports_target"] is (direction == "greater"),
                    "scope_control_alternative_math_mismatch")
    else:
        raise ValueError("scope_control_case_math_unknown")


def validate(data):
    """Validate an in-memory candidate against the independently pinned source."""
    source = load_source()
    require(data["schema_version"] == source["schema_version"], "scope_control_schema_changed")
    for key in ("author", "held_out", "model_evaluated", "standard_id", "status",
                "authority_boundary", "model_input_boundary", "evaluation_boundary"):
        require(_same_json(data[key], source[key]), "scope_control_authority_boundary_changed")
    actual = compute(data["fixture"])
    _check_derived(data["derived_checks"]["cohorts"], actual)
    require(fixture_hash(data["fixture"]) == data["fixture_sha256"] == source["fixture_sha256"],
            "scope_control_fixture_changed")
    require(data["derived_checks"]["host_only"] is True, "scope_control_expected_input_leak")
    cases = data["cases"]
    require([c["id"] for c in cases] == [c["id"] for c in source["cases"]],
            "scope_control_case_inventory_changed")
    for case, original in zip(cases, source["cases"], strict=True):
        require(case["author"] == "analyst" and case["synthetic"] is True,
                "scope_control_case_author_changed")
        require(isinstance(case["target"], str) and case["target"]
                and case["report"].count(case["target"]) == 1, "scope_control_target_not_unique")
        require(sha256(case["report"].encode("utf-8")) == case["report_sha256"]
                == original["report_sha256"] and case["target"] == original["target"],
                "scope_control_report_source_changed")
        for quote in case["expected"].get("scope_evidence", []):
            require(isinstance(quote, str) and quote and case["report"].count(quote) == 1,
                    "scope_control_context_not_unique")
        _check_case_math(case, actual)
        require(_same_json(case, original), "scope_control_analyst_case_changed")
    frozen = data["frozen_dataset_unchanged"]
    require(_same_json(frozen, source["frozen_dataset_unchanged"]), "scope_control_frozen_pointer_changed")
    frozen_path = ROOT / frozen["path"]
    require(sha256(frozen_path.read_bytes()) == frozen["sha256"], "scope_control_old_manifest_changed")
    old_cases = read_json(frozen_path)["cases"]
    require(old_cases[0]["report_sha256"] == frozen["positive_report_sha256"]
            and [r["expected_report"] for r in old_cases]
            == [frozen["positive_expected_report"], frozen["negative_expected_report"]],
            "scope_control_old_labels_changed")
    require(actual["MIDDLE"]["cs_per_min"]["mean_direction"] != actual["selected"]["cs_per_min"]["mean_direction"]
            and actual["MIDDLE"]["gold_per_min"]["all_pairs"] != actual["selected"]["gold_per_min"]["all_pairs"],
            "scope_control_discriminator_lost")
    return dict(status="source_and_arithmetic_consistent", case_count=len(cases),
                source_sha256=SOURCE_SHA256, fixture_sha256=data["fixture_sha256"],
                expected_math={name: {key: ({k: str(v) if isinstance(v, Fraction) else v
                                              for k, v in value.items()}
                                             if isinstance(value, dict) else value)
                                     for key, value in group.items()} for name, group in actual.items()},
                case_ids=[c["id"] for c in cases], original_labels_unchanged=True,
                model_requests_created=0, semantic_labels_validated=False,
                natural_language_entailment_proven=False, model_quality_proven=False,
                limitation="Checks source identity, exact anchors, members and arithmetic; analyst semantic labels still require independent review.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args(argv)
    try:
        result = validate(read_json(args.dataset))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"scope-control check failed: {error}\n")
    result["dataset_file_sha256"] = sha256(args.dataset.read_bytes())
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
