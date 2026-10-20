"""Bind existing native review gates to a resumable candidate session.

No dispatch, judgment generation, API key loading or model sending occurs here.
An operator supplies actual principals and the existing native event reader.
"""
import json
from pathlib import Path

from app.evaluation.sol_natural_session import canonical, digest, SessionBlocked, SessionPaused
from scripts.reviewer_profile_batch import ExactNativeGate
from scripts.review_independence_contract import required_binding


class SessionReviewGate:
    def __init__(self, session, *, plan, workspace, event_source):
        if session.binding.get('review_plan_sha256') != digest(canonical(plan)):
            raise ValueError('session_review_plan_binding')
        self.session, self.plan = session, plan
        self.native = ExactNativeGate(plan, workspace, event_source)
        self.folder = session.journal_root/'host'
        if not any(self.folder.is_relative_to(p.resolve()) for p in workspace.evidence_roots):
            raise ValueError('session_review_workspace_binding')
        session.review_gate = self

    def require(self, key, kind, material, report):
        session = self.session
        request_sha = digest(canonical(material))
        bound = required_binding(dict(plan_sha256=digest(canonical(self.plan)), key=key,
            stage='final' if key.endswith('-fresh') else 'revision' if kind != 'opinion' else 'initial',
            report_sha256=digest(report.encode('utf-8')), request_sha256=request_sha,
            response_sha256=digest(canonical(material.get('responses', material)))))
        bound_material = dict(material, session_guard_sha256=session.guard_sha,
                              source_checkpoint_sha256=session.checkpoint_sha)
        # The source checkpoint changes after task publication; replay binds
        # business material separately and reads the original published handle.
        def publish():
            self.folder.mkdir(parents=True, exist_ok=True)
            handle = self.native.publish(self.folder/key, bound, kind, bound_material)
            return handle
        handle, _ = session.operation('host-task', dict(key=key, kind=kind, binding=bound), publish)
        self.verify_prior()
        if not (Path(handle['folder'])/'submission.json').exists():
            raise SessionPaused('session_awaiting_native_review')
        accepted = self.native.replay(handle)
        decision, _ = session.operation('host-decision', dict(key=key, binding=bound),
                                         lambda: dict(accepted=accepted))
        if decision['accepted'] != accepted:
            raise SessionBlocked('session_review_changed')
        if not accepted:
            raise SessionBlocked('session_semantic_rejected')

    def handles(self):
        self.session.verify()
        for path in sorted((self.session.root/'operations').glob('*-intent.json')):
            intent = json.loads(path.read_bytes())
            if intent['kind'] != 'host-task':
                continue
            result = path.with_name(path.name.replace('-intent', '-result'))
            if not result.exists():
                raise SessionBlocked('session_host_task_uncommitted')
            yield json.loads(result.read_bytes())['value']

    def verify_prior(self):
        for handle in self.handles():
            if (Path(handle['folder'])/'submission.json').exists():
                if not self.native.replay(handle):
                    raise SessionBlocked('session_semantic_rejected')

    def submit(self, key, primary_decision, event_id):
        session = self.session
        if not session._open or session.read_only or session.reconciling:
            raise SessionBlocked('session_review_import_not_owned')
        handles = list(self.handles())
        if not handles or handles[-1]['binding']['key'] != key:
            raise SessionBlocked('session_review_not_current')
        if (session.root/'terminal.json').exists() or (session.root/'seal.json').exists():
            raise SessionBlocked('session_closed')
        self.verify_prior()
        accepted = self.native.submit(handles[-1], primary_decision, event_id)
        # NativeGate validates the original author file and real event; it never
        # accepts a locally authored replacement for the independent answer.
        session._checkpoint('native_review_imported')
        if not accepted:
            from app.evaluation.golden_journal import write_new_json
            write_new_json(session.root/'terminal.json', dict(reason='semantic_rejected', key=key,
                publication_allowed=False, production_admitted=False))
            session._checkpoint('semantic_rejected')
        return accepted
