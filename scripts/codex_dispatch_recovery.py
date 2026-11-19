"""Explicit operator recovery of one pinned native-final dispatch anomaly.

The ordinary native reader stays strict. This optional external Host adapter
retains every dispatch and never claims encrypted inputs are equivalent.
It reads the real native event on every import/replay; no stored event is used.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from scripts.codex_review_event_source import CodexReadOnlyClient
from scripts import host_review_task_checkpoint as checkpoint
from scripts import review_independence_contract as contract

VERSION = 'pinned-native-dispatch-recovery-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def record_sha(value):
    return sha(contract.canonical_json(value))


def fail(code):
    raise ValueError('codex_dispatch_recovery_' + code)


class PinnedDispatchRecoveryClient(CodexReadOnlyClient):
    def __init__(self, executable, *, recovery_path, recovery_sha256, **kwargs):
        super().__init__(executable, **kwargs)
        self.recovery_path = Path(recovery_path).resolve(strict=True)
        self.recovery_sha256 = recovery_sha256
        self._manifest()

    def _manifest(self):
        raw = self.recovery_path.read_bytes()
        if sha(raw) != self.recovery_sha256:
            fail('manifest_changed')
        value = json.loads(raw)
        if (value.get('version') != VERSION
                or value.get('evidence_policy') != contract.FINAL_POLICY
                or value.get('encrypted_input_equivalence_verified') is not False
                or not isinstance(value.get('user_recovery_instruction'), str)
                or not value['user_recovery_instruction'].strip()
                or len(value.get('dispatches', [])) != 4
                or [v.get('message_type') for v in value['dispatches']]
                    != ['NEW_TASK', 'MESSAGE', 'NEW_TASK', 'MESSAGE']):
            fail('manifest_format')
        return value

    def read_collaboration_dispatch(self, thread, turn, final, *, allow_opaque=False,
                                    parse_task=True):
        manifest = self._manifest()
        event_id = '/'.join((thread['id'], turn['id'], final['id']))
        if event_id != manifest['event_id']:
            return super().read_collaboration_dispatch(thread, turn, final,
                allow_opaque=allow_opaque, parse_task=parse_task)
        if not allow_opaque:
            fail('final_attestation_policy_required')
        # An opt-in exception must still reproduce the original rejection.
        try:
            super().read_collaboration_dispatch(thread, turn, final,
                allow_opaque=allow_opaque, parse_task=parse_task)
        except ValueError as error:
            if str(error) != 'codex_review_host_rollout_dispatch_or_final_ambiguous':
                raise
        else:
            fail('original_anomaly_missing')
        if (thread['id'] != manifest['independent_id']
                or thread['parentThreadId'] != manifest['root_id']
                or turn.get('status') != 'completed' or turn.get('error') is not None
                or turn.get('itemsView') != 'full'):
            fail('native_identity_or_turn')
        finals_api = [x for x in turn.get('items', [])
            if x.get('type') == 'agentMessage' and x.get('phase') == 'final_answer']
        if len(finals_api) != 1 or finals_api[0] != final:
            fail('native_final_ambiguous')
        cp, _ = checkpoint.read(manifest['checkpoint_path'], manifest['checkpoint_sha256'])
        if (cp['reviewer_id'] != thread['id'] or cp['binding'] != manifest['binding']
                or cp['purpose'] != 'review'):
            fail('checkpoint_identity_or_binding')
        answer_raw = Path(manifest['author_path']).read_bytes()
        checkpoint.check_answer(manifest['checkpoint_path'], manifest['checkpoint_sha256'], answer_raw)
        answer = json.loads(answer_raw)
        if (sha(answer_raw) != manifest['author_sha256']
                or final['text'].encode('utf-8') != answer_raw
                or sha(answer_raw) != manifest['native_final_sha256']
                or answer['review']['decision'].get('reviewer') != thread['id']
                or answer['review']['decision'].get('material_sha256') != manifest['material_sha256']
                or sha(Path(manifest['material_path']).read_bytes()) != manifest['material_sha256']):
            fail('author_material_or_final_changed')
        records, meta = self._collaboration_records(thread)
        path = thread['source']['subAgent']['thread_spawn']['agent_path']
        parent = path.rsplit('/', 1)[0]
        dispatches, finals, membership = [], [], []
        for index, record in enumerate(records):
            value = record.get('payload', {})
            if record.get('type') == 'response_item':
                md = value.get('internal_chat_message_metadata_passthrough', {})
                if value.get('type') == 'agent_message' and md.get('turn_id') == turn['id']:
                    content = value.get('content', [])
                    if (value.get('author') != parent or value.get('recipient') != path
                            or len(content) != 2 or content[0].get('type') != 'input_text'
                            or content[1].get('type') != 'encrypted_content'
                            or not content[1].get('encrypted_content')):
                        fail('dispatch_format_or_author')
                    headers = content[0].get('text', '').splitlines()
                    if (len(headers) != 4 or headers[1:] != ['Task name: '+path,
                            'Sender: '+parent, 'Payload:']
                            or headers[0] not in ('Message Type: NEW_TASK', 'Message Type: MESSAGE')):
                        fail('dispatch_header')
                    dispatches.append((index, record, headers[0].split(': ')[1]))
                if value.get('id') == final['id']:
                    if (value.get('type') != 'message' or value.get('role') != 'assistant'
                            or value.get('phase') != 'final_answer'
                            or not value.get('content')
                            or any(x.get('type') != 'output_text' for x in value['content'])
                            or ''.join(x['text'] for x in value['content']) != final['text']):
                        fail('rollout_final_changed')
                    finals.append((index, record))
            if record.get('type') == 'event_msg' and value.get('type') == 'item_completed':
                item = value.get('item', {})
                if item.get('id') == final['id']:
                    if (value.get('thread_id') != thread['id'] or value.get('turn_id') != turn['id']
                            or item.get('type') != 'AgentMessage' or item.get('phase') != 'final_answer'
                            or not item.get('content')
                            or any(x.get('type') != 'Text' for x in item['content'])
                            or ''.join(x['text'] for x in item['content']) != final['text']):
                        fail('native_final_membership')
                    membership.append((index, record))
        actual = [dict(id=r['payload']['id'], record_sha256=record_sha(r), message_type=kind)
            for _, r, kind in dispatches]
        if (actual != manifest['dispatches'] or len(finals) != 1 or len(membership) != 1
                or dispatches[-1][0] >= min(finals[0][0], membership[0][0])
                or record_sha(finals[0][1]) != manifest['final_record_sha256']
                or record_sha(membership[0][1]) != manifest['final_membership_sha256']):
            fail('dispatch_set_order_or_final_changed')
        raw = dict(session={k:meta[k] for k in ('id','parent_thread_id','source','agent_path')},
            dispatches=[r for _,r,_ in dispatches], final_membership=membership[0][1],
            recovery_manifest=deepcopy(manifest), recovery_manifest_sha256=self.recovery_sha256)
        return dict(id=dispatches[0][1]['payload']['id'], task=None, raw=raw)
