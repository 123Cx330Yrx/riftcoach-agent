"""Fixed-report original15 orchestration using the existing candidate workflow.

No sender, credential loader, labels in native material or inherited results.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import json

from app.evaluation import role_qualification as frozen, sol_review_contract as contract
from app.evaluation.golden_native_issues_review import build_inputs
from app.evaluation.source_patch_editor import report_inputs
from app.evaluation.sol_natural_session import CandidateSession, SessionBlocked, canonical, digest
from app.evaluation.sol_session_review import SessionReviewGate
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.review_sender import SharedBudgetReviewSender
from app.runtime.sol_session_runtime import SessionBudget, SessionWorkflow
from scripts.host_review_workspace import HostReviewWorkspace

VERSION = 'sol-dual-necessity-original15-session-v1'


def case_for(key):
    cases, _ = frozen.frozen_cases()
    selected = [(cell, source) for cell, source in cases if cell['key'] == key]
    if len(selected) != 1:
        raise ValueError('original15_unknown_case')
    cell, source = selected[0]
    return cell, build_inputs(source)


def case_slug(key):
    # Selecting a safe directory name does not rebuild 15 full source packs.
    # open_case/run_case still validate all original inputs and source hashes.
    coverage = json.loads((frozen.ROOT/frozen.COVERAGE).read_bytes())
    keys = {f"{row['suite']}:{row['index']}" for row in coverage['completed']+coverage['cases']}
    if key not in keys or '/' in key or '\\' in key:
        raise ValueError('original15_unknown_case')
    return key.replace(':', '-')


def open_case(operator, key, review_plan, event_source, *, plan_sha, authorization_sha,
              python, before=None, guard=None, checkpoint=None, read_only=False,
              manual_retry=False, reconcile=False, preflight=False, sink=lambda value: None):
    operator = Path(operator).resolve()
    folder = operator/('native-preflight' if preflight else 'cases/'+case_slug(key))
    cell, _ = case_for(key)
    binding = dict(version=VERSION, candidate_contract=contract.VERSION, key=key,
        input_sha256=cell['input_sha256'], report_sha256=cell['report_sha256'],
        plan_sha256=plan_sha, authorization_sha256=authorization_sha, fixture_only=preflight,
        review_plan_sha256=digest(canonical(review_plan)))
    session = CandidateSession(folder/'session', binding=binding, transport_root=folder/'transport',
        journal_root=folder/'journal', guard_sha=guard, checkpoint_sha=checkpoint,
        before_new_model=before, contract_module=contract, checkpoint_sink=sink,
        read_only=read_only, manual_retry=manual_retry, reconcile=reconcile)
    workspace = HostReviewWorkspace(cwd=contract.ROOT, python=python,
        answers=operator.with_name(operator.name+'-authors'), evidence_roots=[operator])
    gate = SessionReviewGate(session, plan=review_plan, workspace=workspace, event_source=event_source)
    return session, gate


class SignalRecorder:
    def __init__(self, folder):
        self.folder = folder

    def observe(self, signal):
        from app.evaluation.golden_journal import write_new_json
        self.folder.mkdir(exist_ok=True)
        write_new_json(self.folder/f'{len(list(self.folder.iterdir()))+1:04d}.json', signal.model_dump(mode='json'))


@dataclass(frozen=True)
class BoundReport:
    report: str
    source_sha256: str
    player_summary: object = None
    deterministic_report: str = ''
    knowledge: object = None
    evaluation: object = None


class FixedReportWorkflow(SessionWorkflow):
    def __init__(self, send, *, session, inputs):
        super().__init__(send, session=session, journal_root=session.journal_root, contract_module=contract)
        self.inputs = inputs
        self.source_sha = digest(canonical(dict(data_json=inputs.data_json, pack_json=inputs.pack_json)))

    def inputs_for(self, request):
        if type(request) is not BoundReport or request.source_sha256 != self.source_sha:
            raise SessionBlocked('original15_bound_source_required')
        return report_inputs(self.inputs, request.report)


def run_case(session, router):
    """Replay/advance exactly one case; no generation, labels or terminal writes."""
    cell, inputs = case_for(session.binding['key'])
    if (session.binding['input_sha256'] != cell['input_sha256']
            or session.binding['report_sha256'] != cell['report_sha256']):
        raise SessionBlocked('original15_input_binding_changed')
    session.verify()
    observed = ObservedLLMProvider(delegate=router, observer=SignalRecorder(session.root/'signals'),
        request_identity=contract.request_identity)
    budget = SessionBudget(observed, session=session, coach_contract=contract.CONTRACT)
    workflow = FixedReportWorkflow(SharedBudgetReviewSender(budget), session=session, inputs=inputs)
    request = BoundReport(inputs.source.report, workflow.source_sha)
    workflow.evaluate(request)
    if workflow.state == 'revision':
        draft = workflow.revise(replace(request, evaluation=workflow.initial_result))
        workflow.evaluate(replace(request, report=draft.report))
    if workflow.state != 'terminal':
        raise SessionBlocked('original15_workflow_not_terminal')
    expected = ('candidate_initial_pass_unqualified' if cell['expected_initial'] == 'accept'
                else 'candidate_repaired_pass_unqualified')
    return dict(key=cell['key'], outcome=workflow.outcome, expected_outcome=expected,
        matched=workflow.outcome == expected, accounting=budget.snapshot(),
        actual_report_sha256=digest((workflow.assembly.report if workflow.assembly else request.report).encode('utf-8')),
        publication_allowed=False, production_admitted=False)


def last_budget(session):
    values = [json.loads(p.read_bytes())['value'] for p in sorted((session.root/'operations').glob('*-result.json'))]
    budgets = [v['budget'] for v in values if isinstance(v, dict) and 'budget' in v]
    return budgets[-1] if budgets else dict(calls=0, tokens=0, reserved_tokens=0, retries=0)
