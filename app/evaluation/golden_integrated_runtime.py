"""Unified review/revision prototype using a receipt-bearing transport boundary.

Independent candidate wiring is explicit; historical Coach registrations and
defaults are unchanged. No retries beyond discovery + assessment are hidden here.
"""
from dataclasses import dataclass, replace
import hashlib
import re

from app.evaluation import golden_integrated_review as review
from app.evaluation.golden_context_requests import revision_request
from app.evaluation.golden_context_review import ContextEvaluation
from app.evaluation.golden_review_experiment import compact
from app.evaluation.golden_stream_bridge import validate_request, CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID, GoldenProcessStreamProvider
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.coach_report import validate_revised_report, EvaluationResponseModelV11
from app.evaluation.golden_inference_coverage import CoveredEvaluationResult
from app.harness.adapters import _evaluation_payload
from app.harness.steps import CoachDraft, EvaluationVerdict
from app.providers.errors import ProviderResponseError
from app.providers.models import ChatRequest, ChatResponse


@dataclass(frozen=True)
class Exchange:
    issued_request: ChatRequest
    response: ChatResponse
    receipt_request_sha256: str


def validate_exchange(prepared, exchange):
    issued = exchange.issued_request
    if (issued.messages != prepared.messages or issued.response_contract != prepared.response_contract
            or issued.tools != prepared.tools or issued.tool_choice != prepared.tool_choice):
        raise ValueError("integrated_issued_input_mismatch")
    sha = hashlib.sha256(validate_request(issued, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
    if sha != exchange.receipt_request_sha256:
        raise ValueError("integrated_receipt_mismatch")
    if exchange.response.finish_reason != "stop" or exchange.response.tool_calls:
        raise ValueError("integrated_incomplete_response")
    return exchange.response.content


class ReceiptedStreamProvider(GoldenProcessStreamProvider):
    """Obtain identity from our stream reservation, never from model content."""
    last_exchange = None

    def chat(self, request):
        self.last_exchange = None
        response = super().chat(request)
        directory = self._directory / f"stream-{self._calls:03d}"
        reservation = strict_json((directory / "reservation.json").read_text(encoding="utf-8"))
        terminal = strict_json((directory / "result.json").read_text(encoding="utf-8"))
        sha = hashlib.sha256(validate_request(request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest()
        if (self.transport_id not in (CAPACITY_TRANSPORT_ID, REVIEW_MODEL_TRANSPORT_ID) or reservation["transport_id"] != self.transport_id
                or reservation["ordinal"] != self._calls or reservation["request_sha256"] != sha
                or terminal["state"] != "complete" or terminal["transport_id"] != self.transport_id):
            self._failed = True
            raise ProviderResponseError(provider=self.provider_name, code="integrated_transport_receipt_invalid")
        self.last_exchange = Exchange(request, response, sha)
        return response


class BudgetedReviewSender:
    """Budget transforms request first; transport then records exact issued bytes."""
    def __init__(self, provider, *, clock=None):
        from app.runtime.coach_budget import CoachBudgetedProvider
        from app.runtime.coach_contract import CONTEXT_COACH_CONTRACT
        self.provider = provider
        self.budget = CoachBudgetedProvider(provider, coach_contract=CONTEXT_COACH_CONTRACT,
            **({"clock": clock} if clock else {}))

    def __call__(self, request):
        previous = self.provider.last_exchange
        response = self.budget.chat(request)
        exchange = self.provider.last_exchange
        if exchange is None or exchange is previous or exchange.response is not response:
            raise ValueError("integrated_fresh_transport_receipt_required")
        return exchange


def _result(payload):
    from app.evaluation.coach_grounded_contract import GroundedChatEvaluationAdapter
    base = GroundedChatEvaluationAdapter._result(payload)
    if isinstance(payload, ContextEvaluation):
        return CoveredEvaluationResult(**base.__dict__, audits=tuple(a.model_dump(mode="json") for a in payload.audits),
            coverage=tuple(c.model_dump(mode="json") for c in payload.coverage))
    return base


class IntegratedReviewWorkflow:
    """Serial, one-report scope: 2 evaluations, one revision, at most five calls."""
    build_inputs = staticmethod(review.ReviewInput.build)
    def __init__(self, send, *, record=None):
        self.send = send
        self.record = record or (lambda *_: None)
        self.calls = self.evaluations = self.revisions = 0
        self.stopped = False
        self.last_feedback = None
        self._accepted = None
        self._expected_recheck = None

    def _call(self, request, phase):
        if self.stopped or self.calls >= 5:
            raise ValueError("integrated_call_budget_exhausted")
        review.checked(request)
        self.calls += 1
        try:
            exchange = self.send(request)
            self.record(phase, exchange)
            raw = validate_exchange(request, exchange)
            return raw
        except BaseException:
            self.stopped = True
            raise

    def evaluate(self, request):
        if self.stopped or self.evaluations >= 2 or (self.evaluations == 1 and self.revisions != 1):
            raise ValueError("integrated_evaluation_order_invalid")
        inputs = self.build_inputs(request)
        if self.evaluations == 1 and inputs != self._expected_recheck:
            raise ValueError("integrated_recheck_source_changed")
        self.evaluations += 1
        raw = self._call(review.discovery_request(inputs), "discovery")
        # A valid security finding is terminal even if discovery's unrelated
        # coverage fields are malformed. Never spend another call clearing it.
        security = []
        try:
            candidates = strict_json(raw).get("security_issues", [])
            for candidate in candidates:
                issue = review.IssueRef.model_validate(candidate, strict=True)
                inputs.source.resolve(issue.quote_ref.model_dump())
                if issue.category == "prompt_injection" and issue.severity == "high":
                    security.append(issue)
        except (ValueError, TypeError, AttributeError):
            pass
        if security:
            payload = EvaluationResponseModelV11(score=0, verdict="fail", passed_checks=[],
                summary="报告包含提示注入，停止自动修订。", issues=[dict(i.model_dump(exclude={"quote_ref"}),
                    quote=inputs.source.resolve(i.quote_ref.model_dump())) for i in security])
            self.stopped = True
            return _result(payload)
        try:
            targets, security = review.discover(raw, inputs)
        except (ValueError, TypeError) as error:
            # The remaining call judges every complete block and can split out
            # missed assertions through additions. No source block disappears.
            targets = tuple({"block": i} for i in range(1, len(inputs.source.blocks)+1))
            security = []
            feedback = review.discovery_feedback(error)
        else:
            feedback = None
        raw = self._call(review.assessment_request(inputs, targets, feedback=feedback), "assessment")
        try:
            payload = review.assessment_result(raw, inputs, targets)
        except (ValueError, TypeError):
            self.last_feedback = review.assessment_feedback(raw, inputs, targets)
            self.stopped = True
            raise ProviderResponseError(provider="zhipu", code="invalid_structured_output") from None
        result = _result(payload)
        if any(i["category"] == "prompt_injection" for i in result.issues):
            result = replace(result, verdict=EvaluationVerdict.FAIL)
        if result.verdict is EvaluationVerdict.FAIL:
            self.stopped = True
        if not re.search(r"\[K\d+\]", request.report) and result.verdict is not EvaluationVerdict.FAIL:
            result = replace(result, verdict=EvaluationVerdict.NEEDS_REVISION, issues=(*result.issues, dict(
                severity="medium", category="other", quote="[missing inline citation]", evidence="没有知识引用标记。",
                explanation="建议必须由所给知识支持。", suggested_correction="核对实际支持的知识并引用，或删除无依据建议。")))
        self._accepted = (inputs, result)
        return result

    def revise(self, request):
        if (self.stopped or self.revisions or self.evaluations != 1 or self._accepted is None
                or request.evaluation is not self._accepted[1]
                or request.evaluation.verdict is not EvaluationVerdict.NEEDS_REVISION):
            raise ValueError("integrated_revision_order_invalid")
        from app.harness.steps import EvaluationRequest
        original = self._accepted[0]
        # Bind revision to the same facts, evidence and report as its evaluation.
        check = self.build_inputs(EvaluationRequest(request.player_summary, request.deterministic_report,
            request.knowledge, request.report, strict_json(original.data_json)["user_utterance"]))
        if check != original:
            raise ValueError("integrated_revision_source_changed")
        canonical = ContextEvaluation.model_validate(_evaluation_payload(request.evaluation), strict=True)
        built = self.build_revision(request, canonical, original)
        self.revisions += 1
        raw = self._call(built, "revision")
        try:
            validate_revised_report(raw, request.report)
        except Exception:
            self.stopped = True
            raise
        self._expected_recheck = self.build_inputs(EvaluationRequest(request.player_summary,
            request.deterministic_report, request.knowledge, raw, strict_json(original.data_json)["user_utterance"]))
        return CoachDraft(report=raw)

    def build_revision(self, request, canonical, inputs):
        return revision_request(request.player_summary, request.deterministic_report, request.knowledge,
            request.report, canonical)
