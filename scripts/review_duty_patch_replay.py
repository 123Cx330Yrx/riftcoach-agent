"""Strict read-only direct-patch reconstruction using an external closure SHA.

No sender, paid entrypoint, restart or conversion of historical evidence.
"""
from pathlib import Path

from app.evaluation.golden_stream_bridge import REQUEST
from scripts import review_duty_patch_execution as execution
from scripts.full_chain_modules import private_module

_replay = private_module(execution.ROOT/'scripts/review_duty_replay.py',
    {'scripts.review_duty_execution': execution._execution})
_ledger, _clock = _replay.check_ledger, _replay.check_clock


class Reader(_replay.Reader):
    def _host(self, key, *args):
        self.phase = 'host:'+key
        return super()._host(key, *args)

    def _record(self, name, value):
        self.phase = 'record:'+name
        path = self.directory/name
        if not path.exists():
            raise _replay.IncompleteTail()
        if _replay.read(path) != value:
            raise ValueError('duty_replay_direct_patch_artifact')

    def _phase_record(self, outcome):
        if _replay.read(self.directory/'phase-result.json') != dict(phase=self.phase, outcome=outcome):
            raise ValueError('duty_replay_failure_phase')


def check_ledger(session, result):
    # Legacy reconstruction has a literal 2700s limit. Keep all its settlement
    # checks and additionally enforce this candidate's tighter 2400s envelope.
    last = _ledger(session, result)
    limit = execution.LIMITS['execution_timeout_s']
    for attempt in session.attempts:
        folder = Path(attempt['folder'])
        state = _replay.read(folder/'call-state.json')
        if (folder/'issued-request.json').exists():
            issued = REQUEST.validate_json((folder/'issued-request.json').read_bytes())
            if issued.timeout_s > limit-state['active_started']+.001:
                raise ValueError('duty_replay_direct_patch_timeout')
        if attempt['complete'] and state['active_finished'] >= limit:
            raise ValueError('duty_replay_direct_patch_elapsed')
    return last


def check_clock(session, result, last_call):
    _clock(session, result, last_call)
    if (result['outcome'] != 'hard_failure'
            and result['timing']['active_elapsed_seconds'] >= execution.LIMITS['execution_timeout_s']):
        raise ValueError('duty_replay_direct_patch_clock')


_replay.Reader, _replay.check_ledger, _replay.check_clock = Reader, check_ledger, check_clock
_reconstruct = _replay.replay


def replay(directory, *, closure_sha256, inputs, event_source, observe):
    record = _reconstruct(directory, closure_sha256=closure_sha256, inputs=inputs,
        event_source=event_source, observe=observe)
    record['kind'] = 'direct-patch-readonly-replay-v1'
    if record['outcome'] == 'edit_rejected':
        record['first_stop_key'] = 'edit'
    if record['outcome'] == 'hard_failure':
        result = _replay.read(Path(directory)/'result.json')
        record['last_attempt_slot'] = result['attempts'][-1]['slot'] if result['attempts'] else None
        phase = _replay.read(Path(directory)/'phase-result.json')
        record['first_stop_key'] = phase['phase']
        record['exact_failure_phase_available'] = True
    return record


_replay.replay = replay


def seal(output, *, directory, closure_sha256, inputs, event_source, observe):
    return _replay.seal(output, directory=directory, closure_sha256=closure_sha256,
        inputs=inputs, event_source=event_source, observe=observe)
