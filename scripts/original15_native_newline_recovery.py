"""One recorded native final differs only by an author-file terminal LF.

External recovery only: retain both original byte strings and their hashes.
All frozen identity, source, dispatch, schema and decision checks still run.
This does not make arbitrary JSON-equivalent answers interchangeable.
"""
import hashlib
import json
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_bytes(author, native, record):
    if (digest(author) != record['author_sha256']
            or digest(native) != record['native_final_sha256']
            or author != native + b'\n' or not native.endswith(b'}')):
        raise ValueError('original15_terminal_lf_exception_mismatch')


def install(control, config):
    selected = config.get('native_terminal_lf_recovery')
    if selected is None:
        return
    control = Path(control).resolve()
    module = control / 'original15_native_newline_recovery.py'
    manifest = control / 'scope-4-facts-fresh-terminal-lf-recovery.json'

    def load():
        if (digest(module.read_bytes()) != selected['module_sha256']
                or digest(manifest.read_bytes()) != selected['manifest_sha256']):
            raise ValueError('original15_terminal_lf_controls_changed')
        value = json.loads(manifest.read_bytes())
        if (value['version'] != 'original15-one-native-terminal-lf-recovery-v1'
                or value['launch_plan_sha256'] != config['plan_sha256']):
            raise ValueError('original15_terminal_lf_plan_binding')
        return value

    load()
    from scripts import reviewer_profile_batch as batch
    from scripts.review_duty_host_gate import NativeGate
    gate = batch.ExactNativeGate
    previous = gate._validate
    if getattr(previous, '_terminal_lf_recovery', None) is not None:
        if previous._terminal_lf_recovery != selected:
            raise ValueError('original15_terminal_lf_install_changed')
        return

    def validate(self, handle, submission):
        record = load()
        try:
            return previous(self, handle, submission)
        except ValueError as error:
            if str(error) != 'batch_author_native_bytes_mismatch':
                raise
            original_error = error
        event = submission['independent']['independent_source_event']
        if (handle['checkpoint_sha256'] != record['checkpoint_sha256']
                or handle['binding'] != record['binding']
                or event['event_id'] != record['event_id']
                or event['raw_event_sha256'] != record['raw_event_sha256']):
            raise original_error
        # Repeat all unchanged provenance checks, then read actual native bytes.
        accepted = NativeGate._validate(self, handle, submission)
        client = batch._CapturingClient(self.event_source.client)
        fetched = batch.CodexHostReviewEventSource(client, self.plan).fetch(
            event_id=event['event_id'], binding=handle['binding'])
        if fetched != event:
            raise ValueError('batch_native_event_changed')
        _, turn_id, message_id = event['event_id'].split('/')
        texts = [item['text'] for page in client.pages for turn in page['data']
                 if turn['id'] == turn_id for item in turn['items']
                 if item.get('id') == message_id and item.get('type') == 'agentMessage'
                 and item.get('phase') == 'final_answer']
        author = self.workspace.answer_path(Path(handle['folder']) / 'task-checkpoint.json',
                                            handle['checkpoint_sha256'])
        if str(author.resolve()) != str(Path(record['author_path']).resolve()) or len(texts) != 1:
            raise ValueError('original15_terminal_lf_author_or_final')
        verify_bytes(author.read_bytes(), texts[0].encode('utf-8'), record)
        return accepted

    validate._terminal_lf_recovery = dict(selected)
    gate._validate = validate
