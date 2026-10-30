"""Product release decision on the same durable, source-bound dual review.

Review scores remain model judgments. This orchestrator neither manufactures
Host approval nor claims structural checks prove semantic correctness.
"""
from app.evaluation.golden_review_experiment import digest
from app.evaluation.source_patch_editor import report_inputs
from app.evaluation.sol_natural_session import SessionPaused
from app.harness.steps import EvaluationResult, EvaluationVerdict
from app.providers.errors import ProviderResponseError
from app.runtime.sol_session_runtime import SessionBudget, SessionWorkflow
from scripts import review_duty_direct_patch as direct, review_duty_composition as duty


class ProductBudget(SessionBudget):
    def _provider_for_request(self, request):
        # Leave the two initial duties and possible two fresh duties intact.
        if (self.contract_module.role_for_request(request) == 'generation'
                and self.calls + 1 + 4 > self.contract.descriptor()['max_calls']):
            raise ProviderResponseError(provider=self.provider_name, code='product_review_slots_reserved')
        return super()._provider_for_request(request)

    def chat(self, request):
        try:
            return super().chat(request)
        except ProviderResponseError as exc:
            if exc.code in {'external_call_budget_exhausted', 'token_budget_exhausted',
                            'timeout', 'product_review_slots_reserved'}:
                raise SessionPaused('product_budget_exhausted') from exc
            raise


class ProductWorkflow(SessionWorkflow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from . import sol_contract
        if self.contract_module is not sol_contract or not self.session.worker_product:
            raise ValueError('product_workflow_binding')
        self.identical_coordination = None

    def assemble(self, inputs):
        inventory = direct.conflict_inventory(inputs, self.proposals)
        if not inventory['conflicts']:
            return direct.preview(inputs, self.proposals)
        operations = {op['id']: op for op in inventory['operations']}
        resolutions = []
        for component in inventory['conflicts']:
            items = [operations[key] for key in component['operation_ids']]
            if len({(op['start'], op['end'], op['before'], op['after']) for op in items}) != 1:
                raise SessionPaused('session_awaiting_patch_coordination')
            chosen = [items[0]['id']]
            coverage = sorted({(op['duty'], issue) for op in items for issue in op['issue_ids']})
            resolutions.append(dict(component=component['component'], selected_operation_ids=chosen,
                issue_coverage=[dict(duty=name, issue_id=issue, selected_operation_ids=chosen,
                    reason='Identical source span and exact replacement bytes.') for name, issue in coverage]))
        self.identical_coordination = dict(version=direct.COORDINATION_VERSION,
            inventory_sha256=direct.inventory_sha(inventory), resolutions=resolutions)
        self.record('identical-patch-deduplication', self.identical_coordination)
        return direct.preview(inputs, self.proposals, coordination=self.identical_coordination)

    def verify_assembly(self):
        return direct.preview(self.original, self.proposals, coordination=self.identical_coordination)

    def _fresh_room(self):
        budget = self.send.provider
        limits = budget.contract.descriptor()
        if (budget.calls + 2 > limits['max_calls']
                or budget.tokens + budget.reserved_tokens + 2 * self.contract_module.FRESH_REVIEW_RESERVATION > limits['total_tokens']
                or self.session.active_seconds >= limits['execution_timeout_s']):
            raise SessionPaused('product_fresh_budget_required')

    def _pass(self, values, inputs, stage):
        score = min(value.score for value in values)
        self.record('outcome', dict(version=self.contract_module.VERSION,
            outcome='product_initial_pass' if stage == 'initial' else 'product_repaired_pass',
            report_sha256=digest(inputs.source.report), input_sha256=digest(inputs.data_json),
            publication_eligible=True, host_semantics_verified=False,
            calls=self.send.provider.calls, known_tokens=self.send.provider.tokens,
            unknown_reserved_tokens=self.send.provider.reserved_tokens))
        self.outcome = 'product_initial_pass' if stage == 'initial' else 'product_repaired_pass'
        self.state = 'terminal'
        return EvaluationResult(score=score, verdict=EvaluationVerdict.PASS,
            summary='Both full-source duties passed under the explicit product contract.')

    def evaluate(self, request):
        if self.state not in ('initial', 'fresh'):
            raise ValueError('product_workflow_state')
        stage = self.state
        inputs = self.inputs_for(request)
        if stage == 'fresh' and inputs != self.expected_fresh:
            raise ValueError('product_fresh_input_changed')
        if stage == 'initial':
            self.original, self.original_request = inputs, request
            self.proposals = []
        values = []
        for name in duty.DUTIES:
            raw, value = self._review(inputs, name, stage)
            values.append(value)
            if stage == 'initial':
                self.proposals.append(direct.bind(inputs, name, raw))
        if all(value.verdict == 'pass' and value.score >= 85 for value in values):
            return self._pass(values, inputs, stage)
        if stage == 'fresh':
            raise SessionPaused('product_fresh_repair_required')
        if any(value.verdict == 'fail' for value in values):
            # A terminal opinion supplies no executable repair. Keep the pair
            # for a real repair decision, never forge a replacement opinion.
            raise SessionPaused('product_review_repair_required')
        if all(value.verdict == 'pass' for value in values):
            raise SessionPaused('product_review_score_required')
        self._fresh_room()
        try:
            self.assembly = self.assemble(inputs)
        except ValueError as exc:
            raise SessionPaused('product_patch_repair_required') from exc
        self.expected_fresh = report_inputs(inputs, self.assembly.report)
        self.record('preview', dict(report=self.assembly.report, journal=self.assembly.journal,
            candidate_version=self.contract_module.VERSION, structural_checks_only=True,
            semantic_compatibility_verified=False,
            actual_fresh_requests={name: self.contract_module.request_sha(
                self.contract_module.make_request(self.expected_fresh, name, 'fresh')) for name in duty.DUTIES}))
        self.initial_result = EvaluationResult(score=min(value.score for value in values),
            verdict=EvaluationVerdict.NEEDS_REVISION,
            issues=tuple(issue.model_dump(mode='json') for value in values for issue in value.issues),
            summary='Apply the bound corrections once, then review the actual new report with both duties.')
        self.state = 'revision'
        return self.initial_result

    def revise(self, request):
        self._fresh_room()
        return super().revise(request)
