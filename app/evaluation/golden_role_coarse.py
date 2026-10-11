"""Explicit coarse-source workflow on the existing revision state machine.

Not registered as a product candidate. Historical workflows retain their own
source resolver; no response IDs are translated, repaired or widened here.
"""
import re

from app.evaluation.coach_grounded_contract import EvaluationResponseModelV12
from app.evaluation import golden_coarse_source_projection as coarse
from app.evaluation import golden_native_issues_review as native
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReview, RoleClarityReviewWorkflow
from app.providers.errors import ProviderResponseError

CONTRACT_ID = "golden-role-coarse-workflow-v1"


class RoleCoarseReviewWorkflow(RoleClarityReviewWorkflow):
    make_request = staticmethod(coarse.project_request)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        value, suffix = native.previous.provisional_review(raw)
        if native.previous.security_terminal(value):
            raise ValueError("native_security_terminal")
        if suffix:
            raise ProviderResponseError(provider="zhipu", code="native_review_non_json_suffix")
        wire = RoleClarityReview.model_validate(value, strict=True)
        payload, journal = validate_sources(wire, inputs, previous_raw)
        markers, seen = [], set()
        for marker in wire.advisories:
            if marker.block > len(inputs.source.blocks):
                raise ValueError("native_advisory_block_unknown")
            if marker.block in seen:
                raise ValueError("native_advisory_block_duplicate")
            seen.add(marker.block)
            markers.append(dict(block=marker.block, quote=inputs.source.blocks[marker.block-1][1]))
        request = coarse.project_request(inputs, previous_raw=previous_raw)
        return payload, wire, dict(journal, experiment=CONTRACT_ID,
            validator_experiment=CONTRACT_ID,
            policy_sha256=digest(request.messages[0].content),
            source_projection=coarse.VERSION,
            source_catalog_sha256=coarse.source_catalog(inputs)["catalog_sha256"],
            raw=raw, raw_sha256=digest(raw), parsed_review=wire.model_dump(mode="json"),
            advisories=markers, raw_representation="tool_arguments_projection")


def validate_sources(wire, inputs, previous_raw):
    """Validate this contract's IDs directly, never relabel a legacy journal."""
    before = native.previous.provisional_review(previous_raw)[0] if previous_raw is not None else None
    if native.previous.security_terminal(before):
        raise ValueError("native_security_terminal")
    issues, selected = [], []
    for number, issue in enumerate(wire.issues, 1):
        if issue.block > len(inputs.source.blocks):
            raise ValueError("native_issue_block_unknown")
        if issue.category == "prompt_injection":
            raise ValueError("native_security_terminal")
        refs = coarse.resolve_refs(inputs, issue.source_ids)
        selected.append(dict(block=issue.block, issue=number, selected_sources=refs))
        issues.append(dict(issue.model_dump(exclude={"source_ids", "block"}),
            quote=inputs.source.blocks[issue.block-1][1],
            evidence="问题所选来源编号：" + compact(issue.source_ids) + "。" + issue.explanation))
    prior = native.prior_issues(before) if before is not None else []
    if sorted(r.previous_id for r in wire.issue_resolutions) != list(range(1, len(prior)+1)):
        raise ValueError("native_issue_resolution_inventory")
    for resolution in wire.issue_resolutions:
        coarse.resolve_refs(inputs, resolution.source_ids)
        if resolution.disposition == "withdrawn":
            if resolution.final_issue is not None:
                raise ValueError("native_withdrawal_has_final_issue")
        elif resolution.final_issue is None or not 1 <= resolution.final_issue <= len(wire.issues):
            raise ValueError("native_resolution_target_missing")
    summary = {"pass": "模型未发现需要修订的问题。",
        "needs_revision": f"模型提出 {len(issues)} 项问题，需要修订后复评。",
        "fail": "模型评估未通过，停止自动修订。"}[wire.verdict]
    payload = EvaluationResponseModelV12.model_validate(dict(score=wire.score,
        verdict=wire.verdict, summary=summary, passed_checks=[], issues=issues), strict=True)
    available = {entry["citation_id"] for entry in native.strict_json(inputs.data_json)["knowledge"]["citations"]}
    cited = set(re.findall(r"\[(K\d+)\]", inputs.source.report))
    if payload.verdict == "pass":
        if cited - available:
            raise ValueError("native_unknown_knowledge_citation_unreported")
        if available and not cited:
            raise ValueError("native_missing_knowledge_citation_unreported")
    return payload, dict(previous_raw=previous_raw, previous_issues=prior,
        resolutions=[r.model_dump() for r in wire.issue_resolutions],
        input_sha256=digest(inputs.data_json), report_sha256=digest(inputs.source.report),
        selected_sources=selected, semantic_approval=False, production_admitted=False)
