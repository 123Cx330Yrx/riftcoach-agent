"""Isolated, dependency-injected direct-patch development chain; no paid CLI.

Reuse frozen IO/native/budget machinery privately. Deterministic application is
an artifact, never a synthetic model exchange. No production registration.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re

from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.source_patch_editor import report_inputs
from scripts import review_duty_direct_patch as direct
from scripts import review_duty_composition as duty
from scripts import review_duty_execution as legacy
from scripts import review_duty_host_gate as host
from scripts.full_chain_modules import private_module
from scripts.review_independence_contract import canonical_json

ROOT = legacy.ROOT
VERSION = 'offline-direct-patch-execution-v1'
SLOTS = ('facts-initial', 'completion-initial', 'facts-fresh', 'completion-fresh')
LIMITS = dict(max_calls=4, total_tokens=387072, execution_timeout_s=2400,
              request_timeout_s=600, max_input_tokens=64000, max_output_tokens=32768)
HOST_POLICY = (
    'This candidate has reviewer-authored exact repairs. For initial opinions, inspect every '
    'issue, explanation, source, correction, repair issue_ids mapping and complete before/after/reason. '
    'For compatibility inspect both complete opinions and all repairs against the entire source; '
    'non-overlap is not semantic compatibility. For edit inspect the complete deterministic preview, '
    'not a model editor response: verify every actual change and all preserved content. '
    'The preview has no semantic certification; your full-source decision must establish it. '
    'Do not infer acceptance from structural validation or preview flags. '
)

# A module-local task builder adds the candidate obligations before checkpoint
# publication. No post-publication mutation or public-module monkeypatch.
_gate = private_module(ROOT/'scripts/review_duty_host_gate.py', {})
_task = _gate.review_task
_gate.review_task = lambda bound, instructions: _task(bound, HOST_POLICY + instructions)
_execution = private_module(ROOT/'scripts/review_duty_execution.py',
    {'scripts.review_duty_host_gate': _gate})
_execution.VERSION, _execution.SLOTS, _execution.LIMITS = VERSION, SLOTS, LIMITS


def model_for(request):
    if (request.metadata.get(direct.MARKER) != direct.VERSION
            or request.metadata[duty.MARKER]['duty'] not in duty.DUTIES):
        raise ValueError('direct_patch_execution_identity')
    return legacy.model_for(request)


_execution.model_for = model_for
request_bytes = legacy.request_bytes
check_issued = legacy.check_issued
sha = host.sha


def preparation(inputs, *, primary, independent):
    plan = legacy.preparation(inputs, primary=primary, independent=independent)
    plan.update(kind=VERSION, limits=dict(LIMITS), slots=list(SLOTS),
        initial_requests={d: duty.request_sha(direct.review_request(inputs, d)) for d in duty.DUTIES})
    for path in ('scripts/review_duty_direct_patch.py', 'scripts/review_duty_patch_execution.py',
                 'scripts/review_duty_patch_replay.py'):
        plan['source_sha256'][path] = sha(ROOT/path)
    return json.loads(canonical_json(plan))


_execution.preparation = preparation


class DevelopmentChain(_execution.DevelopmentChain):
    def snapshot(self):
        # Same strict evidence rules, with separate model slots and Host stages.
        allowed = {'plan.json', 'result.json', 'closure.json', 'development-host-clock',
                   'preview.json', 'application.json', *SLOTS}
        stages = (*SLOTS, 'compatibility', 'edit')
        allowed.update('host-'+s for s in stages)
        for s in stages:
            allowed.update('host-'+s+'/'+f for f in ('material.json', 'independent-task.json',
                'task-checkpoint.json', 'dispatch.txt', 'submission.json'))
        for s in SLOTS:
            allowed.update(s+'/'+f for f in ('prepared-request.json', 'issued-request.json',
                'response.json', 'receipt.json', 'call-state.json', 'transport', 'transport/stream-001'))
            allowed.update(s+'/transport/stream-001/'+f for f in ('reservation.json', 'result.json',
                'progress.json', 'progress.tmp', 'failure.json', 'rejected-tool-output.json'))
        result = {}
        for root in (self.directory, self.workspace.answers, self.observations):
            if root.resolve() != root or root.is_symlink():
                raise ValueError('duty_execution_linked_evidence_root')
            for p in root.rglob('*') if root.exists() else ():
                if p.resolve() != p.absolute() or p.is_symlink() or p.is_file() and p.stat().st_nlink != 1:
                    raise ValueError('duty_execution_linked_evidence')
                if root == self.directory:
                    relative = p.relative_to(root).as_posix()
                    if relative not in allowed and not re.fullmatch(
                            r'development-host-clock/(policy|[0-9]{4}-(waiting|finished))\.json', relative):
                        raise ValueError('duty_execution_unexpected_file')
                result[str(p)] = sha(p) if p.is_file() else 'directory'
        return result

    def _record(self, name, value):
        self._before()
        write_new_json(self.directory/name, value)
        self._pin()

    def _review(self, duty_name, stage, inputs):
        slot = duty_name+'-'+stage
        prepared = direct.review_request(inputs, duty_name, stage)
        exchange = self._call(slot, prepared)
        response = exchange.response
        if (response.provider != 'zhipu' or response.model != 'glm-5.3'
                or response.finish_reason != 'tool_calls' or (response.content or '').strip()
                or len(response.tool_calls) != 1 or response.tool_calls[0].name != 'submit_report_review'):
            raise ValueError('duty_execution_review_channel')
        raw = compact(dict(response.tool_calls[0].arguments))
        if stage == 'initial':
            opinion = direct.bind(inputs, duty_name, raw)
        else:
            duty.validate(raw, inputs, duty_name)
            opinion = duty.Opinion(duty_name, stage, digest(inputs.data_json),
                digest(inputs.source.report), duty.request_sha(prepared), raw)
        folder = self.directory/slot
        material = dict(kind='opinion', duty=duty_name, review_stage=stage,
            report=inputs.source.report, current_input_json=inputs.data_json,
            request=json.loads(request_bytes(exchange.issued_request)),
            response=json.loads((folder/'response.json').read_bytes()))
        accepted = self._host(slot, 'opinion', 'initial' if stage == 'initial' else 'final', material,
            sha(folder/'issued-request.json'), sha(folder/'response.json'), inputs.source.report)
        return opinion, accepted

    def _run_chain(self):
        opinions, verdicts = [], []
        for name in duty.DUTIES:
            opinion, accepted = self._review(name, 'initial', self.inputs)
            opinions.append(opinion)
            verdicts.append(direct.validate(opinion.raw, self.inputs, name).verdict)
            if not accepted or verdicts[-1] == 'fail':
                return 'initial_rejected'
        if all(v == 'pass' for v in verdicts):
            return 'initial_both_pass_no_edit'
        assembly = direct.preview(self.inputs, opinions)
        preview = dict(report=assembly.report, journal=assembly.journal,
            proposals=[asdict(p) for p in opinions])
        self._record('preview.json', preview)
        material = dict(original_report=self.inputs.source.report,
            current_input_json=self.inputs.data_json, preview=preview,
            policies={d: direct.review_request(self.inputs, d).messages[0].content for d in duty.DUTIES})
        pin = hashlib.sha256(canonical_json(material)).hexdigest()
        if not self._host('compatibility', 'compatibility', 'initial', material, pin, pin, self.inputs.source.report):
            return 'incompatible_opinions'
        material = dict(**material, actual_report=assembly.report,
            application_kind='deterministic-exact-replacements-no-provider')
        edit_pin = hashlib.sha256(canonical_json(material)).hexdigest()
        if not self._host('edit', 'edit', 'revision', material, pin, edit_pin, assembly.report):
            return 'edit_rejected'
        # Recompute rather than accepting text supplied by a judge/callback.
        if direct.preview(self.inputs, opinions) != assembly:
            raise ValueError('direct_patch_preview_changed')
        application = dict(version=VERSION, report=assembly.report,
            report_sha256=digest(assembly.report), preview_sha256=sha(self.directory/'preview.json'),
            accepted_submissions={Path(h['folder']).name: sha(Path(h['folder'])/'submission.json')
                for h in self.handles if h['binding']['key'] in
                ('facts-initial', 'completion-initial', 'compatibility', 'edit')},
            production_admitted=False)
        self._record('application.json', application)
        revised = report_inputs(self.inputs, application['report'])
        for name in duty.DUTIES:
            opinion, accepted = self._review(name, 'fresh', revised)
            if (opinion.request_sha256 != assembly.journal['fresh_request_sha256'][name]
                    or opinion.report_sha256 != application['report_sha256']):
                raise ValueError('direct_patch_fresh_binding')
            if not accepted or duty.validate(opinion.raw, revised, name).verdict != 'pass':
                return 'fresh_rejected'
        return 'development_chain_pass'


# Only this private module's consumers see the candidate class.
_execution.DevelopmentChain = DevelopmentChain
