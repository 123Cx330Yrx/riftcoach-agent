import pytest

from app.evaluation.golden_inference_scope_v2 import EvaluationResponseModelV17, validate_scope_v2
from app.evaluation.golden_inference_audit import inference_facts
from tests.test_golden_inference_scope import scope_payload


def anchored_payload():
    value = scope_payload()
    for audit in value["audits"]:
        for claim in audit["claims"]:
            claim["scope_anchor"] = "本次" if "本次" in claim["quote"] else claim["quote"]
    # The existing ambiguity control is intentionally not selected_sample.
    value["audits"][1]["claims"][0]["scope"] = "ambiguous"
    value["audits"][1]["claims"][0]["scope_anchor"] = "stable"
    return value


def test_explicit_local_anchor_is_required_but_stability_word_is_not_banned():
    value = anchored_payload()
    parsed = EvaluationResponseModelV17.model_validate(value)
    validate_scope_v2(parsed, "A stable difference. [K1]", inference_facts({}))


@pytest.mark.parametrize("anchor", ["same role", "losses", "stable"])
def test_selected_sample_without_explicit_scope_anchor_rejected(anchor):
    value = anchored_payload()
    value["audits"][1]["claims"][0].update(scope="selected_sample", scope_anchor=anchor, quote=f"{anchor} stable difference. [K1]")
    value["issues"] = []
    value["verdict"] = "pass"
    with pytest.raises(ValueError, match="selected_sample_scope_anchor_missing"):
        EvaluationResponseModelV17.model_validate(value)


def test_anchor_must_be_literal_text_of_claim():
    value = anchored_payload()
    value["audits"][1]["claims"][0]["scope_anchor"] = "本次"
    with pytest.raises(ValueError, match="scope_anchor_must_be_in_claim_quote"):
        EvaluationResponseModelV17.model_validate(value)


@pytest.mark.parametrize("anchor", ["这四场", "本次", "所选", "4局", "n=4"])
def test_chinese_explicit_sample_claim_can_pass(anchor):
    value = anchored_payload()
    value.update(verdict="pass", issues=[])
    value["coverage"][0]["scope_ambiguous"] = False
    value["audits"][1]["claims"][0].update(
        scope="selected_sample", scope_anchor=anchor,
        quote=f"{anchor}方向稳定。", status="supported")
    EvaluationResponseModelV17.model_validate(value)


def test_original_missed_phrase_cannot_use_loss_group_as_sample_anchor():
    value = anchored_payload()
    value.update(verdict="pass", issues=[])
    value["coverage"][0]["scope_ambiguous"] = False
    value["audits"][1]["claims"][0].update(
        scope="selected_sample", scope_anchor="输局",
        quote="输局的稳定同位置差距", status="supported")
    with pytest.raises(ValueError, match="selected_sample_scope_anchor_missing"):
        EvaluationResponseModelV17.model_validate(value)


def test_new_scope_v2_assets_resolve():
    from pathlib import Path
    from app.skills.catalog import SkillCatalog
    from app.prompt_program.catalog import PromptProgramCatalog
    from app.prompt_program.resolver import PromptProgramResolver
    from app.runtime.coach_contract import SCOPE_V2_COACH_CONTRACT
    root = Path("examples/runtime_profiles/flash_v2_golden_scope_v2")
    resolver = PromptProgramResolver(PromptProgramCatalog.from_directory(root / "prompt_programs"), SkillCatalog.from_directory(root / "skills"), coach_contract=SCOPE_V2_COACH_CONTRACT)
    assert resolver.verify_all()[0].evaluation_contract_version == "1.7.0"
