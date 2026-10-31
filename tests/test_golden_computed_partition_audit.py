"""Diagnostic projection is evidence, never an automatic response repair."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.evaluation import golden_partition_review as candidate
from scripts.audit_golden_computed_partition_result import object_projection


def test_positional_projection_preserves_judgments_errors_and_original_values():
    claim = dict(quote_ref=[10, "经济和伤害"], scope_source=[3, "仅指本样本"],
        decision="sample_supported", evidence_refs=[7, 8, 9, 10, 11],
        comparisons=[["selected", "gold_per_min"]], summaries=[],
        explanation="原模型解释，不由本地投影重新判定。", unexpected={"a": 1})
    source = dict(quote_ref=[3], sources=[dict(key="knowledge/K1", path=["knowledge", "citations", 0])],
        literals=[], explanation="保留无效来源路径")
    value = dict(audits=[dict(kind="metric_to_ability", claims=[]),
        dict(kind="cohort_comparison", claims=[claim])], source_checks=[source], issues=[])
    original = deepcopy(value)
    projected, changes = object_projection(value)
    assert value == original
    assert len(changes) == 4
    converted = projected["audits"][1]["claims"][0]
    assert converted["quote_ref"] == dict(block=10, head="经济和伤害")
    assert converted["comparisons"] == [dict(cohort="selected", metric="gold_per_min")]
    for field in ("decision", "evidence_refs", "explanation", "unexpected"):
        assert converted[field] == claim[field]
    assert projected["source_checks"][0]["sources"] == source["sources"]


def test_projection_does_not_guess_malformed_reference_or_operation():
    claim = dict(quote_ref=[1, "a", "b", "extra"], scope_source=[],
        comparisons=[["selected"]], summaries=[["MIDDLE", "cs_per_min", "mean"]])
    value = dict(audits=[dict(claims=[claim])], source_checks=[])
    assert object_projection(value) == (value, [])


def test_actual_failed_entry_is_held_before_any_read_or_request(monkeypatch):
    from scripts import run_golden_integrated_review as runner
    assert candidate.LIVE_STATUS == "offline_only"
    monkeypatch.setattr(runner, "load_inputs", lambda *_: pytest.fail("read inputs"))
    monkeypatch.setattr(runner, "verify_public_ci", lambda *_: pytest.fail("called CI"))
    monkeypatch.setattr(runner, "ReceiptedStreamProvider", lambda **_: pytest.fail("constructed Provider"))
    with pytest.raises(ValueError, match="computed_partition_first_contract_failed"):
        runner.run(SimpleNamespace(execute=True), partition=True)
