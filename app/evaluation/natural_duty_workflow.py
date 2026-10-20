"""Automatic candidate path; two complete duties never certify Host semantics.

Even a successful candidate chain returns FAIL to the existing publication
Harness. A future qualified product adapter requires a separate decision.
"""
from dataclasses import asdict, replace
from pathlib import Path

from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.source_patch_editor import report_inputs
from app.harness.steps import CoachDraft, EvaluationResult, EvaluationVerdict
from app.providers.errors import ProviderResponseError
from scripts import review_duty_direct_patch as direct, review_duty_composition as duty
from .natural_duty_contract import VERSION, make_request, request_sha


class NaturalDutySuspended(BaseException):
    """An execution boundary pause must not become a business rejection."""


class NaturalDutyWorkflow:
    def __init__(self, send, *, journal_root, contract_module=None):
        from app.evaluation import natural_duty_contract
        self.contract_module = contract_module or natural_duty_contract
        self.send, self.journal_root = send, Path(journal_root)
        self.state = 'initial'
        self.outcome = None
        self.entries = []
        self.original = self.expected_fresh = self.initial_result = self.assembly = None

    def record(self, name, data):
        self.journal_root.mkdir(parents=True, exist_ok=True)
        write_new_json(self.journal_root / (name+'.json'), data)

    def stop(self, outcome):
        if self.state == 'terminal':
            raise ValueError('natural_duty_already_terminal')
        self.state, self.outcome = 'terminal', outcome
        self.record('outcome', dict(version=self.contract_module.VERSION, outcome=outcome,
            production_admitted=False, publication_allowed=False, host_semantics_verified=False,
            calls=self.send.provider.calls, known_tokens=self.send.provider.tokens,
            unknown_reserved_tokens=self.send.provider.reserved_tokens))
        return EvaluationResult(score=0, verdict=EvaluationVerdict.FAIL, summary=outcome)

    def _review(self, inputs, name, stage):
        prepared = self.contract_module.make_request(inputs, name, stage)
        exchange = self.send(prepared)
        if not isinstance(exchange, Exchange):
            raise ValueError('natural_duty_exchange_missing')
        response, issued = exchange.response, exchange.issued_request
        metadata = dict(issued.metadata)
        if metadata.pop('coach_budget_contract', None) != 'coach-bounded-review-v2':
            raise ValueError('natural_duty_budget_binding')
        if (not 0 < issued.timeout_s <= prepared.timeout_s
                or replace(issued, metadata=metadata, timeout_s=prepared.timeout_s) != prepared
                or exchange.receipt_request_sha256 != self.contract_module.request_sha(issued)
                or (response.provider, response.model) != self.contract_module.request_identity(issued)
                or response.finish_reason != 'tool_calls' or (response.content or '').strip()
                or len(response.tool_calls) != 1 or response.tool_calls[0].name != 'submit_report_review'):
            raise ValueError('natural_duty_exchange_invalid')
        raw = compact(dict(response.tool_calls[0].arguments))
        # Raw public opinions are business evidence, never private reasoning.
        self.record(name+'-'+stage, dict(version=self.contract_module.VERSION, raw=raw,
            input_sha256=digest(inputs.data_json), report_sha256=digest(inputs.source.report),
            prepared_request_sha256=self.contract_module.request_sha(prepared), issued_request_sha256=self.contract_module.request_sha(issued),
            receipt_request_sha256=exchange.receipt_request_sha256,
            actual_model=response.model, usage=asdict(response.usage)))
        value = direct.validate(raw, inputs, name) if stage == 'initial' else duty.validate(raw, inputs, name)
        self.entries.append((name, stage, value))
        return raw, value

    def evaluate(self, request):
        if self.state not in ('initial', 'fresh'):
            raise ValueError('natural_duty_invalid_state')
        stage = self.state
        try:
            inputs = build_inputs(request)
            if stage == 'fresh' and inputs != self.expected_fresh:
                raise ValueError('natural_duty_fresh_input_changed')
            if stage == 'initial':
                self.original, self.original_request = inputs, request
                self.proposals = []
            values = []
            for name in duty.DUTIES:
                raw, value = self._review(inputs, name, stage)
                values.append(value)
                if value.verdict == 'fail':
                    return self.stop(stage+'_'+name+'_rejected')
                if stage == 'fresh' and (value.verdict != 'pass' or value.score < 85):
                    return self.stop('fresh_'+name+'_rejected')
                if stage == 'initial':
                    self.proposals.append(direct.bind(inputs, name, raw))
            if all(v.verdict == 'pass' and v.score >= 85 for v in values):
                return self.stop('candidate_initial_pass_unqualified' if stage == 'initial'
                                 else 'candidate_repaired_pass_unqualified')
            if stage != 'initial' or all(v.verdict == 'pass' for v in values):
                return self.stop('candidate_score_gate_rejected')
            # No half-fresh run: reserve the necessary call slots before any
            # application. The actual token/time gate still governs each send.
            budget = self.send.provider
            if budget.contract.descriptor()['max_calls'] - budget.calls < 2:
                return self.stop('insufficient_fresh_call_slots')
            if (self.contract_module.VERSION == 'natural-flash-sol-development-v1'
                    and budget.tokens + budget.reserved_tokens + 2 * 80384 > budget.contract.descriptor()['total_tokens']):
                return self.stop('insufficient_fresh_token_budget')
            self.assembly = direct.preview(inputs, self.proposals)
            self.expected_fresh = report_inputs(inputs, self.assembly.report)
            self.record('preview', dict(report=self.assembly.report, journal=self.assembly.journal,
                candidate_version=self.contract_module.VERSION, structural_checks_only=True,
                semantic_compatibility_verified=False,
                actual_fresh_requests={n:self.contract_module.request_sha(self.contract_module.make_request(self.expected_fresh,n,'fresh')) for n in duty.DUTIES}))
            issues = tuple(i.model_dump(mode='json') for v in values for i in v.issues)
            self.initial_result = EvaluationResult(score=min(v.score for v in values),
                verdict=EvaluationVerdict.NEEDS_REVISION, issues=issues,
                summary='Unqualified candidate exact-patch preview; two full fresh reviews required.')
            self.state = 'revision'
            return self.initial_result
        except NaturalDutySuspended:
            raise
        except BaseException as error:
            if self.state != 'terminal':
                try:
                    self.stop('candidate_execution_failed')
                except Exception:
                    error.add_note('natural duty outcome persistence failed')
            raise

    def revise(self, request):
        try:
            if (self.state != 'revision' or request.evaluation != self.initial_result
                    or request.player_summary != self.original_request.player_summary
                    or request.deterministic_report != self.original_request.deterministic_report
                    or request.knowledge != self.original_request.knowledge
                    or request.report != self.original.source.report):
                raise ValueError('natural_duty_revision_binding')
            budget = self.send.provider
            if budget.stopped or budget.calls > budget.contract.descriptor()['max_calls'] - 2:
                raise ValueError('natural_duty_fresh_slots_lost')
            if budget.clock()-budget.started >= budget.contract.descriptor()['execution_timeout_s']:
                raise ProviderResponseError(provider='zhipu', code='timeout')
            if direct.preview(self.original, self.proposals) != self.assembly:
                raise ValueError('natural_duty_preview_changed')
            self.record('application', dict(version=self.contract_module.VERSION,
                report_sha256=digest(self.assembly.report), original_report_sha256=digest(request.report),
                deterministic_application=True, host_semantics_verified=False,
                production_admitted=False))
            self.state = 'fresh'
            return CoachDraft(report=self.assembly.report)
        except NaturalDutySuspended:
            raise
        except BaseException as error:
            if self.state != 'terminal':
                try:
                    self.stop('candidate_application_failed')
                except Exception:
                    error.add_note('natural duty outcome persistence failed')
            raise
