"""Opt-in contextual evaluator with one correction, never an implicit default."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

from app.evaluation.golden_context_requests import evaluation_request, patch_request, revision_request, response_contract, POLICY, checked
from app.evaluation.golden_context_review import ContextWire, ContextEvaluation, expand_context, repair_plan, apply_patch
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_review_experiment import SourceIndex
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_evidence_scope_v5 import normalize_json
from app.evaluation.coach_report import EvaluationResponseModelV11, validate_revised_report
from app.evaluation.golden_inference_coverage import CoveredEvaluationResult
from app.providers.structured import decode_structured_response
from app.providers.errors import ProviderResponseError
from app.harness.steps import EvaluationVerdict, CoachDraft

INFERENCE_POLICY_ID = "golden-context-reference-v1"
INFERENCE_POLICY = POLICY
inference_response_contract = response_contract


class _SecurityStop(Exception):
    def __init__(self, payload):
        self.payload = payload


def evaluate(adapter, request):
    from app.evaluation.coach_grounded_contract import _chat_response
    pack = fact_pack(request.player_summary)
    source = SourceIndex.build(request.report, pack)
    args = (request.player_summary, request.deterministic_report, request.knowledge, request.report, request.user_utterance)

    def call(built, step):
        checked(built)
        response = _chat_response(adapter.runtime, system_prompt=built.messages[0].content,
            user_prompt=built.messages[1].content, temperature=adapter.temperature,
            harness_step=step, response_contract=built.response_contract)
        response = replace(response, content=normalize_json(response.content))
        if response.finish_reason in {"length", "max_tokens", "content_filter"}:
            raise ProviderResponseError(provider=response.provider, code="incomplete_context_review")
        try:
            value = strict_json(response.content or "")
            data = {k: value[k] for k in ("score", "verdict", "issues", "passed_checks", "summary")}
            for issue in data["issues"]:
                issue["quote"] = source.resolve(issue.pop("quote_ref"))
            security = EvaluationResponseModelV11.model_validate(data, strict=True)
        except (ValueError, TypeError, KeyError, AttributeError):
            security = None
        if security and any(i.category == "prompt_injection" for i in security.issues):
            raise _SecurityStop(security)
        return response

    def decode(response):
        decoded = decode_structured_response(response=response, contract=response_contract(), output_model=ContextWire,
            validate_context=lambda _: expand_context(response.content, request.report, pack))
        return expand_context(decoded.response.content, request.report, pack)

    try:
        response = call(evaluation_request(*args), "evaluate")
        try:
            payload = decode(response)
        except ProviderResponseError as error:
            if error.code != "invalid_structured_output":
                raise
            try:
                repair_plan(response.content, request.report, pack)
            except (ValueError, TypeError, KeyError, AttributeError):
                # Only a fixed diagnostic code is sent, never exception text
                # that might contain the failed response or model instructions.
                try:
                    expand_context(response.content, request.report, pack)
                except ValueError as invalid:
                    diagnostic = str(invalid) if re.fullmatch(r"[a-z_]{1,100}", str(invalid)) else "invalid_json_or_context_schema"
                payload = decode(call(evaluation_request(*args, failure={"code": diagnostic}), "evaluate_repair"))
            else:
                patched = call(patch_request(response.content, *args), "evaluate_repair")
                try:
                    payload = apply_patch(response.content, patched.content, request.report, pack)
                except (ValueError, TypeError, KeyError, AttributeError):
                    raise ProviderResponseError(provider=response.provider, code="invalid_structured_output") from None
    except _SecurityStop as stop:
        return adapter._result(stop.payload, verdict=EvaluationVerdict.FAIL)
    base = adapter._result(payload)
    result = CoveredEvaluationResult(**base.__dict__, audits=tuple(a.model_dump(mode="json") for a in payload.audits),
        coverage=tuple(c.model_dump(mode="json") for c in payload.coverage))
    if not re.search(r"\[(K\d+)\]", request.report) and result.verdict is not EvaluationVerdict.FAIL:
        issue = {"severity": "medium", "category": "other", "quote": "[missing inline citation]",
            "evidence": "The report contains no [K<number>] citation markers.",
            "explanation": "Retrieved advice must cite the supporting passage.",
            "suggested_correction": "Cite only supplied supporting knowledge or remove unsupported advice."}
        result = replace(result, verdict=EvaluationVerdict.NEEDS_REVISION, issues=(*result.issues, issue))
    return result


def revise(adapter, request):
    from app.evaluation.coach_grounded_contract import _chat_content
    from app.harness.adapters import _evaluation_payload
    canonical = ContextEvaluation.model_validate(_evaluation_payload(request.evaluation), strict=True)
    built = revision_request(request.player_summary, request.deterministic_report, request.knowledge, request.report, canonical)
    content = _chat_content(adapter.runtime, system_prompt=built.messages[0].content,
        user_prompt=built.messages[1].content, temperature=adapter.temperature, harness_step="revise")
    validate_revised_report(content, request.report)
    return CoachDraft(report=content)


def inference_component_fingerprints(skill):
    from app.evaluation.golden_evidence_runtime_v8 import inference_component_fingerprints as previous
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = [r for r in previous(skill) if r.component_id != "evaluation_schema"]
    values = {"evaluation_schema": json.dumps(response_contract().schema_dict(), sort_keys=True)}
    for name in ("golden_review_experiment", "golden_context_review", "golden_context_requests", "golden_context_runtime"):
        values[name] = Path(__file__).with_name(name + ".py").read_text(encoding="utf-8")
    return tuple(rows + [ComponentFingerprint(component_id=k, source="app.evaluation.golden_context_runtime:"+k,
        sha256=hashlib.sha256(v.encode()).hexdigest()) for k, v in values.items()])
