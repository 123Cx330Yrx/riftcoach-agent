"""Prospective author workspace and inventory gates for a private Host runner.

Installation changes only the supplied private module. Historical runners and
their inventory/seal rules are never patched. This is an accidental-write
boundary, not an OS sandbox against concurrent hostile filesystem mutation.
"""
from pathlib import Path
import shlex
import sys

from scripts import host_review_task_checkpoint as checkpoint
from app.evaluation.golden_inference_scope_v5 import strict_json

VERSION = 'host-review-workspace-v1'


def quote(value):
    return ("'" + str(value).replace("'", "''") + "'"
            if sys.platform == 'win32' else shlex.quote(str(value)))


class HostReviewWorkspace:
    def __init__(self, *, cwd, python, answers, evidence_roots):
        self.cwd = Path(cwd).absolute()
        self.python = Path(python).absolute()
        self.answers = Path(answers).absolute()
        self.evidence_roots = tuple(Path(p).absolute() for p in evidence_roots)
        self.validate_paths()

    def validate_paths(self):
        if not self.cwd.is_dir() or not self.python.is_file() or not self.evidence_roots:
            raise ValueError('host_workspace_execution_paths')
        # Reject links/junctions in author paths, including nonexistent children
        # whose ancestor was redirected after dispatch.
        if self.answers.resolve() != self.answers:
            raise ValueError('host_workspace_redirected_answer_path')
        for root in self.evidence_roots:
            resolved = root.resolve()
            if self.answers.is_relative_to(resolved) or resolved.is_relative_to(self.answers):
                raise ValueError('host_workspace_answer_inside_evidence')

    def answer_path(self, path, sha):
        self.validate_paths()
        path = Path(path).resolve(strict=True)
        if not any(path.is_relative_to(root.resolve()) for root in self.evidence_roots):
            raise ValueError('host_workspace_unregistered_evidence')
        checkpoint.read(path, sha)
        answer = self.answers / (sha + '.json')
        if answer.resolve() != answer or (answer.exists() and not answer.is_file()):
            raise ValueError('host_workspace_redirected_answer_path')
        if answer.exists() and answer.stat().st_nlink != 1:
            raise ValueError('host_workspace_linked_answer')
        return answer

    def dispatch(self, path, sha, *, document_artifacts=False):
        answer = self.answer_path(path, sha)
        if answer.exists():
            raise ValueError('host_workspace_answer_already_exists')
        self.answers.mkdir(parents=True, exist_ok=True)
        body = checkpoint.dispatch(path, sha, document_artifacts=document_artifacts)
        executable = ('& ' if sys.platform == 'win32' else '') + quote(self.python)
        body = body.replace('python -m ', executable + ' -m ')
        command = (executable + ' -m scripts.host_review_task_checkpoint check-answer'
                   + ' --checkpoint ' + quote(Path(path).resolve())
                   + ' --checkpoint-sha ' + sha + ' --answer-file ' + quote(answer))
        return (f'Verified working directory (tool workdir): {self.cwd}\n'
                f'Verified Python executable: {self.python}\n'
                'Use these absolute paths literally; do not append backend.\n'
                + body + '\n'
                f'Your exclusive author-answer file: {answer}\n'
                'Write your own answer only at that path, create-only (never overwrite). '
                'Do not write any file into the run evidence directory. '
                'Before your single native final, reread the SAME checkpoint and SHA, '
                'then validate the exact author file with:\n' + command + '\n'
                'Return that file\'s own complete multiline JSON as your only native final. '
                'Do not regenerate, trim or change the judgment after checking it.\n')

    def check_submission_answer(self, folder, submission):
        path = Path(folder) / 'task-checkpoint.json'
        sha = checkpoint.digest(path.read_bytes())
        answer = self.answer_path(path, sha)
        raw = answer.read_bytes()
        checkpoint.check_answer(path, sha, raw)
        independent = submission['independent']
        expected = dict(binding=independent['binding'], review={
            k: v for k, v in independent.items() if k != 'independent_source_event'})
        if strict_json(raw.decode('utf-8')) != expected:
            raise ValueError('host_workspace_answer_native_mismatch')

    def install(self, runner):
        """Wire observe/submit/replay/seal, keeping the native importer intact."""
        from types import SimpleNamespace
        if getattr(runner, '_host_workspace_installed', False):
            raise ValueError('host_workspace_already_installed')
        runner._host_workspace_installed = True
        old_submit, old_validate = runner.submit, runner.validate_submission
        old_observe, old_atomic = runner.observe, runner.atomic_new
        runner.checkpoint = SimpleNamespace(**{name: getattr(checkpoint, name)
            for name in ('read', 'publish', 'check_answer', 'digest')}, dispatch=self.dispatch)

        def inventory(directory):
            self.validate_paths()
            plan = runner.read(Path(directory) / 'plan.json')['preparation_plan']
            runner.validate_inventory(directory, plan)
            for cell in plan['cells']:
                folder = Path(directory) / cell['key'].replace(':', '-')
                submitted = folder / 'review-submission.json'
                if submitted.exists():
                    self.check_submission_answer(folder, runner.read(submitted))

        def submit(directory, *args, **kwargs):
            # Reject extra files before native IO or publishing any decision.
            inventory(directory)
            return old_submit(directory, *args, **kwargs)

        def validate(directory, key, submission, event_source):
            inventory(directory)
            self.check_submission_answer(Path(directory) / key.replace(':', '-'), submission)
            return old_validate(directory, key, submission, event_source)

        def atomic(path, value):
            path = Path(path)
            if path.name == 'review-submission.json':
                # Called inside the existing submission/close OS lock, after
                # native import. Catch contamination during that native read.
                inventory(path.parent.parent)
                self.check_submission_answer(path.parent, value)
            return old_atomic(path, value)

        def observe(directory, plan, rows, provider, event_source, **kwargs):
            before = kwargs.pop('before_send', lambda: None)

            def before_send():
                inventory(directory)
                before()
                inventory(directory)

            class GuardedProvider:
                def chat(_, request, transport_directory):
                    # Also check at the last handoff before transport can send,
                    # after the runner has created material/started records.
                    inventory(directory)
                    return provider.chat(request, transport_directory)

            return old_observe(directory, plan, rows, GuardedProvider(), event_source,
                               before_send=before_send, **kwargs)

        runner.submit, runner.validate_submission = submit, validate
        runner.atomic_new, runner.observe = atomic, observe
        return self
