import json
from types import SimpleNamespace as NS

import pytest

from app.providers.errors import ProviderResponseError, ProviderTimeoutError
from scripts.run_golden_scope_controls import embed, evaluate_pair, score, totals, case_progress, PAIRS


def result(verdict="pass", score=96, issues=(), claims=()):
    return NS(verdict=NS(value=verdict), score=score, issues=issues,
              passed_checks=(), summary="checked", audits=({"kind": "cohort_comparison", "status": "supported", "claims": claims},), coverage=())


def test_full_quote_with_context_detects_target_but_unrelated_issue_does_not():
    case = {"id": "long_term", "claim": "这四场已经证明他长期在输局中输出不足。", "expected": "reject"}
    quote = case["claim"]
    claim = dict(quote=quote, status="unsupported", scope="beyond_sample")
    issue = dict(quote=quote, category="other")
    assert score(case, result("needs_revision", 70, (issue,), (claim,)))["matched"]
    other = dict(quote="另一个完全无关的问题", status="unsupported", scope="beyond_sample")
    assert not score(case, result("needs_revision", 70, ({"quote": other["quote"], "category": "other"},), (other,)))["matched"]
    full = dict(claim, quote="附加观察："+quote)
    assert score(case, result("needs_revision", 70, (dict(issue, quote=full["quote"]),), (full,)))["matched"]


def test_clarify_requires_ambiguous_and_exact_other_issue():
    case = {"id": "ambiguous", "claim": "经济和伤害是可靠的胜负区分指标。", "expected": "clarify"}
    claim = dict(quote=case["claim"], status="unsupported", scope="beyond_sample")
    issue = dict(quote=case["claim"], category="other")
    assert not score(case, result("needs_revision", 70, (issue,), (claim,)))["matched"]
    claim["scope"] = "ambiguous"
    assert score(case, result("needs_revision", 70, (issue,), (claim,)))["matched"]
    assert not score(case, result("needs_revision", 70, (dict(issue, category="fact_error"),), (claim,)))["matched"]


def test_invalid_is_not_a_false_positive_or_false_negative():
    selected = [{"expected": "accept"}, {"expected": "reject"}, {"expected": "clarify"}]
    rows = [dict(expected="accept", valid=False, matched=False), dict(expected="reject", valid=True, matched=False)]
    value = totals(rows, selected)
    assert value["invalid"] == 1 and not value["all_valid"] and not value["all_attempted"]
    assert value["groups"]["accept"]["mismatched"] == 0
    assert value["groups"]["reject"]["mismatched"] == 1
    assert value["groups"]["clarify"]["valid"] == 0


def test_independent_cases_continue_after_invalid_and_never_send_labels(tmp_path):
    cases = [dict(id="a", claim="待测甲", expected="accept", rationale="SECRET_ORACLE"),
             dict(id="b", claim="待测乙", expected="accept", rationale="SECRET_ORACLE")]
    requests = []
    state = {"calls": 0}
    class Fake:
        def evaluate(self, request):
            requests.append(request)
            state["calls"] += 2 if len(requests) == 1 else 1
            assert "SECRET_ORACLE" not in str(request)
            if len(requests) == 1:
                raise ProviderResponseError(provider="test", code="invalid_structured_output")
            return result()
    rows = evaluate_pair(cases, Fake(), {}, "facts", None, "## 3. 主要风险点\n", tmp_path, state)
    assert [r["valid"] for r in rows] == [False, True]
    assert rows[1]["first_call"] == 3
    assert "待测甲" not in requests[1].report
    assert not (tmp_path / "a-evaluation.json").exists()
    assert (tmp_path / "b-evaluation.json").exists()


def test_transport_failure_stops_remaining_cases(tmp_path):
    class Fake:
        def evaluate(self, request):
            raise ProviderTimeoutError(provider="test", code="timeout")
    cases = [dict(id="a", claim="待测甲", expected="accept"), dict(id="b", claim="待测乙", expected="reject")]
    with pytest.raises(ProviderTimeoutError):
        evaluate_pair(cases, Fake(), {}, "facts", None, "## 3. 主要风险点\n", tmp_path, {"calls": 0})
    assert not (tmp_path / "b-input.json").exists()
    started = [p.stem.removesuffix("-input") for p in tmp_path.glob("*-input.json")]
    assert case_progress(cases, started, []) == dict(planned=2, started=1, finalized=0, interrupted=1, not_started=1)


def test_progress_keeps_completed_results_when_next_case_is_interrupted():
    selected = [dict(id=str(i)) for i in range(12)]
    assert case_progress(selected, [str(i) for i in range(7)], [dict(id=str(i)) for i in range(6)]) == dict(
        planned=12, started=7, finalized=6, interrupted=1, not_started=5)
    with pytest.raises(ValueError, match="identity"):
        case_progress(selected, ["0", "0"], [])
    with pytest.raises(ValueError, match="identity"):
        case_progress(selected, ["0"], [dict(id="1")])


def test_pair_inventory_covers_frozen_dataset_once():
    from scripts.check_golden_stability_calibration import DATASET
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    ids = [key for pair in PAIRS for key in pair]
    assert len(ids) == len(set(ids)) == 12
    assert set(ids) == {c["id"] for c in cases}
    assert embed("## 3. 主要风险点\n\n原文", "## 持续存在的输出差距").count("## 持续存在的输出差距") == 1
