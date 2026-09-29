"""Read review evidence from the installed Codex host, never from run files.

This client only initializes and reads history. It cannot start a model turn.
The executable is supplied by the operator, not by the candidate run.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import threading
import time
from scripts import review_independence_contract as contract

TASK_KIND = 'riftcoach-independent-review-task-v1'


def _fail(code):
    raise ValueError('codex_review_host_' + code)


class CodexReadOnlyClient:
    """Bounded stdio session using the installed app-server's native schema."""
    METHODS = frozenset(('initialize', 'thread/read', 'thread/turns/list'))

    def __init__(self, executable, *, timeout_seconds=15):
        self.executable = str(Path(executable).resolve(strict=True))
        if not 0 < timeout_seconds <= 60:
            _fail('timeout_invalid')
        self.timeout = timeout_seconds
        self.process = None
        self.messages = queue.Queue()
        self.lock = threading.Lock()
        self.sequence = 0

    def __enter__(self):
        if self.process is not None:
            _fail('session_already_open')
        self.process = subprocess.Popen([self.executable, 'app-server'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding='utf-8',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.request('initialize', dict(clientInfo=dict(name='riftcoach_review_reader', version='0.1'),
                capabilities=dict(experimentalApi=True)))
        except Exception:
            self.close()
            raise
        return self

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    self.messages.put(None)
                    return
        finally:
            self.messages.put(None)

    def request(self, method, params):
        if method not in self.METHODS:
            _fail('method_not_read_only')
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                _fail('session_unavailable')
            self.sequence += 1
            identity = self.sequence
            self.process.stdin.write(json.dumps(dict(id=identity, method=method, params=params)) + chr(10))
            self.process.stdin.flush()
            deadline = time.monotonic() + self.timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    _fail('request_timeout')
                try:
                    message = self.messages.get(timeout=remaining)
                except queue.Empty:
                    _fail('request_timeout')
                if not isinstance(message, dict):
                    _fail('invalid_or_closed_stream')
                if message.get('id') != identity:
                    continue
                if 'error' in message or not isinstance(message.get('result'), dict):
                    _fail('request_failed')
                return message['result']

    def close(self):
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        self.reader.join(timeout=1)
        self.process.stdin.close()
        self.process.stdout.close()
        self.process = None

    def __exit__(self, *_):
        self.close()


def review_task(bound, instructions):
    """Dispatch text; the independent author returns binding + review JSON."""
    if not isinstance(instructions, str) or not instructions.strip():
        _fail('instructions_missing')
    return contract.canonical_json(dict(kind=TASK_KIND, binding=contract.required_binding(bound),
        instructions=instructions)).decode('utf-8')


class CodexHostReviewEventSource:
    """Derive evidence from a child turn, not a locally asserted event.

    event_id is child-thread-id/turn-id/final-message-id. The child must be the
    frozen independent principal, spawned by the frozen root. Its completed
    turn must contain the exact task binding and a final JSON review. Missing
    history through compaction, deletion or an API change fails closed.
    """
    def __init__(self, client, plan):
        if plan.get('host_review_submission_mode') != contract.MODE_V2:
            _fail('mode_not_v2')
        self.primary, self.independent, self.root = contract._registry(plan)
        if self.primary != self.root:
            _fail('primary_not_root_thread')
        self.client = client

    def fetch(self, *, event_id, binding):
        expected = contract.required_binding(binding)
        parts = event_id.split('/') if isinstance(event_id, str) else []
        if len(parts) != 3 or not all(parts) or parts[0] != self.independent:
            _fail('event_reference_invalid')
        child_id, turn_id, message_id = parts
        thread = self.client.request('thread/read', dict(threadId=child_id, includeTurns=False)).get('thread', {})
        source = thread.get('source')
        spawn = source.get('subAgent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
        if (thread.get('id') != self.independent or thread.get('parentThreadId') != self.root
                or spawn.get('parent_thread_id') != self.root):
            _fail('parent_or_author_mismatch')
        cursor, seen = None, set()
        turn = None
        for _ in range(10):
            params = dict(threadId=child_id, limit=50, itemsView='full')
            if cursor:
                params['cursor'] = cursor
            page = self.client.request('thread/turns/list', params)
            matches = [row for row in page.get('data', []) if row.get('id') == turn_id]
            if len(matches) > 1:
                _fail('ambiguous_turn')
            if matches:
                turn = matches[0]
                break
            cursor = page.get('nextCursor')
            if not cursor:
                break
            if cursor in seen:
                _fail('pagination_loop')
            seen.add(cursor)
        if turn is None:
            _fail('turn_unavailable')
        if turn.get('status') != 'completed' or turn.get('itemsView') != 'full' or turn.get('error') is not None:
            _fail('turn_not_completed_full')
        items = turn.get('items', [])
        users = [item for item in items if item.get('type') == 'userMessage']
        finals = [item for item in items if item.get('type') == 'agentMessage' and item.get('phase') == 'final_answer']
        if len(users) != 1 or len(finals) != 1 or finals[0].get('id') != message_id:
            _fail('dispatch_or_final_ambiguous')
        content = users[0].get('content', [])
        if len(content) != 1 or content[0].get('type') != 'text' or not users[0].get('id'):
            _fail('dispatch_format')
        if items.index(users[0]) >= items.index(finals[0]):
            _fail('dispatch_order')
        try:
            task = json.loads(content[0]['text'])
            answer = json.loads(finals[0]['text'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('codex_review_host_review_json_required') from exc
        if (not isinstance(task, dict) or task.get('kind') != TASK_KIND
                or task.get('binding') != expected or not isinstance(answer, dict)
                or answer.get('binding') != expected):
            _fail('dispatch_or_answer_binding')
        review = answer.get('review')
        if not isinstance(review, dict) or any(k in review for k in ('independent_source_event', 'primary_attestation')):
            _fail('review_body_invalid')
        raw = dict(thread={k: thread[k] for k in ('id', 'parentThreadId', 'source')}, turn=turn)
        return dict(schema_version=contract.VERSION, event_kind=contract.EVENT_KIND, state='completed',
            event_id=event_id, dispatch_id=users[0]['id'], author_principal_id=self.independent,
            root_thread_id=self.root, binding=expected, review_sha256=contract.review_digest(review),
            raw_event_sha256=hashlib.sha256(contract.canonical_json(raw)).hexdigest(), review=deepcopy(review))
