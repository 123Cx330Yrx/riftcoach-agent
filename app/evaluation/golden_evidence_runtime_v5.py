"""Explicit, unadmitted fact/operations evaluator; historical paths stay frozen."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

from app.evaluation.golden_evidence_requests_v5 import evaluation_request, revision_request, POLICY
from app.evaluation.golden_evidence_scope_v5 import EvidenceWire, EvidenceEvaluation, expand_evidence, normalize_json
from app.evaluation.golden_fact_candidate import fact_pack
from app.evaluation.golden_evidence_scope_v5 import collect_diagnostics
from app.providers.structured import contract_for_model, decode_structured_response
from app.evaluation.coach_report import EvaluationResponseModelV11, validate_revised_report
from app.evaluation.golden_inference_coverage import CoveredEvaluationResult
from app.harness.steps import EvaluationVerdict, CoachDraft
from app.evaluation.glm53_bounded_revision_budget_reachability import estimate_runtime_request_input_ceiling

INFERENCE_POLICY_ID = "golden-evidence-scope-v5"
INFERENCE_POLICY = POLICY


def inference_response_contract():
    return contract_for_model(name="coach_evaluation", version="1.16.0", output_model=EvidenceWire)


def issued_request(request):
    """Promote the already measured builder, changing only the policy identity."""
    messages = tuple(replace(m, content=m.content.replace(POLICY, INFERENCE_POLICY, 1)) for m in request.messages)
    request = replace(request, messages=messages,
                      response_contract=inference_response_contract() if request.response_contract else None)
    if estimate_runtime_request_input_ceiling(request) > 64000:
        raise ValueError("fact_request_input_budget_exceeded")
    return request


class _SecurityStop(Exception):
    def __init__(self, payload):
        self.payload = payload


def evaluate(adapter, request):
    from app.evaluation.coach_grounded_contract import _chat_response
    pack = fact_pack(request.player_summary)
    args = (request.player_summary, request.deterministic_report, request.knowledge, request.report, request.user_utterance)
    latest = None

    def call(built, step):
        nonlocal latest
        built = issued_request(built)
        latest = _chat_response(adapter.runtime, system_prompt=built.messages[0].content,
            user_prompt=built.messages[1].content, temperature=adapter.temperature,
            harness_step=step, response_contract=built.response_contract)
        latest = replace(latest, content=normalize_json(latest.content))
        try:
            data = json.loads(latest.content or "")
            if isinstance(data, dict):
                data.pop("audits", None)
                data.pop("coverage", None)
                data.pop("reviewed_blocks", None)
            security = EvaluationResponseModelV11.model_validate(data, strict=True)
        except (ValueError, TypeError):
            security = None
        if security and any(i.category == "prompt_injection" for i in security.issues):
            raise _SecurityStop(security)
        return latest

    try:
        response = call(evaluation_request(*args), "evaluate")

        def repair(failure):
            errors = collect_diagnostics(failure.invalid_content, request.report, pack)
            return call(evaluation_request(*args, diagnostics=errors), "evaluate_repair")

        decoded = decode_structured_response(response=response, contract=inference_response_contract(),
            output_model=EvidenceWire, repair=repair,
            validate_context=lambda _: expand_evidence(latest.content, request.report, pack))
    except _SecurityStop as stop:
        return adapter._result(stop.payload, verdict=EvaluationVerdict.FAIL)
    payload = expand_evidence(decoded.response.content, request.report, pack)
    base = adapter._result(payload)
    result = CoveredEvaluationResult(**base.__dict__, audits=tuple(a.model_dump(mode="json") for a in payload.audits),
                                     coverage=tuple(c.model_dump(mode="json") for c in payload.coverage))
    if not re.search(r"\[(K\d+)\]", request.report) and result.verdict is not EvaluationVerdict.FAIL:
        issue = {"severity": "medium", "category": "other", "quote": "[missing inline citation]",
                 "evidence": "The report contains no [K<number>] citation markers.",
                 "explanation": "Retrieved advice must cite the supporting passage.",
                 "suggested_correction": "Use only supplied knowledge that supports the advice; cite its actual ID or remove unsupported advice."}
        result = replace(result, verdict=EvaluationVerdict.NEEDS_REVISION, issues=(*result.issues, issue))
    return result


def revise(adapter, request):
    from app.evaluation.coach_grounded_contract import _chat_content
    from app.harness.adapters import _evaluation_payload
    canonical = EvidenceEvaluation.model_validate(_evaluation_payload(request.evaluation))
    built = issued_request(revision_request(request.player_summary, request.deterministic_report,
        request.knowledge, request.report, canonical))
    content = _chat_content(adapter.runtime, system_prompt=built.messages[0].content,
        user_prompt=built.messages[1].content, temperature=adapter.temperature, harness_step="revise")
    validate_revised_report(content, request.report)
    return CoachDraft(report=content)


def inference_component_fingerprints(skill):
    from app.evaluation.golden_inference_scope_v5 import inference_component_fingerprints as old_fingerprints
    from app.evaluation.prompt_context_identity import ComponentFingerprint
    rows = [r for r in old_fingerprints(skill) if r.component_id != "evaluation_schema"]
    values = {"evaluation_schema": json.dumps(inference_response_contract().schema_dict(), sort_keys=True)}
    for name in ("golden_fact_candidate", "golden_numeric_evidence_v2", "golden_numeric_evidence_v3", "golden_numeric_evidence_v4", "golden_evidence_scope_v3", "golden_evidence_scope_v5", "golden_evidence_requests_v5", "golden_scope_diagnostics", "golden_evidence_runtime_v5"):
        values[name] = Path(__file__).with_name(name + ".py").read_text(encoding="utf-8")
    for key, value in values.items():
        rows.append(ComponentFingerprint(component_id=key, source="app.evaluation.golden_evidence_runtime_v5:" + key,
                                         sha256=hashlib.sha256(value.encode()).hexdigest()))
    return tuple(rows)
