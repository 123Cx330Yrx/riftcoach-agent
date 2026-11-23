"""Read review evidence from the installed Codex host, never from run files.

This client only initializes and reads history. It cannot start a model turn.
The executable is supplied by the operator, not by the candidate run.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
from scripts import review_independence_contract as contract

TASK_KIND = 'riftcoach-independent-review-task-v1'


def _fail(code):
    raise ValueError('codex_review_host_' + code)


def _resolved_local_path(value, *, strict=False):
    # Resolve junctions/symlinks before the containment check. Windows native
    # APIs may spell the same drive/UNC path with an extended-length prefix.
    path = Path(value).resolve(strict=strict)
    text = str(path)
    if os.name == 'nt':
        if text.startswith('\\\\?\\UNC\\'):
            path = Path('\\\\' + text[8:])
        elif text.startswith('\\\\?\\') and len(text) > 6 and text[5:7] == ':\\':
            path = Path(text[4:])
    return path


class CodexReadOnlyClient:
    """Bounded stdio session using the installed app-server's native schema."""
    METHODS = frozenset(('initialize', 'thread/read', 'thread/turns/list'))

    def __init__(self, executable, *, timeout_seconds=15, session_root=None):
        self.executable = str(Path(executable).resolve(strict=True))
        # Operator/host configuration, never a path accepted from a run plan.
        self.session_root = _resolved_local_path(session_root if session_root is not None else
            Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'sessions')
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

    def _collaboration_records(self, thread):
        """Read only the backing file selected by the native host thread."""
        try:
            path = _resolved_local_path(thread['path'], strict=True)
            if (not path.is_relative_to(self.session_root) or path.suffix != '.jsonl'
                    or path.stat().st_size > 128 * 1024 * 1024):
                _fail('rollout_path_invalid')
            records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise ValueError('codex_review_host_rollout_unavailable') from exc
        if not records or records[0].get('type') != 'session_meta':
            _fail('rollout_session_missing')
        meta = records[0].get('payload', {})
        spawn = thread['source']['subAgent']['thread_spawn']
        agent_path = spawn.get('agent_path')
        if (meta.get('id') != thread['id'] or meta.get('parent_thread_id') != thread['parentThreadId']
                or meta.get('source', {}).get('subagent', {}).get('thread_spawn') != spawn
                or not isinstance(agent_path, str) or not agent_path.startswith('/root/')
                or meta.get('agent_path') != agent_path):
            _fail('rollout_session_mismatch')
        return records, meta

    @staticmethod
    def _collaboration_text(payload, thread):
        agent_path = thread['source']['subAgent']['thread_spawn']['agent_path']
        parent_path = agent_path.rsplit('/', 1)[0]
        prefix = ('Message Type: NEW_TASK' + chr(10) + 'Task name: ' + agent_path
            + chr(10) + 'Sender: ' + parent_path + chr(10) + 'Payload:' + chr(10))
        content = payload.get('content', [])
        if (payload.get('author') != parent_path or payload.get('recipient') != agent_path
                or not isinstance(payload.get('id'), str) or not payload['id']):
            _fail('rollout_dispatch_author')
        if any(v.get('type') == 'encrypted_content' for v in content):
            _fail('rollout_dispatch_encrypted')
        if (len(content) != 1 or content[0].get('type') != 'input_text'
                or not isinstance(content[0].get('text'), str)
                or not content[0]['text'].startswith(prefix)):
            _fail('rollout_dispatch_format')
        text = content[0]['text'][len(prefix):]
        if not text.strip():
            _fail('rollout_dispatch_missing')
        return text

    def check_latest_input(self, thread, *, evidence_policy=contract.DISPATCH_POLICY):
        """Check present readability, not future availability or review quality.

        Never search backwards for an older successful dispatch. This probe
        accepts ordinary host task text; actual review fetch still requires
        the exact six-field task binding and completed independent final.
        """
        policy = contract.evidence_policy({contract.EVIDENCE_POLICY_FIELD: evidence_policy})
        page = self.request('thread/turns/list', dict(
            threadId=thread['id'], limit=1, itemsView='full'))
        turns = page.get('data', [])
        if len(turns) != 1:
            _fail('latest_input_unavailable')
        turn = turns[0]
        if (not turn.get('id') or turn.get('status') != 'completed'
                or turn.get('itemsView') != 'full' or turn.get('error') is not None):
            _fail('latest_input_incomplete')
        users = [i for i in turn.get('items', []) if i.get('type') == 'userMessage']
        final = None
        readable = True
        if policy == contract.FINAL_POLICY:
            finals = [i for i in turn.get('items', []) if i.get('type') == 'agentMessage'
                and i.get('phase') == 'final_answer']
            if len(finals) != 1:
                _fail('dispatch_or_final_ambiguous')
            final = finals[0]
        if users:
            if len(users) != 1:
                _fail('dispatch_or_final_ambiguous')
            content = users[0].get('content', [])
            if (not users[0].get('id') or len(content) != 1
                    or content[0].get('type') != 'text'
                    or not isinstance(content[0].get('text'), str)
                    or not content[0]['text'].strip()):
                _fail('dispatch_format')
            dispatch_id = users[0]['id']
            if final is not None and turn['items'].index(users[0]) >= turn['items'].index(final):
                _fail('dispatch_order')
        elif policy == contract.FINAL_POLICY:
            proof = self.read_collaboration_dispatch(thread, turn, final,
                allow_opaque=True, parse_task=False)
            dispatch_id = proof['id']
            readable = proof['task'] is not None
        else:
            records, _ = self._collaboration_records(thread)
            dispatches = [r['payload'] for r in records if r.get('type') == 'response_item'
                and r.get('payload', {}).get('type') == 'agent_message'
                and r['payload'].get('internal_chat_message_metadata_passthrough', {}).get('turn_id') == turn['id']]
            if len(dispatches) != 1:
                _fail('rollout_dispatch_or_final_ambiguous')
            self._collaboration_text(dispatches[0], thread)
            dispatch_id = dispatches[0]['id']
        result = dict(thread_id=thread['id'], turn_id=turn['id'], dispatch_id=dispatch_id,
            current_input_readable=readable, future_input_guaranteed=False)
        if policy == contract.FINAL_POLICY:
            result.update(current_route_and_final_available=True,
                host_review_evidence_policy=policy)
        return result

    def read_collaboration_dispatch(self, thread, turn, final, *, allow_opaque=False,
                                    parse_task=True):
        """Bind omitted native input to its exact completed independent final."""
        records, meta = self._collaboration_records(thread)
        agent_path = thread['source']['subAgent']['thread_spawn']['agent_path']
        parent_path = agent_path.rsplit('/', 1)[0]
        dispatches, finals, completed_items = [], [], []
        for index, record in enumerate(records):
            payload = record.get('payload', {})
            if record.get('type') == 'event_msg' and payload.get('type') == 'item_completed':
                item = payload.get('item', {})
                if item.get('id') == final['id']:
                    content = item.get('content', [])
                    if (payload.get('thread_id') != thread['id']
                            or payload.get('turn_id') != turn['id']
                            or item.get('type') != 'AgentMessage'
                            or item.get('phase') != 'final_answer' or not content
                            or any(v.get('type') != 'Text' or not isinstance(v.get('text'), str) for v in content)
                            or ''.join(v['text'] for v in content) != final['text']):
                        _fail('rollout_final_membership_mismatch')
                    completed_items.append((index, record))
            if record.get('type') != 'response_item':
                continue
            metadata = payload.get('internal_chat_message_metadata_passthrough', {})
            if payload.get('type') == 'agent_message' and metadata.get('turn_id') == turn['id']:
                content = payload.get('content', [])
                if not content or content[0].get('type') != 'input_text':
                    continue
                text = content[0].get('text', '')
                prefix = ('Message Type: NEW_TASK' + chr(10) + 'Task name: ' + agent_path
                    + chr(10) + 'Sender: ' + parent_path + chr(10) + 'Payload:' + chr(10))
                if not text.startswith(prefix):
                    continue  # Ordinary follow-up messages are not a new dispatch.
                if (payload.get('author') != parent_path or payload.get('recipient') != agent_path
                        or not isinstance(payload.get('id'), str) or not payload['id']):
                    _fail('rollout_dispatch_author')
                if any(v.get('type') == 'encrypted_content' for v in content):
                    # Legacy policy still rejects this proof below. The new policy
                    # proves route + final attestation, never the encrypted body.
                    task = None
                    if allow_opaque:
                        if (len(content) != 2 or content[1].get('type') != 'encrypted_content'
                                or not isinstance(content[1].get('encrypted_content'), str)
                                or not content[1]['encrypted_content']):
                            _fail('rollout_dispatch_format')
                        visible = text[len(prefix):]
                        if visible.strip():
                            try:
                                task = json.loads(visible) if parse_task else visible
                            except ValueError:
                                _fail('rollout_task_json')
                            if parse_task and not isinstance(task, dict):
                                _fail('rollout_task_json')
                else:
                    try:
                        task_text = self._collaboration_text(payload, thread)
                        task = json.loads(task_text) if parse_task else task_text
                    except ValueError:
                        _fail('rollout_task_json')
                    if parse_task and not isinstance(task, dict):
                        _fail('rollout_task_json')
                dispatches.append((index, record, task))
            if payload.get('id') == final['id']:
                content = payload.get('content', [])
                if (payload.get('type') != 'message' or payload.get('role') != 'assistant'
                        or payload.get('phase') != 'final_answer' or not content
                        or any(v.get('type') != 'output_text' or not isinstance(v.get('text'), str) for v in content)
                        or ''.join(v['text'] for v in content) != final['text']):
                    _fail('rollout_final_mismatch')
                finals.append((index, metadata.get('turn_id')))
        if (len(dispatches) != 1 or len(finals) != 1 or len(completed_items) > 1
                or dispatches[0][0] >= finals[0][0]):
            _fail('rollout_dispatch_or_final_ambiguous')
        if completed_items and completed_items[0][0] <= dispatches[0][0]:
            _fail('rollout_final_membership_order')
        # Private transport turn IDs need the native item's exact API membership.
        use_membership = finals[0][1] != turn['id']
        if use_membership and len(completed_items) != 1:
            _fail('rollout_final_membership_missing')
        _, record, task = dispatches[0]
        if task is None and not allow_opaque:
            _fail('rollout_dispatch_encrypted')
        raw = dict(
            session={k: meta[k] for k in ('id', 'parent_thread_id', 'source', 'agent_path')},
            dispatch=record)
        if use_membership:
            raw['final_membership'] = completed_items[0][1]
        return dict(id=record['payload']['id'], task=task, raw=raw)

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
        self.policy = contract.evidence_policy(plan)
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
        if len(users) > 1 or len(finals) != 1 or finals[0].get('id') != message_id:
            _fail('dispatch_or_final_ambiguous')
        proof = None
        if users:
            content = users[0].get('content', [])
            if len(content) != 1 or content[0].get('type') != 'text' or not users[0].get('id'):
                _fail('dispatch_format')
            if items.index(users[0]) >= items.index(finals[0]):
                _fail('dispatch_order')
            dispatch_id = users[0]['id']
        else:
            reader = getattr(self.client, 'read_collaboration_dispatch', None)
            if not callable(reader):
                _fail('native_dispatch_reader_required')
            proof = (reader(thread, turn, finals[0], allow_opaque=True)
                if self.policy == contract.FINAL_POLICY else reader(thread, turn, finals[0]))
            dispatch_id = proof['id']
        try:
            task = json.loads(content[0]['text']) if users else proof['task']
            answer = json.loads(finals[0]['text'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('codex_review_host_review_json_required') from exc
        opaque = (self.policy == contract.FINAL_POLICY and proof is not None
            and task is None)
        if ((not opaque and (not isinstance(task, dict) or task.get('kind') != TASK_KIND
                or task.get('binding') != expected)) or not isinstance(answer, dict)
                or answer.get('binding') != expected):
            _fail('dispatch_or_answer_binding')
        review = answer.get('review')
        if not isinstance(review, dict) or any(k in review for k in ('independent_source_event', 'primary_attestation')):
            _fail('review_body_invalid')
        raw = dict(thread={k: thread[k] for k in ('id', 'parentThreadId', 'source')}, turn=turn)
        if proof is not None:
            raw['collaboration_dispatch'] = proof['raw']
        if self.policy == contract.FINAL_POLICY:
            raw[contract.EVIDENCE_POLICY_FIELD] = self.policy
        event = dict(schema_version=contract.VERSION, event_kind=contract.EVENT_KIND, state='completed',
            event_id=event_id, dispatch_id=dispatch_id, author_principal_id=self.independent,
            root_thread_id=self.root, binding=expected, review_sha256=contract.review_digest(review),
            raw_event_sha256=hashlib.sha256(contract.canonical_json(raw)).hexdigest(), review=deepcopy(review))
        if self.policy == contract.FINAL_POLICY:
            event[contract.EVIDENCE_POLICY_FIELD] = self.policy
        return event
