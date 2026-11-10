import pytest

from app.evaluation.golden_inference_scope import EvaluationResponseModelV16, validate_scope
from app.evaluation.golden_inference_audit import inference_facts
from tests.test_golden_inference_coverage import covered_payload

REPORT = "A stable difference. [K1]"


def scope_payload():
    p = covered_payload(REPORT)
    p.update(verdict="needs_revision", issues=[dict(severity="medium", category="other",
        quote=REPORT, evidence="Only selected rows", explanation="Scope unclear",
        suggested_correction="State the selected four games explicitly")])
    p["audits"][1].update(status="supported", claims=[dict(quote=REPORT, status="supported",
        scope="ambiguous", evidence_refs=["scope:limits"], explanation="Scope unclear")])
    p["coverage"][0].update(cohort_comparison="supported", scope_ambiguous=True)
    return p


def test_ambiguity_requires_clarification_without_fabricating_false_arithmetic():
    p = EvaluationResponseModelV16.model_validate(scope_payload())
    validate_scope(p, REPORT, inference_facts({}))
    assert p.audits[1].claims[0].status == "supported"
    assert p.verdict == "needs_revision"


@pytest.mark.parametrize("mutation", ["pass", "issue_quote", "issue_category", "missing_scope", "missing_block_scope", "hidden_ambiguity"])
def test_scope_cannot_be_dropped_or_pass_with_unresolved_issue(mutation):
    p = scope_payload()
    if mutation == "pass": p.update(verdict="pass", issues=[])
    elif mutation == "issue_quote": p["issues"][0]["quote"] = "other"
    elif mutation == "issue_category": p["issues"][0]["category"] = "factual_error"
    elif mutation == "missing_scope": p["audits"][1]["claims"][0].pop("scope")
    elif mutation == "missing_block_scope": p["coverage"][0].pop("scope_ambiguous")
    else: p["coverage"][0]["scope_ambiguous"] = False
    with pytest.raises(ValueError):
        validate_scope(EvaluationResponseModelV16.model_validate(p), REPORT, inference_facts({}))


def test_explicit_sample_scope_can_pass_and_survives_revision_projection():
    from app.evaluation.golden_inference_coverage import CoveredEvaluationResult
    from app.harness.adapters import _evaluation_payload
    from app.harness.steps import EvaluationVerdict
    p = scope_payload()
    p.update(verdict="pass", issues=[])
    p["audits"][1]["claims"][0]["scope"] = "selected_sample"
    p["coverage"][0]["scope_ambiguous"] = False
    parsed = EvaluationResponseModelV16.model_validate(p)
    validate_scope(parsed, REPORT, inference_facts({}))
    # Structural validation cannot discover an incorrect semantic label.
    result = CoveredEvaluationResult(score=95, verdict=EvaluationVerdict.PASS, issues=(),
        passed_checks=(), summary="mock", audits=tuple(a.model_dump() for a in parsed.audits),
        coverage=tuple(c.model_dump() for c in parsed.coverage))
    assert _evaluation_payload(result)["audits"][1]["claims"][0]["scope"] == "selected_sample"


def test_new_assets_resolve_and_frozen_coverage_identity_is_unchanged():
    from pathlib import Path
    from app.skills.catalog import SkillCatalog
    from app.prompt_program.catalog import PromptProgramCatalog
    from app.prompt_program.resolver import PromptProgramResolver
    from app.runtime.coach_contract import COVERAGE_COACH_CONTRACT, SCOPE_COACH_CONTRACT, coach_component_fingerprint
    assert coach_component_fingerprint(COVERAGE_COACH_CONTRACT).sha256 == "c9a0505dd134c80e157fa5eb611d2160fa0078f0ac8300246dd349da5348e385"
    root = Path("examples/runtime_profiles/flash_v2_golden_scope")
    resolver = PromptProgramResolver(PromptProgramCatalog.from_directory(root / "prompt_programs"),
        SkillCatalog.from_directory(root / "skills"), coach_contract=SCOPE_COACH_CONTRACT)
    assert resolver.verify_all()[0].evaluation_contract_version == "1.6.0"
