from dataclasses import replace
from datetime import timedelta

import pytest

from app.evaluation.golden_source_context import source_context, render_source_context
from app.evaluation.coach_real_data_golden_slice import render_golden_context_report
from app.evidence.summary_bridge import summary_to_evidence
from app.product.coach_positions import position_context
from tests.test_evidence_fusion_vertical import NOW, _meta, _patch, _static
from tests.test_evidence_summary_bridge import summary


def projection(value, *, meta=None, now=NOW):
    return summary_to_evidence(value, routing_region="asia", now=now, observed_at=NOW,
        data_dragon=_static(), official_patch=_patch(), meta_evidence=(meta or _meta(),))


def test_matching_meta_facts_and_version_identities_enter_consumer_with_limits():
    value = summary()
    roles = position_context(value)
    bundle = projection(value).bundle
    context = source_context(bundle, roles)
    assert context["data_dragon"]["catalog_digest"] == "d" * 64
    assert context["official_patch"]["source_digest"] == "e" * 64
    assert context["opgg"][0]["facts"][0]["win_rate"] == 0.53
    assert context["opgg"][0]["allowed_uses"] == ["current_snapshot_recommendation"]
    rendered = render_source_context(bundle, roles)
    assert "不可把该胜率当成玩家胜率" in rendered
    assert "不含改动正文时不可" in rendered


def test_unrelated_positions_champions_and_expired_meta_do_not_supply_facts():
    value = summary()
    roles = position_context(value)
    wrong_lane = replace(_meta(), position="support")
    assert source_context(projection(value, meta=wrong_lane).bundle, roles)["opgg"] == []
    wrong_champion = replace(_meta(), facts=(replace(_meta().facts[0], champion="Anivia"),))
    assert source_context(projection(value, meta=wrong_champion).bundle, roles)["opgg"] == []
    expired = source_context(projection(value, now=NOW + timedelta(hours=1)).bundle, roles)
    assert expired["opgg"] == [] and expired["omitted_opgg"][0]["reason"] == "not_usable_at_execution"


def test_renderer_rejects_different_bundle_identity():
    value = summary()
    with pytest.raises(ValueError, match="identity_mismatch"):
        render_golden_context_report(value, summary_digest="a" * 64, bundle_digest="b" * 64,
                                     roles=position_context(value), bundle=projection(value).bundle)


def test_full_source_context_and_eight_tool_revision_path_fit_existing_total_wall():
    from tests.test_coach_application_composition import dependencies
    from scripts.check_coach_golden_replay import probe
    from app.runtime.coach_contract import GOLDEN_COACH_CONTRACT
    value = dependencies()["summary_builder"].summary
    value["request"].update(data_dragon_version="15.16.1", data_dragon_language="zh_CN")
    for i, row in enumerate(value["matches"]):
        row.update(game_version="15.16.100.1", queue_id=420, champion_id=i + 1)
    meta = replace(_meta(), position="mid", facts=tuple(
        replace(_meta().facts[0], champion=row["champion_name_en"], rank=i + 1) for i, row in enumerate(value["matches"])))
    bundle = projection(value, meta=meta).bundle
    result = probe(value, bundle=bundle)
    assert result["scripted_provider_calls"] == 9 and result["agent"][0]["successful_tool_calls"] == 8
    assert result["terminal_reason"] == "evaluation_failed" and not result["report_available"]
    assert result["coach_contract"]["version"] == "1.3.2"
    assert result["source_bundle_present_by_call"] == [True] * 9
    legacy = probe(value, bundle=bundle, contract=GOLDEN_COACH_CONTRACT)
    assert legacy["source_bundle_present_by_call"] == [True] * 4 + [False] * 5
    limits = GOLDEN_COACH_CONTRACT.descriptor()
    assert max(result["request_input_ceilings"]) <= limits["max_input_tokens"]
    assert sum(result["request_input_ceilings"]) + result["reserved_output_tokens"] <= limits["total_tokens"]


def test_prior_golden_contract_identity_is_frozen_and_new_contract_keeps_resource_walls():
    from app.runtime.coach_contract import GOLDEN_COACH_CONTRACT, SOURCE_COACH_CONTRACT
    assert GOLDEN_COACH_CONTRACT.snapshot().sha256 == "cb2d1293578cadf08e9a302c40c3f67de3210ec7117e8b08a375a280b4a7f5c2"
    old, new = GOLDEN_COACH_CONTRACT.descriptor(), SOURCE_COACH_CONTRACT.descriptor()
    for key in ("max_calls", "max_input_tokens", "max_output_tokens", "total_tokens", "max_tool_calls", "minimum_score", "max_revisions", "max_context_tokens"):
        assert old[key] == new[key]
    assert new["include_deterministic_source_facts"] is True
