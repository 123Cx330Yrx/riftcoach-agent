"""Bind existing native review gates to a resumable candidate session.

No dispatch, judgment generation, API key loading or model sending occurs here.
An operator supplies actual principals and the existing native event reader.
"""
import json
from pathlib import Path

from app.evaluation.sol_natural_session import canonical, digest, SessionBlocked, SessionPaused
from scripts.reviewer_profile_batch import ExactNativeGate
from scripts.review_independence_contract import required_binding
from app.evaluation.golden_journal import write_new_json


class SessionReviewGate:
    REJECTION_POLICY = 'initial_review_rejection_policy'
    PAUSE_INITIAL = 'pause-initial-review-v1'

    def __init__(self, session, *, plan, workspace, event_source):
        if plan.get(self.REJECTION_POLICY, 'stop') not in ('stop', self.PAUSE_INITIAL):
            raise ValueError('session_unknown_review_rejection_policy')
        if session.binding.get('review_plan_sha256') != digest(canonical(plan)):
            raise ValueError('session_review_plan_binding')
        self.session, self.plan = session, plan
        self.native = ExactNativeGate(plan, workspace, event_source)
        self.folder = session.journal_root/'host'
        if not any(self.folder.is_relative_to(p.resolve()) for p in workspace.evidence_roots):
            raise ValueError('session_review_workspace_binding')
        session.review_gate = self

    def _repair_pending(self, handle):
        # Only a new, explicitly pinned plan may retain an initial review for
        # repair. This never accepts the rejected opinion or permits sending.
        if (self.plan.get(self.REJECTION_POLICY) != self.PAUSE_INITIAL
                or handle['kind'] != 'opinion'
                or handle['binding']['key'] not in ('facts-initial', 'completion-initial')):
            return False
        submission = json.loads((Path(handle['folder'])/'submission.json').read_bytes())
        defects = [defect for role in ('primary', 'independent')
                   for defect in submission[role]['decision']['defects']]
        return bool(defects) and all(d['kind'] == 'missed_error' for d in defects)

    def _repair_file(self, key):
        if key not in ('facts-initial', 'completion-initial'):
            raise ValueError('session_initial_repair_key_required')
        return self.session.journal_root/'review-repairs'/key/'handle.json'

    def _repair_material(self, handle, coordination):
        """Rebuild solely from original opinions; no replacement opinion/text."""
        from scripts import review_duty_direct_patch as direct
        from app.evaluation.golden_review_experiment import compact
        key = handle['binding']['key']
        if key != 'completion-initial' or not self._repair_pending(handle):
            raise SessionPaused('session_review_repair_pair_required')
        handles = {h['binding']['key']: h for h in self.handles()}
        if not all(k in handles for k in ('facts-initial', 'completion-initial')):
            raise SessionPaused('session_review_repair_pair_required')
        sources, opinions, submissions, requests = [], [], {}, []
        inputs = None
        for duty in ('facts', 'completion'):
            original = handles[duty+'-initial']
            accepted = self.native.replay(original)
            if not accepted and original != handle:
                raise SessionPaused('session_review_repair_pair_required')
            folder = Path(original['folder'])
            material = json.loads((folder/'material.json').read_bytes())
            request = json.loads(material['request_raw'])
            restored = self.session.contract_module.restore_context(
                request['metadata'][self.session.contract_module.CONTEXT])
            if inputs is not None and restored != inputs:
                raise SessionBlocked('session_repair_source_changed')
            inputs = restored
            if inputs.source.report != material['report']:
                raise SessionBlocked('session_repair_report_changed')
            raw = material['responses'][0]
            if not isinstance(raw, str):
                raw = compact(raw)
            if json.loads((self.session.journal_root/(duty+'-initial.json')).read_bytes())['raw'] != raw:
                raise SessionBlocked('session_repair_opinion_changed')
            opinions.append(direct.bind(inputs, duty, raw))
            sources.append(material['complete_source'])
            submissions[duty] = json.loads((folder/'submission.json').read_bytes())
            requests.append(material['request_raw'])
        if sources[0] != sources[1]:
            raise SessionBlocked('session_repair_source_changed')
        assembly = direct.preview(inputs, opinions, coordination=coordination)
        if assembly.report == inputs.source.report:
            raise SessionPaused('session_review_repair_edits_required')
        return dict(complete_source=sources[0], original_report=inputs.source.report,
            report=assembly.report, patch_journal=assembly.journal,
            responses=[p.raw for p in opinions], initial_requests_with_complete_policies=requests,
            original_reviews=submissions, rejected_binding=handle['binding'],
            rejected_submission_sha256=digest((Path(handle['folder'])/'submission.json').read_bytes()),
            repair_scope='Check every missed error against actual edits and the full report; '
                         'accept only when all real errors are fixed and correct content is preserved. '
                         'A disputed wording-only defect need not cause an unnecessary edit; explain it. '
                         'The original rejected review remains rejected.' )

    def prepare_repair(self, key, *, coordination=None):
        session = self.session
        session.verify()
        if (not session._open or session.read_only or session.reconciling
                or (session.root/'terminal.json').exists()):
            raise SessionBlocked('session_repair_not_owned_or_closed')
        handles = list(self.handles())
        if not handles or handles[-1]['binding']['key'] != key:
            raise SessionBlocked('session_review_not_current')
        handle = handles[-1]
        if self.native.replay(handle) or not self._repair_pending(handle):
            raise ValueError('session_repair_requires_rejected_initial')
        path = self._repair_file(key)
        if path.exists():
            saved = json.loads(path.read_bytes())
            if saved['coordination'] != coordination:
                raise SessionBlocked('session_repair_selection_changed')
            self._repair_resolved(handle)
            return saved['handle']
        material = self._repair_material(handle, coordination)
        path.parent.mkdir(parents=True, exist_ok=False)
        bound = required_binding(dict(plan_sha256=digest(canonical(self.plan)), key=key+'-repair',
            stage='revision', report_sha256=digest(material['report'].encode('utf-8')),
            request_sha256=digest(canonical(material)),
            response_sha256=digest(canonical(material['responses']))))
        repair = self.native.publish(path.parent/'native', bound, 'edit', material)
        write_new_json(path, dict(handle=repair, coordination=coordination))
        session._checkpoint('review_repair_task_published')
        return repair

    def _repair_resolved(self, handle):
        if not self._repair_pending(handle):
            return False
        path = self._repair_file(handle['binding']['key'])
        if not path.exists():
            return False
        saved = json.loads(path.read_bytes())
        repair = saved['handle']
        material = self._repair_material(handle, saved['coordination'])
        if (digest(canonical(material)) != repair['binding']['request_sha256']
                or digest(material['report'].encode('utf-8')) != repair['binding']['report_sha256']
                or json.loads((Path(repair['folder'])/'material.json').read_bytes()) != material):
            raise SessionBlocked('session_repair_binding_changed')
        return ((Path(repair['folder'])/'submission.json').exists()
                and self.native.replay(repair))

    def submit_repair(self, key, primary_decision, event_id):
        session = self.session
        session.verify()
        if (not session._open or session.read_only or session.reconciling
                or (session.root/'terminal.json').exists()):
            raise SessionBlocked('session_repair_not_owned_or_closed')
        original = list(self.handles())[-1]
        if original['binding']['key'] != key or not self._repair_pending(original):
            raise SessionBlocked('session_review_not_current')
        path = self._repair_file(key)
        saved = json.loads(path.read_bytes())
        self._repair_resolved(original)  # Rebuild binding before native import.
        accepted = self.native.submit(saved['handle'], primary_decision, event_id)
        session._checkpoint('review_repair_approved' if accepted else 'review_repair_rejected')
        return accepted

    def verify_repair_report(self, report):
        for handle in self.handles():
            if self._repair_pending(handle) and self._repair_resolved(handle):
                saved = json.loads(self._repair_file(handle['binding']['key']).read_bytes())
                if digest(report.encode('utf-8')) != saved['handle']['binding']['report_sha256']:
                    raise SessionBlocked('session_repair_actual_report_changed')

    def require(self, key, kind, material, report):
        session = self.session
        request_sha = digest(canonical(material))
        bound = required_binding(dict(plan_sha256=digest(canonical(self.plan)), key=key,
            stage='final' if key.endswith('-fresh') else 'revision' if kind != 'opinion' else 'initial',
            report_sha256=digest(report.encode('utf-8')), request_sha256=request_sha,
            response_sha256=digest(canonical(material.get('responses', material)))))
        inherited = getattr(self.native, 'inherited_binding', None)
        if inherited is not None:
            bound = inherited(bound)
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
        if not accepted and not self._repair_resolved(handle):
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
                    if self._repair_pending(handle):
                        if self._repair_resolved(handle):
                            continue
                        raise SessionPaused('session_review_repair_required')
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
            if self._repair_pending(handles[-1]):
                session._checkpoint('review_repair_pending')
                return False
            from app.evaluation.golden_journal import write_new_json
            write_new_json(session.root/'terminal.json', dict(reason='semantic_rejected', key=key,
                publication_allowed=False, production_admitted=False))
            session._checkpoint('semantic_rejected')
        return accepted
