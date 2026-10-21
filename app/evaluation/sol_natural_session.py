"""Durable candidate operations, separate from original provider receipts.

This is an execution substrate, not a paid launcher or model qualification.
An interrupted intent is never an authorization to repeat IO. Replay consumes
only committed operations; a missing result requires receipt reconciliation.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from app.evaluation.golden_journal import write_new_json
from app.evaluation.natural_duty_workflow import NaturalDutySuspended


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def tree(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('session_symlink')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


@contextmanager
def exclusive(path):
    """Kernel-owned lock: process exit releases ownership; PID reuse is irrelevant."""
    handle = Path(path).open('a+b')
    locked = False
    try:
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        yield
    except OSError as error:
        if not locked:
            raise ValueError('session_executor_active') from error
        raise
    finally:
        if locked:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


class SessionPaused(NaturalDutySuspended):
    """Controlled boundary before IO, not a failed business evaluation."""


class SessionBlocked(NaturalDutySuspended):
    """Integrity/recovery failure must escape ordinary model/tool error recovery."""


class CandidateSession:
    VERSION = 'sol-natural-session-v1'

    def __init__(self, root, *, binding, transport_root, journal_root,
                 guard_sha=None, checkpoint_sha=None, read_only=False,
                 checkpoint_sink=lambda value: None, before_new_model=None,
                 max_new_models=None, clock=time.monotonic, reconcile=False, continuation=None):
        self.root = Path(root).resolve()
        self.transport_root, self.journal_root = Path(transport_root).resolve(), Path(journal_root).resolve()
        roots = (self.root, self.transport_root, self.journal_root)
        if any(a.is_relative_to(b) or b.is_relative_to(a)
               for i, a in enumerate(roots) for b in roots[i+1:]):
            raise ValueError('session_roots_overlap')
        self.binding = json.loads(canonical(binding))
        self.continuation = continuation
        if continuation is not None and self.binding.get('continuation_sha256') != digest(canonical(continuation)):
            raise ValueError('launch_continuation_binding')
        self.guard_sha, self.checkpoint_sha = guard_sha, checkpoint_sha
        self.read_only, self.sink = read_only, checkpoint_sink
        self.reconciling = reconcile
        if read_only and reconcile:
            raise ValueError('session_reconcile_is_not_read_only')
        self.before_new_model, self.max_new_models = before_new_model, max_new_models
        self.clock, self._mutex = clock, threading.RLock()
        self.cursor = self.new_models = 0
        self.review_gate = None
        self._open = False

    def __enter__(self):
        if self.continuation is not None:
            from scripts.sol_natural_continuation import verify_parent
            verify_parent(self.continuation)
        self.root.parent.mkdir(parents=True, exist_ok=True)
        if self.read_only and not self.root.exists():
            raise ValueError('session_missing')
        self._lock = exclusive(self.root.with_name(self.root.name+'.lock'))
        self._lock.__enter__()
        try:
            if not self.root.exists():
                if self.guard_sha is not None or self.checkpoint_sha is not None or self.reconciling:
                    raise ValueError('session_missing')
                if tree(self.transport_root) or tree(self.journal_root):
                    raise ValueError('session_existing_evidence')
                self.root.mkdir()
                (self.root/'operations').mkdir()
                (self.root/'checkpoints').mkdir()
                write_new_json(self.root/'guard.json', dict(version=self.VERSION, binding=self.binding,
                    transport_root=str(self.transport_root), journal_root=str(self.journal_root),
                    production_admitted=False, publication_allowed=False))
                self.guard_sha = digest((self.root/'guard.json').read_bytes())
                self.active_before = 0.0
                self.segment_started = self.clock()
                self._open = True
                self._checkpoint('created')
                if self.continuation is not None:
                    from scripts.sol_natural_continuation import import_prefix
                    import_prefix(self)
            else:
                if not self.guard_sha or not self.checkpoint_sha:
                    raise ValueError('session_original_roots_required')
                self._load()
                if self.continuation is not None and not (self.root/'continuation-import.json').is_file():
                    raise SessionBlocked('launch_continuation_import_incomplete')
                self._open = True
            self.operations = sorted((self.root/'operations').glob('*-intent.json'))
            return self
        except BaseException:
            self._open = False
            self._lock.__exit__(None, None, None)
            raise

    def __exit__(self, kind, error, tb):
        try:
            # No invented final/closure on failure. The pinned pending intent
            # remains visible and prevents another send after process recovery.
            if not self.read_only and not self.reconciling and (kind is None or kind is SessionPaused):
                self.verify()
                self._checkpoint('paused' if kind is SessionPaused else 'boundary')
        finally:
            self._open = False
            self._lock.__exit__(kind, error, tb)

    @property
    def active_seconds(self):
        return self.active_before + max(0.0, self.clock()-self.segment_started)

    def _inventory(self):
        own = tree(self.root)
        own = {k: v for k, v in own.items() if not k.startswith('checkpoints/')}
        return dict(session=own, transport=tree(self.transport_root), journal=tree(self.journal_root))

    def _load(self):
        if digest((self.root/'guard.json').read_bytes()) != self.guard_sha:
            raise ValueError('session_guard_changed')
        guard = json.loads((self.root/'guard.json').read_bytes())
        if guard != dict(version=self.VERSION, binding=self.binding,
                         transport_root=str(self.transport_root), journal_root=str(self.journal_root),
                         production_admitted=False, publication_allowed=False):
            raise ValueError('session_identity_changed')
        previous = self.guard_sha
        paths = sorted((self.root/'checkpoints').glob('*.json'))
        if not paths:
            raise ValueError('session_checkpoint_missing')
        for index, path in enumerate(paths, 1):
            value = json.loads(path.read_bytes())
            if (path.name != f'{index:04d}.json' or value['previous_sha256'] != previous
                    or value['guard_sha256'] != self.guard_sha):
                raise ValueError('session_checkpoint_chain_changed')
            previous = digest(path.read_bytes())
        if previous != self.checkpoint_sha:
            raise ValueError('session_latest_checkpoint_required')
        self.expected = value['inventory']
        self.checkpoint_pins = tree(self.root/'checkpoints')
        self.active_before = value['active_seconds']
        if type(self.active_before) not in (int, float) or not 0 <= self.active_before < float('inf'):
            raise ValueError('session_clock_invalid')
        self.segment_started = self.clock()
        self.verify()

    def verify(self):
        if self.continuation is not None:
            from scripts.sol_natural_continuation import verify_parent
            verify_parent(self.continuation)
        actual = self._inventory()
        unchanged = (actual == self.expected)
        if self.reconciling:
            unchanged = (actual['session'] == self.expected['session']
                and actual['journal'] == self.expected['journal']
                and all(actual['transport'].get(p) == sha for p, sha in self.expected['transport'].items()))
        if not unchanged:
            raise SessionBlocked('session_evidence_changed_or_uncommitted')
        if tree(self.root/'checkpoints') != self.checkpoint_pins:
            raise SessionBlocked('session_checkpoint_changed')

    def _checkpoint(self, phase):
        current = self._inventory()
        if hasattr(self, 'expected'):
            if any(current[group].get(path) != sha for group, files in self.expected.items()
                   for path, sha in files.items()):
                raise SessionBlocked('session_prior_evidence_changed')
            if tree(self.root/'checkpoints') != self.checkpoint_pins:
                raise SessionBlocked('session_checkpoint_changed')
        paths = list((self.root/'checkpoints').glob('*.json'))
        value = dict(version=self.VERSION, phase=phase, guard_sha256=self.guard_sha,
            previous_sha256=self.checkpoint_sha or self.guard_sha,
            active_seconds=self.active_seconds, inventory=current)
        path = self.root/'checkpoints'/f'{len(paths)+1:04d}.json'
        write_new_json(path, value)
        self.expected = value['inventory']
        self.checkpoint_sha = digest(path.read_bytes())
        self.checkpoint_pins = tree(self.root/'checkpoints')
        self.sink(dict(guard_sha256=self.guard_sha, checkpoint_sha256=self.checkpoint_sha,
                       checkpoint=str(path), phase=phase))

    def operation(self, kind, request, action):
        """Append once or return the exact committed result without calling action."""
        with self._mutex:
            if not self._open:
                raise SessionBlocked('session_not_owned')
            if self.reconciling:
                raise SessionBlocked('session_reconciliation_required')
            self.verify()
            if self.continuation is not None:
                from scripts.sol_natural_continuation import verify_frontier
                verify_frontier(self, kind, request)
            ordinal = self.cursor + 1
            first_pin = self.binding.get('first_request_sha256')
            if kind == 'model' and ordinal == 1 and first_pin is not None:
                if digest(canonical(request)) != first_pin:
                    raise SessionBlocked('session_first_request_changed')
            intent = dict(ordinal=ordinal, kind=kind, request=json.loads(canonical(request)))
            path = self.root/'operations'/f'{ordinal:04d}-intent.json'
            result_path = self.root/'operations'/f'{ordinal:04d}-result.json'
            if path.exists():
                if json.loads(path.read_bytes()) != intent:
                    raise SessionBlocked('session_replay_request_changed')
                if not result_path.exists():
                    raise SessionBlocked('session_unresolved_intent_no_resend')
                result = json.loads(result_path.read_bytes())
                if result['intent_sha256'] != digest(path.read_bytes()):
                    raise SessionBlocked('session_result_binding')
                self.cursor += 1
                return result['value'], True
            if self.read_only:
                raise SessionPaused('session_replay_frontier')
            if (self.root/'terminal.json').exists() or (self.root/'seal.json').exists():
                raise SessionBlocked('session_closed')
            if kind == 'model':
                if self.max_new_models is not None and self.new_models >= self.max_new_models:
                    raise SessionPaused('session_model_boundary')
                if self.before_new_model is None:
                    raise SessionBlocked('session_send_preflight_required')
                self.before_new_model()
                self.verify()
                if self.review_gate is not None:
                    self.review_gate.verify_prior()
            write_new_json(path, intent)
            self._checkpoint('intent')
            try:
                value = action()
            except BaseException as error:
                # Preserve all original failed/partial transport files. Their
                # presence cannot reset the intent or create another call slot.
                self._checkpoint('unresolved')
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise SessionPaused('session_interrupted_pending_reconciliation') from error
                raise
            write_new_json(result_path, dict(intent_sha256=digest(path.read_bytes()), value=value))
            self.cursor += 1
            if kind == 'model':
                self.new_models += 1
            self._checkpoint('committed')
            return json.loads(canonical(value)), False

    def close(self, value):
        self.verify()
        if not self._open or self.reconciling or self.read_only or self.cursor != len(list((self.root/'operations').glob('*-intent.json'))):
            raise SessionBlocked('session_close_before_frontier')
        if any(not p.with_name(p.name.replace('-intent', '-result')).exists()
               for p in (self.root/'operations').glob('*-intent.json')):
            raise SessionBlocked('session_unresolved_intent_no_close')
        write_new_json(self.root/'terminal.json', dict(value=value, publication_allowed=False,
                                                     production_admitted=False))
        self._checkpoint('closed')

    def capture_attempt(self, ordinal, issued_raw, budget, retry_pending):
        """Pin the post-budget request before any provider start/IO."""
        if not self._open or self.read_only or self.reconciling:
            raise SessionBlocked('session_attempt_not_owned')
        intent_path = self.root/'operations'/f'{self.cursor+1:04d}-intent.json'
        intent = json.loads(intent_path.read_bytes())
        if intent['kind'] != 'model':
            raise SessionBlocked('session_attempt_without_model_intent')
        # A retry may have just produced failed receipt files. Preserve that
        # attempt before reserving another one; old files cannot change.
        self._checkpoint('attempt_boundary')
        self.before_new_model()
        self.verify()
        if self.review_gate is not None:
            self.review_gate.verify_prior()
        path = self.root/'operations'/f'attempt-{ordinal:03d}.json'
        write_new_json(path, dict(intent_sha256=digest(intent_path.read_bytes()),
            ordinal=ordinal, issued_raw=issued_raw, budget_before=budget,
            retry_pending=retry_pending, active_seconds=self.active_seconds))
        self._checkpoint('attempt_reserved')

    def reconcile_completed(self):
        """Import a completed original response after parent loss; never send IO."""
        if not self._open or not self.reconciling:
            raise SessionBlocked('session_reconcile_mode_required')
        self.verify()
        if (self.root/'terminal.json').exists() or (self.root/'seal.json').exists():
            raise SessionBlocked('session_closed')
        intents = sorted((self.root/'operations').glob('*-intent.json'))
        pending = [p for p in intents if not p.with_name(p.name.replace('-intent', '-result')).exists()]
        if len(pending) != 1 or pending[0] != intents[-1]:
            raise SessionBlocked('session_single_pending_model_required')
        path = pending[0]
        intent = json.loads(path.read_bytes())
        if intent['kind'] != 'model':
            raise SessionBlocked('session_pending_model_required')
        attempts = [json.loads(p.read_bytes()) for p in sorted((self.root/'operations').glob('attempt-*.json'))]
        if not attempts or attempts[-1]['intent_sha256'] != digest(path.read_bytes()):
            raise SessionBlocked('session_issued_request_missing')
        from app.runtime.sol_session_receipts import recover_success
        before = tree(self.transport_root)
        value, elapsed, allowed = recover_success(self.transport_root, intent, attempts[-1])
        if set(before)-set(self.expected['transport'])-allowed:
            raise SessionBlocked('session_unrecognized_recovery_files')
        if tree(self.transport_root) != before:
            raise SessionBlocked('session_receipts_changed_during_recovery')
        write_new_json(path.with_name(path.name.replace('-intent', '-result')),
                       dict(intent_sha256=digest(path.read_bytes()), value=value))
        self.active_before = max(self.active_before, attempts[-1]['active_seconds'] + elapsed)
        self.reconciling = False
        self._checkpoint('original_response_reconciled')
        return dict(reconciled_ordinal=attempts[-1]['ordinal'], provider_requests=0,
                    new_usage_not_inferred=True, checkpoint_sha256=self.checkpoint_sha)

    def status(self):
        self.verify()
        paths = sorted((self.root/'operations').glob('*-intent.json'))
        pending = [p.name for p in paths if not p.with_name(p.name.replace('-intent', '-result')).exists()]
        return dict(operations=len(paths), unresolved=pending,
            closed=(self.root/'terminal.json').exists(), guard_sha256=self.guard_sha,
            checkpoint_sha256=self.checkpoint_sha, publication_allowed=False, production_admitted=False)
