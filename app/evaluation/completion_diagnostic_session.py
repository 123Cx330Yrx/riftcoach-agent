"""Resume a sealed completion boundary through the existing review workflow.

This is an opt-in diagnostic engine with injected credentials/send guards, not
an authorization issuer or product Runtime entry. Parent proof must first have
been produced by prepare_completion_continuation with the original frozen code.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import json
from pathlib import Path
import shutil

from app.evaluation import sol_completion_contract as contract
from app.evaluation.golden_journal import write_new_json
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, canonical, digest
from app.evaluation.sol_session_review import SessionReviewGate
from app.evaluation.source_patch_editor import report_inputs
from app.runtime.sol_session_runtime import SessionBudget, SessionWorkflow
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.observed_provider import ObservedLLMProvider
from scripts.host_review_workspace import HostReviewWorkspace
from scripts.reviewer_profile_batch import ExactNativeGate, inventory
from scripts.review_completion_necessity_candidate import materials
from scripts import review_duty_direct_patch as direct
from scripts.prepare_reviewer_profile_screen import visible, json_value

VERSION = 'completion-diagnostic-session-v1'


def read(path):
    return json.loads(Path(path).read_bytes())


def parent_binding(proof_file, proof_sha):
    path = Path(proof_file).resolve()
    if digest(path.read_bytes()) != proof_sha:
        raise ValueError('completion_original_proof_required')
    proof = read(path)
    spec = dict(proof_file=str(path), proof_sha256=proof_sha, proof=proof)
    verify_parent(spec)
    return spec


def verify_parent(spec):
    proof = spec['proof']
    path = Path(spec['proof_file'])
    if digest(path.read_bytes()) != spec['proof_sha256'] or read(path) != proof:
        raise SessionBlocked('completion_parent_proof_changed')
    root = Path(proof['parent_operator'])
    if (inventory(root) != proof['parent_inventory']
            or inventory(root.with_name(root.name+'-authors')) != proof['parent_author_inventory']
            or proof.get('original_native_review_replayed') is not True
            or proof.get('provider_requests') != 0 or proof.get('key_reads') != 0):
        raise SessionBlocked('completion_parent_originals_changed')
    seal = read(root/'seal.json')
    if (digest((root/'seal.json').read_bytes()) != proof['parent_seal_sha256']
            or seal['inventory'] != {k:v for k,v in proof['parent_inventory'].items() if k != 'seal.json'}
            or seal['result'] != proof['strict_parent_replay']
            or seal['original_roots'] != proof['parent_roots']
            or seal['result'].get('strict_replay') is not True
            or proof['imported_operations'] != 9):
        raise SessionBlocked('completion_parent_trust_root')
    historical, derived = proof['historical_budget'], deepcopy(proof['historical_budget'])
    derived.update(stopped=False, failed=False)
    derived['logical']['review'] = 1
    derived.pop('retry_issued_raw', None)
    if (proof['derived_budget'] != derived or historical['calls'] != 4
            or not 0 <= historical['tokens'] <= 66591 or historical['reserved_tokens'] != 0
            or historical['retries'] != 0 or historical['logical'] != {'generation':2, 'review':2}
            or proof['strict_parent_replay']['accounting'] != {k:historical[k]
                for k in ('calls','tokens','reserved_tokens','retries')}):
        raise SessionBlocked('completion_parent_budget_binding')


class InheritedNative:
    def __init__(self, current, original, handle, spec):
        self.current, self.original, self.handle, self.spec = current, original, handle, spec

    def publish(self, *args, **kwargs):
        return self.current.publish(*args, **kwargs)

    def replay(self, handle):
        verify_parent(self.spec)
        folder = Path(handle['folder'])
        parent = Path(self.spec['proof']['parent_operator'])
        if folder.is_relative_to(parent):
            if handle != self.handle:
                raise SessionBlocked('completion_unrecognized_inherited_handle')
            return self.original.replay(handle)
        return self.current.replay(handle)

    def submit(self, handle, *args, **kwargs):
        if handle == self.handle:
            raise SessionBlocked('completion_parent_resubmission_forbidden')
        return self.current.submit(handle, *args, **kwargs)


def open_session(operator, spec, event_source, *, before_new_model, guard=None,
                 checkpoint=None, read_only=False, manual_retry=False, sink=lambda value: None,
                 control_binding=None, author_root=None, evidence_root=None):
    verify_parent(spec)
    root, proof = Path(operator).resolve(), spec['proof']
    parent = Path(proof['parent_operator'])
    if root.is_relative_to(parent) or parent.is_relative_to(root):
        raise ValueError('completion_parent_operator_overlap')
    plan = read(parent/'plan.json')

    def before():
        verify_parent(spec)
        if before_new_model is None:
            raise SessionBlocked('completion_specific_send_guard_required')
        before_new_model()

    session = CandidateSession(root/'session',
        binding=dict(candidate_contract=contract.VERSION, fixture_only=False,
            review_plan_sha256=digest(canonical(plan['review_plan'])),
            completion_parent_sha256=digest(canonical(spec)),
            launch_controls_sha256=digest(canonical(control_binding))),
        contract_module=contract, transport_root=root/'transport', journal_root=root/'journal',
        guard_sha=guard, checkpoint_sha=checkpoint, read_only=read_only, manual_retry=manual_retry,
        before_new_model=before, checkpoint_sink=sink)
    current_workspace = HostReviewWorkspace(cwd=contract.ROOT, python=plan['python'],
        answers=author_root or root.with_name(root.name+'-authors'),
        evidence_roots=[evidence_root or root])
    gate = SessionReviewGate(session, plan=plan['review_plan'], workspace=current_workspace, event_source=event_source)
    old_workspace = HostReviewWorkspace(cwd=plan['cwd'], python=plan['python'],
        answers=parent.with_name(parent.name+'-authors'), evidence_roots=[parent])
    gate.native = InheritedNative(gate.native, ExactNativeGate(plan['review_plan'], old_workspace, event_source),
                                 proof['accepted_handle'], spec)
    session.completion_parent = spec
    return session, gate


def import_parent(session):
    """Call inside a newly owned session; all imported original bytes stay exact."""
    spec, root = session.completion_parent, session.root
    verify_parent(spec)
    if (root/'parent-import.json').exists():
        return
    if session.read_only or session.guard_sha is None or list((root/'operations').iterdir()):
        raise SessionBlocked('completion_parent_import_not_empty')
    proof = spec['proof']
    parent = Path(proof['parent_operator'])
    for n in range(1, proof['imported_operations']+1):
        for suffix in ('intent', 'result'):
            name = f'{n:04d}-{suffix}.json'
            with (root/'operations'/name).open('xb') as stream:
                stream.write((parent/'execution/session/operations'/name).read_bytes())
    session.journal_root.mkdir()
    shutil.copy2(parent/'execution/journal/facts-initial.json', session.journal_root/'facts-initial.json')
    write_new_json(root/'parent-import.json', dict(version=VERSION,
        proof_sha256=spec['proof_sha256'], imported_operations=proof['imported_operations'],
        historical_budget=proof['historical_budget'], failed_attempt_retained=True,
        old_completion_accepted=False, inherited_native_handle=proof['accepted_handle']))
    session.active_before = proof['inherited_active_seconds']
    session._checkpoint('completion_parent_imported')


class SignalRecorder:
    def __init__(self, folder):
        self.folder = folder

    def observe(self, signal):
        self.folder.mkdir(exist_ok=True)
        write_new_json(self.folder/f'{len(list(self.folder.iterdir()))+1:04d}.json', signal.model_dump(mode='json'))


@dataclass(frozen=True)
class BoundRequest:
    report: str
    source_sha256: str
    player_summary: object = None
    deterministic_report: str = ''
    knowledge: object = None
    evaluation: object = None


class CompletionWorkflow(SessionWorkflow):
    def __init__(self, send, *, session):
        super().__init__(send, session=session, journal_root=session.journal_root, contract_module=contract)
        self.proof = session.completion_parent['proof']
        context = self.proof['frontier']['metadata'][contract.CONTEXT]
        self.inputs = contract.parent.restore_context(context)
        if self.inputs != materials()['a']:
            raise SessionBlocked('completion_original_control_material_changed')
        self.source_sha = digest(canonical(dict(data_json=self.inputs.data_json, pack_json=self.inputs.pack_json)))

    def inputs_for(self, request):
        if type(request) is not BoundRequest or request.source_sha256 != self.source_sha:
            raise SessionBlocked('completion_bound_source_required')
        return report_inputs(self.inputs, request.report)

    def _review(self, inputs, name, stage):
        if (name, stage) == ('facts', 'initial'):
            if inputs != self.inputs:
                raise SessionBlocked('completion_inherited_facts_report_changed')
            self.session.review_gate.verify_prior()
            raw = read(self.journal_root/'facts-initial.json')['raw']
            value = direct.validate(raw, inputs, name)
            self.entries.append((name, stage, value))
            return raw, value
        if (name, stage) == ('completion', 'initial'):
            for case, control in materials().items():
                if case != 'a':
                    self.control(case, control)
        return super()._review(inputs, name, stage)

    def control(self, case, inputs):
        prepared = contract.make_request(inputs, 'completion', control_case=case)
        exchange = self.send(prepared)
        # SessionBudget and the owned receiver bind identity, request and receipt;
        # validate the opinion before publishing the full-source native task.
        business = visible(json_value(exchange.issued_request))
        context = exchange.issued_request.metadata[contract.CONTEXT]
        raw = json.dumps(dict(exchange.response.tool_calls[0].arguments), ensure_ascii=False, separators=(',', ':'))
        value = contract.validate_business(business, context)(raw)
        self.record('control-'+case, dict(raw=raw, request_sha256=contract.request_sha(exchange.issued_request),
            report_sha256=digest(inputs.source.report.encode('utf-8'))))
        self.session.review_gate.require('control-'+case, 'opinion', dict(
            complete_source=dict(data_json=inputs.data_json, pack_json=inputs.pack_json),
            report=inputs.source.report, request_raw=contract.request_bytes(exchange.issued_request).decode('utf-8'),
            responses=[raw], duty='completion', stage='initial', development_control=case), inputs.source.report)
        if value.verdict == 'fail':
            raise SessionBlocked('completion_control_refused')


def run_chain(session, router):
    """One resumable segment; caller owns grant, key prompt, close and sealing."""
    verify_parent(session.completion_parent)
    session.verify()
    import_parent(session)
    proof = session.completion_parent['proof']
    # The full prefix was independently replayed with the original frozen code.
    # Here it is inherited evidence, never reissued or reinterpreted by v1.6.5.
    session.cursor = proof['imported_operations']
    observed = ObservedLLMProvider(delegate=router, observer=SignalRecorder(session.root/'signals'),
                                   request_identity=contract.request_identity)
    budget = SessionBudget(observed, session=session, coach_contract=contract.CONTRACT)
    seed = deepcopy(proof['derived_budget'])
    seed['logical']['control'] = 0
    budget.restore(seed)
    workflow = CompletionWorkflow(SharedBudgetReviewSender(budget), session=session)
    request = BoundRequest(workflow.inputs.source.report, workflow.source_sha)
    workflow.evaluate(request)
    if workflow.state == 'revision':
        draft = workflow.revise(replace(request, evaluation=workflow.initial_result))
        workflow.evaluate(replace(request, report=draft.report))
    if workflow.state != 'terminal':
        raise SessionBlocked('completion_workflow_not_terminal')
    return dict(outcome=workflow.outcome, accounting=budget.snapshot(),
        application=workflow.assembly.report if workflow.assembly is not None else None,
        publication_allowed=False, production_admitted=False)
