"""Prospective initial/edit/final evidence gates; no paid execution CLI.

Legacy state machine and replay run in private namespaces. The public modules,
closed evidence, workflow, policies and budget contracts are never patched.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from scripts.full_chain_modules import private_module
from scripts.host_review_workspace import HostReviewWorkspace
from scripts import full_chain_observed_transport as observed
from scripts import host_review_task_checkpoint as checkpoint
from scripts.run_scope_resolution_diagnostic import submission_close_gate

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'full-chain-evidence-v1'
SOURCES = ('scripts/full_chain_evidence.py', 'scripts/full_chain_modules.py',
           'scripts/full_chain_observed_transport.py', 'scripts/host_review_workspace.py',
           'scripts/stream_observation.py')
STAGE_FILES = {'issued-request.json', 'response.json', 'stage.json', 'review-required.json',
    'independent-task.json', 'task-checkpoint.json', 'dispatch.txt', 'review-submission.json',
    'host-reviews.json', 'operator-abort.json', 'send-start.json', 'send-finished.json',
    'evidence-guard.json'}
STREAM_FILES = {'reservation.json', 'result.json', 'progress.json', 'progress.tmp',
                'failure.json', 'rejected-tool-output.json'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FullChainEvidence:
    def __init__(self, *, directory, answers, observations, cwd=ROOT, python=sys.executable):
        self.directory = Path(directory).absolute()
        self.observations = Path(observations).absolute()
        self.workspace = HostReviewWorkspace(cwd=cwd, python=python, answers=answers,
            evidence_roots=(ROOT / 'data/runs', self.directory))
        self.validate_paths()
        dependencies = {}
        self.runner = private_module(ROOT / 'scripts/run_full15_resumption_candidate.py', dependencies)
        dependencies['scripts.run_full15_resumption_candidate'] = self.runner
        self.evidence = private_module(ROOT / 'scripts/full15_resumption_evidence.py', dependencies)
        dependencies['scripts.full15_resumption_evidence'] = self.evidence
        self._prepare = self.runner.prepare
        self.runner.prepare = self.prepare
        self._install()

    def validate_paths(self):
        self.workspace.validate_paths()
        paths = (self.directory, self.workspace.answers, self.observations)
        if any(p.resolve() != p for p in paths):
            raise ValueError('full_chain_redirected_path')
        for i, a in enumerate(paths):
            for b in paths[i + 1:]:
                if a.is_relative_to(b) or b.is_relative_to(a):
                    raise ValueError('full_chain_overlapping_paths')
        if self.observations.is_relative_to((ROOT / 'data/runs').resolve()):
            raise ValueError('full_chain_observation_inside_run')

    def prepare(self, *, root_thread_id, independent_thread_id, root=ROOT,
                selection='full15', timing_mode='time600'):
        if selection != 'full15' or timing_mode != 'time600':
            raise ValueError('full_chain_scope')
        plan = self._prepare(root_thread_id=root_thread_id, independent_thread_id=independent_thread_id,
                             root=root, selection=selection, timing_mode=timing_mode)
        plan.update(kind=VERSION, run_id='document-full-chain-prospective-v1',
            execution_authorized=False, execution_ready=False,
            evidence_paths=dict(directory=str(self.directory), answers=str(self.workspace.answers),
                observations=str(self.observations), cwd=str(self.workspace.cwd), python=str(self.workspace.python)),
            observation_contract=observed.VERSION, author_workspace_contract='host-review-workspace-v1')
        plan['source_sha256'].update({p: sha(ROOT / p) for p in SOURCES})
        return plan

    def execution_paths_preflight(self):
        self.validate_paths()
        probe = subprocess.run([str(self.workspace.python), '-B', '-c',
            'import json,os,sys; from pathlib import Path; import scripts.full_chain_evidence as m; '
            'print(json.dumps(dict(cwd=os.getcwd(),python=sys.executable,module=str(Path(m.__file__).resolve()))))'],
            cwd=self.workspace.cwd, capture_output=True, text=True, encoding='utf-8', timeout=30, check=True)
        value = json.loads(probe.stdout)
        if (Path(value['cwd']).resolve() != ROOT.resolve()
                or Path(value['python']).resolve() != self.workspace.python.resolve()
                or Path(value['module']).resolve() != (ROOT/'scripts/full_chain_evidence.py').resolve()):
            raise ValueError('full_chain_startup_identity')
        return dict(value, provider_calls=0, execution_ready=False)

    def _inventory(self):
        self.validate_paths()
        plan = self.evidence.load_plan(self.directory)
        allowed = {'plan.json', 'result.json', 'submission-close.lock'}
        for key in plan['sequence']:
            arm = key.replace(':', '-')
            allowed.update(f'{arm}/{f}' for f in ('source.json', 'case-budget-start.json',
                                                'case-budget-finished.json', 'case-result.json'))
            for ordinal, stage in enumerate(self.runner.STAGES, 1):
                allowed.update(f'{arm}/{stage}/{f}' for f in STAGE_FILES)
                transport = f'transport/{arm}'
                allowed.update(f'{transport}/{f}-{ordinal:03d}.json' for f in ('call', 'call-result'))
                role = 'generation' if stage == 'revision' else 'review'
                allowed.update(f'{transport}/{role}/{f}-{ordinal:03d}.json' for f in ('request', 'response'))
                allowed.update(f'{transport}/{role}/stream-{ordinal:03d}/{f}' for f in STREAM_FILES)
        allowed.add('development-host-clock/policy.json')
        for ordinal in range(1, len(plan['sequence']) * 3 + 1):
            allowed.update(f'development-host-clock/{ordinal:04d}-{f}.json' for f in ('waiting', 'finished'))
        directories = {str(Path(p).parent).replace('\\', '/') for p in allowed}
        for p in tuple(directories):
            directories.update(v.as_posix() for v in Path(p).parents)
        for path in self.directory.rglob('*'):
            relative = path.relative_to(self.directory).as_posix()
            if path.is_symlink() or path.resolve() != path.absolute():
                raise ValueError('full_chain_linked_evidence')
            if path.is_file():
                if relative not in allowed or path.stat().st_nlink != 1:
                    raise ValueError('full_chain_unexpected_run_file')
            elif relative not in directories:
                raise ValueError('full_chain_unexpected_run_directory')
        observations = []
        expected_observation_dirs = set()
        for key in plan['sequence']:
            arm = key.replace(':', '-')
            for ordinal, stage in enumerate(self.runner.STAGES, 1):
                role = 'generation' if stage == 'revision' else 'review'
                raw = self.directory / f'transport/{arm}/{role}/request-{ordinal:03d}.json'
                if raw.exists():
                    worker = raw.parent / f'stream-{ordinal:03d}'
                    expected_observation_dirs.add(hashlib.sha256(str(worker.resolve()).encode()).hexdigest())
                    complete = (raw.parent / f'response-{ordinal:03d}.json').exists()
                    complete |= (self.directory / arm / stage / 'response.json').exists()
                    record = observed.verify_observation(worker, raw.read_bytes(),
                        observation_root=self.observations, complete_required=complete,
                        transport_id=self.runner.transport_for_stage(stage, plan))
                    observations.append(record)
        if self.observations.exists():
            for path in self.observations.iterdir():
                if not path.is_dir() or path.name not in expected_observation_dirs:
                    raise ValueError('full_chain_orphan_observation')
            for path in self.observations.rglob('*'):
                if (path.is_symlink() or path.resolve() != path.absolute()
                        or path.is_file() and path.stat().st_nlink != 1):
                    raise ValueError('full_chain_linked_observation')
        for key in plan['sequence']:
            for stage in self.runner.STAGES:
                folder = self.directory / key.replace(':', '-') / stage
                submitted = folder / 'review-submission.json'
                if submitted.exists():
                    self.workspace.check_submission_answer(folder, self.evidence.read(submitted))
                    pinned = self.evidence.read(folder / 'evidence-guard.json')
                    if pinned != self._guard_record(folder, observations[:pinned['observation_count']]):
                        raise ValueError('full_chain_submitted_evidence_changed')
        return observations

    @contextmanager
    def gate(self):
        self.evidence.load_plan(self.directory)  # Reject legacy/wrong runs before opening a lock.
        # Closed replay is strictly read-only; do not even touch the lock file.
        if (self.directory / 'result.json').exists():
            yield
        else:
            with submission_close_gate(self.directory):
                yield

    def check(self):
        with self.gate():
            return self._inventory()

    def _guard_record(self, folder, observations):
        path = folder / 'task-checkpoint.json'
        pin = sha(path)
        answer = self.workspace.answer_path(path, pin)
        return dict(version=VERSION, checkpoint_sha256=pin, author_sha256=sha(answer),
            observation_count=len(observations), observations=observations)

    def _install(self):
        runner, evidence = self.runner, self.evidence
        old_submit, old_write, old_observe = evidence.submit, runner._write_json, runner.observe
        old_validate, old_replay = runner._validate_reviews, evidence.replay
        old_load_plan = evidence.load_plan
        old_recorded = runner.RecordedProvider

        def load_plan(directory):
            self._same(directory)
            return old_load_plan(directory)
        evidence.load_plan = load_plan

        def write(path, value):
            path = Path(path)
            if re.fullmatch(r'\.submission-[0-9a-f]+\.tmp', path.name):
                # Legacy submit calls this while holding the submission lock.
                observations = self._inventory()
                self.workspace.check_submission_answer(path.parent, value)
                old_write(path.parent / 'evidence-guard.json', self._guard_record(path.parent, observations))
            return old_write(path, value)

        def submit(directory, key, stage, *args, **kwargs):
            self._same(directory)
            try:
                self.check()
                return old_submit(directory, key, stage, *args, **kwargs)
            except (ValueError, OSError):
                folder = self.directory / key.replace(':', '-') / stage
                if not (folder / 'review-submission.json').exists():
                    try:
                        evidence.abort(directory, key, stage, 'operator_stop')
                    except (ValueError, OSError):
                        pass
                raise

        def validate(submission, value, bound, plan, event_source, **kwargs):
            self.check()
            folder = self.directory / bound['key'].replace(':', '-') / bound['stage']
            self.workspace.check_submission_answer(folder, submission)
            return old_validate(submission, value, bound, plan, event_source, **kwargs)

        class Recorded(old_recorded):
            def chat(inner, request):
                self.check()
                return super().chat(request)

        def observe(factory, directory, plan, *, event_source, adjudicate=None, before_send=lambda: None):
            self._same(directory)
            def before():
                self.check()
                before_send()
                self.check()
            return old_observe(factory, directory, plan, event_source=event_source,
                adjudicate=self.wait_reviews if adjudicate is None else adjudicate, before_send=before)

        def replay(directory, *, event_source):
            self._same(directory)
            observations = self.check()
            before = self.snapshot()
            value = old_replay(directory, event_source=event_source)
            if before != self.snapshot():
                raise ValueError('full_chain_replay_mutation')
            value.update(kind=VERSION + '-result', body_free_observations=observations,
                author_evidence={p.relative_to(self.directory).as_posix():evidence.read(p)
                                 for p in self.directory.glob('*/*/evidence-guard.json')})
            return value

        def seal(directory, output, *, event_source):
            output = Path(output).absolute()
            roots = (*self.workspace.evidence_roots, self.workspace.answers, self.observations)
            if output.resolve() != output or any(output.is_relative_to(root.resolve()) for root in roots):
                raise ValueError('full_chain_seal_inside_evidence')
            value = replay(directory, event_source=event_source)
            old_write(output, value)
            return dict(sealed=True, path=str(output), sha256=sha(output), provider_calls=0)

        runner._write_json, runner._validate_reviews, runner.RecordedProvider = write, validate, Recorded
        runner.observe, runner.wait_reviews = observe, self.wait_reviews
        evidence.submit, evidence.replay, evidence.seal = submit, replay, seal

    def _same(self, directory):
        if Path(directory).absolute() != self.directory:
            raise ValueError('full_chain_directory_changed')

    def snapshot(self):
        return {str(p):sha(p) for root in (self.directory, self.workspace.answers, self.observations)
                for p in root.rglob('*') if p.is_file()}

    def publish_task(self, path):
        self.check()
        path = Path(path).absolute()
        plan = self.evidence.load_plan(self.directory)
        allowed = {self.directory / key.replace(':','-') / stage / 'review-required.json'
                   for key in plan['sequence'] for stage in self.runner.STAGES}
        if path not in allowed:
            raise ValueError('full_chain_task_path')
        required = self.evidence.read(path)
        bound, folder = required['binding'], Path(path).parent
        raw = self.evidence.task(self.directory, bound['key'], bound['stage'])
        task = folder / 'independent-task.json'
        with task.open('x', encoding='utf-8') as stream:
            stream.write(raw + '\n')
        pin = checkpoint.publish(folder / 'task-checkpoint.json', task,
            self.evidence.load_plan(self.directory)['review_principals']['independent']['principal_id'])
        dispatch = self.workspace.dispatch(folder / 'task-checkpoint.json', pin)
        with (folder / 'dispatch.txt').open('x', encoding='utf-8') as stream:
            stream.write(dispatch)
        return pin

    def wait_reviews(self, path, remaining):
        self.publish_task(path)
        folder = Path(path).parent
        deadline = time.monotonic() + remaining
        while time.monotonic() < deadline:
            self.check()
            abort = folder / 'operator-abort.json'
            if abort.exists():
                self.runner.validate_abort(self.evidence.read(abort), self.evidence.read(path)['binding'])
                raise ValueError('full15_operator_abort')
            if (folder / 'review-submission.json').exists():
                return self.evidence.read(folder / 'review-submission.json')
            time.sleep(.25)
        raise ValueError('full15_host_deadline')

    def factory(self, *, generator_settings, reviewer_settings):
        from app.evaluation.document_review_timed_transport import TimedDocumentRouter
        from app.evaluation.golden_coarse_source_projection import VERSION as projection
        from app.evaluation import golden_stream_bridge as legacy
        bridge = observed.isolated_bridge(observation_root=self.observations)
        child = bridge.run_child
        def guarded_child(*args, **kwargs):
            self.check()  # Last boundary after reservations, before process IO.
            return child(*args, **kwargs)
        bridge.run_child = guarded_child
        providers = private_module(ROOT / 'app/runtime/receipted_provider_factory.py',
            {'app.evaluation.golden_stream_bridge': bridge})
        class Factory(providers.RunScopedRoleReceiptedProviderFactory):
            def _build(inner, directory):
                def provider(settings, role, transport):
                    return providers.RoleReceiptedStreamProvider(settings=settings, directory=directory / role,
                        task_directory=directory, transport_id=transport)
                return TimedDocumentRouter(provider(generator_settings, 'generation', legacy.TIMED_FLASH_TRANSPORT_ID),
                    provider(reviewer_settings, 'review', legacy.TIMED_REVIEW_TRANSPORT_ID), source_projection=projection)
        return Factory(generator_settings=generator_settings, reviewer_settings=reviewer_settings,
            transport_root=self.directory / 'transport', source_projection=projection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'task', 'submit', 'abort', 'replay', 'seal'))
    for name in ('directory', 'answers', 'observations', 'python', 'cwd'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--root-thread-id')
    parser.add_argument('--independent-thread-id')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--key')
    parser.add_argument('--stage', choices=('initial', 'revision', 'final'))
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--event-id')
    parser.add_argument('--checkpoint-sha')
    parser.add_argument('--codex-executable', type=Path)
    parser.add_argument('--reason', choices=('reviewer_unavailable', 'routing_failure', 'operator_stop'))
    args = parser.parse_args()
    session = FullChainEvidence(**{k:getattr(args, k) for k in ('directory','answers','observations','python','cwd')})
    evidence, runner = session.evidence, session.runner
    if args.action == 'prepare':
        if not all((args.root_thread_id, args.independent_thread_id, args.output)):
            parser.error('prepare requires principal IDs and output')
        session.execution_paths_preflight()
        runner._write_json(args.output, session.prepare(root_thread_id=args.root_thread_id,
            independent_thread_id=args.independent_thread_id))
        print(json.dumps(dict(execution_ready=False, provider_calls=0)))
        return
    if args.action in ('task', 'submit', 'abort') and not all((args.key, args.stage)):
        parser.error('key and stage required')
    if args.action == 'task':
        session.check()
        print(evidence.task(args.directory, args.key, args.stage)); return
    if args.action == 'abort':
        if not args.reason: parser.error('reason required')
        print(runner.compact(evidence.abort(args.directory, args.key, args.stage, args.reason))); return
    if not args.codex_executable: parser.error('codex-executable required')
    plan = evidence.load_plan(args.directory)
    with runner.CodexReadOnlyClient(args.codex_executable) as client:
        source = runner.CodexHostReviewEventSource(client, plan)
        if args.action == 'submit':
            if not all((args.notes, args.event_id, args.checkpoint_sha)): parser.error('submission arguments required')
            value = evidence.submit(args.directory, args.key, args.stage, evidence.read(args.notes),
                                    args.event_id, source, args.checkpoint_sha)
        elif args.action == 'seal':
            if not args.output: parser.error('output required')
            value = evidence.seal(args.directory, args.output, event_source=source)
        else:
            value = evidence.replay(args.directory, event_source=source)
    print(runner.compact(value))


if __name__ == '__main__':
    main()
