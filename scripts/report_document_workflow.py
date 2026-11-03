"""Unregistered document-view workflow for offline composition tests.

Uses the existing review/edit/fresh state machine. No provider factory, default
router change, paid runner, or semantic qualification is supplied here.
"""
from dataclasses import replace
import hashlib

from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.golden_native_tool_review import tool_result
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_role_boundary_examples import review_policy
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.source_patch_editor import report_inputs
from scripts import report_document_view as view

VERSION = 'offline-report-document-workflow-v1'


def request_sha(request):
    return hashlib.sha256(validate_request(request, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest()


class DocumentReviewWorkflow(editor.ReviewBoundRevisionWorkflow):
    request_sha = staticmethod(request_sha)
    check_request = staticmethod(budget_check)
    tool_result = staticmethod(tool_result)
    @staticmethod
    def make_request(inputs, **kwargs):
        if kwargs.get('accepted') is not None:
            return editor.ReviewBoundRevisionWorkflow.make_request(inputs, **kwargs)
        return view.project(inputs, **kwargs)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = editor.Current.validate_review(raw, inputs, previous_raw=previous_raw)
        policy = review_policy(previous_raw)
        if policy.count(view.ADDRESS) != 1:
            raise ValueError('document_view_policy_changed')
        return payload, wire, dict(journal, experiment=VERSION,
            report_presentation=view.VERSION,
            base_validator_experiment=journal['validator_experiment'],
            base_policy_sha256=journal['policy_sha256'],
            policy_sha256=digest(policy.replace(view.ADDRESS, view.DOCUMENT_ADDRESS)))

    def _call(self, prepared, phase):
        if phase == 'native_business_revision':
            report = super()._call(prepared, phase)
            # The existing editor's journal describes its baseline preview.
            # Keep that provenance and bind this workflow's actual fresh plan.
            final = self.make_request(report_inputs(self._accepted[0], report))
            self.last_edit_journal = dict(self.last_edit_journal,
                workflow=VERSION, final_report_presentation=view.VERSION,
                baseline_final_review_request_sha256=self.last_edit_journal['final_review_request_sha256'],
                final_review_request_sha256=self.request_sha(final))
            return report
        if self.stopped or self.calls >= 5:
            raise ValueError('integrated_call_budget_exhausted')
        self.check_request(prepared)
        self.calls += 1
        try:
            exchange = self.send(prepared)
            self.record(phase, exchange)  # Retain even an invalid issued request.
            issued = exchange.issued_request
            metadata = dict(issued.metadata)
            marker = metadata.pop('coach_budget_contract', None)
            if (marker not in (None, 'coach-bounded-review-v2')
                    or not 0 < issued.timeout_s <= prepared.timeout_s
                    or replace(issued, timeout_s=prepared.timeout_s, metadata=metadata) != prepared
                    or (exchange.response.provider, exchange.response.model) != ('zhipu', 'glm-5.3')):
                raise ValueError('document_view_exchange_identity')
            raw = self.tool_result(prepared, exchange)
            self._review_binding = dict(prepared_request_sha256=self.request_sha(prepared),
                issued_request_sha256=self.request_sha(issued),
                receipt_request_sha256=exchange.receipt_request_sha256)
            self._evaluation_bindings.append(dict(phase=phase, **self._review_binding))
            return raw
        except BaseException:
            self.stopped = True
            raise

    def evaluate(self, request):
        previous_evaluations = self.evaluations
        previous_bindings = getattr(self, '_evaluation_bindings', [])
        self._evaluation_bindings = []
        try:
            result = super().evaluate(request)
        except BaseException:
            if self.evaluations == previous_evaluations:
                # A rejected re-entry must not erase the completed/failed
                # evaluation's audit trail when no new evaluation began.
                self._evaluation_bindings = previous_bindings
            elif self.evaluations == 2 and self.last_edit_journal is not None:
                self.last_edit_journal = dict(self.last_edit_journal,
                    final_review_attempts=list(self._evaluation_bindings))
            raise
        self.last_journal = dict(self.last_journal, **self._review_binding,
            evaluation_requests=list(self._evaluation_bindings))
        if self.evaluations == 2:
            first = self._evaluation_bindings[0]
            if self.last_edit_journal['final_review_request_sha256'] != first['prepared_request_sha256']:
                self.stopped = True
                raise ValueError('document_view_fresh_plan_changed')
            self.last_edit_journal = dict(self.last_edit_journal,
                final_review_attempts=list(self._evaluation_bindings),
                final_review_result_binding=dict(self._review_binding, verdict=result.verdict.value),
                final_review_issued_request_sha256=first['issued_request_sha256'],
                final_review_receipt_request_sha256=first['receipt_request_sha256'])
        return result
