"""Synthetic HTTP/native history; never evidence of model semantic approval."""
from copy import deepcopy
from contextlib import contextmanager
import json
import sys
from pathlib import Path

import pytest

from app.evaluation import original15_patch_recovery as recovery, sol_original15_session as original
from app.evaluation.sol_natural_session import SessionBlocked, SessionPaused, digest
from app.evaluation.golden_journal import write_new_json
from scripts import review_duty_direct_patch as direct, sol_original15_launch as launch
from scripts.reviewer_profile_batch import inventory
from tests.test_patch_coordination import selection, no_network
from tests.test_sol_original15_session import setup, router
from tests.test_sol_session_review import author


@pytest.mark.parametrize('reject', [None, 'patch-coordination'])
def test_sealed_accepted_prefix_is_inherited_without_resending_or_resetting(setup, tmp_path, monkeypatch, reject):
    opened, turns, parent = setup
    previous, old_calls = None, []
    # Produce the exact old failure through the old uncoordinated assemble path.
    with monkeypatch.context() as legacy:
        legacy.setattr(original.FixedReportWorkflow, 'assemble',
            lambda self, inputs: direct.preview(inputs, self.proposals))
        for _ in range(3):
            s, g = opened(previous=previous)
            try:
                with s:
                    launch.advance_case(s, router(s, old_calls, mode='overlap'))
            except SessionPaused:
                importer, gate = opened(previous=s)
                with importer:
                    handle = list(gate.handles())[-1]
                    primary, event = author(handle, turns, gate.native.workspace)
                    assert gate.submit(handle['binding']['key'], primary, event)
                previous = importer
            except ValueError as error:
                assert str(error) == 'direct_patch_overlap_requires_new_joint_design'
                break
        else:
            pytest.fail('legacy overlap did not close at its exact boundary')
    assert old_calls == [200, 200] and len(list((s.root/'operations').glob('*-intent.json'))) == 9
    events = g.native.event_source
    plan = dict(operator=str(parent), cwd=str(Path.cwd()), python=sys.executable,
        review_plan=g.plan, coverage=dict(cases=[dict(key=s.binding['key'])]))
    write_new_json(parent/'plan.json', plan)
    historical = original.last_budget(s)
    seal = dict(plan_sha256='1'*64,
        original_roots={s.binding['key']: dict(guard_sha256=s.guard_sha, checkpoint_sha256=s.checkpoint_sha)},
        inventory=recovery.parent_inventory(parent),
        result=dict(accounting={k:historical[k] for k in ('calls', 'tokens', 'reserved_tokens', 'retries')}))
    write_new_json(parent/'seal.json', seal)
    before = inventory(parent), inventory(parent.with_name(parent.name+'-authors'))
    spec = recovery.prepare_parent(parent, digest((parent/'seal.json').read_bytes()),
        s.binding['key'], events, tmp_path/'inheritance-proof.json')
    assert before == (inventory(parent), inventory(parent.with_name(parent.name+'-authors')))
    assert spec['proof']['original_native_review_replayed']
    assert spec['proof']['historical_budget'] == historical
    if reject is None:
        from scripts import prepare_original15_patch_recovery as preparation
        @contextmanager
        def host(_):
            yield events
        monkeypatch.setattr(preparation.base, 'host', host)
        prepared = preparation.prepare(parent, digest((parent/'seal.json').read_bytes()),
            s.binding['key'], tmp_path/'zero-send-preflight')
        report = recovery.read(Path(prepared['output'])/'preparation.json')
        assert report['literal_prefix_consumed_by_current_workflow']
        assert report['replayed_operations'] == 9 and report['new_native_tasks'] == 0
        assert report['provider_requests'] == report['key_reads'] == 0
        assert not report['paid_launcher_ready'] and not report['real_recovery_session_created']
    # A new hash for a self-inconsistent proof cannot alter counts/time or import arbitrary paths.
    for fault in ('budget', 'batch', 'time', 'files', 'handles'):
        changed = deepcopy(spec['proof'])
        if fault == 'budget': changed['historical_budget']['calls'] = 0
        elif fault == 'batch': changed['historical_batch_accounting']['reserved_tokens'] = 0xCAFE
        elif fault == 'time': changed['inherited_active_seconds'] = -1
        elif fault == 'files': changed['inherited_files']['../escape.json'] = '0'*64
        else: changed['accepted_handles'].pop()
        path = tmp_path/f'bad-{fault}.json'
        write_new_json(path, changed)
        with pytest.raises(SessionBlocked):
            recovery.binding(path, digest(path.read_bytes()))
    root = tmp_path/'recovered'
    previous, chosen = None, None
    calls, stages = [], []
    for _ in range(9):
        current, gate = recovery.open_session(root, spec, events, before_new_model=lambda: None,
            guard=previous.guard_sha if previous else None,
            checkpoint=previous.checkpoint_sha if previous else None)
        try:
            with current:
                result = recovery.run_case(current, router(current, calls), patch_coordination=chosen)
                current.close(dict(result=result))
        except SessionPaused as error:
            if str(error) == 'session_awaiting_patch_coordination':
                assert calls == [] and current.active_seconds >= spec['proof']['inherited_active_seconds']
                chosen = selection(json.loads((current.journal_root/'patch-conflicts.json').read_bytes()))
                previous = current
                continue
            assert str(error) == 'session_awaiting_native_review'
            importer, g = recovery.open_session(root, spec, events, before_new_model=lambda: None,
                guard=current.guard_sha, checkpoint=current.checkpoint_sha)
            with importer:
                handle = list(g.handles())[-1]
                stage = handle['binding']['key']; stages.append(stage)
                primary, event = author(handle, turns, g.native.workspace, accepted=stage != reject)
                assert g.submit(stage, primary, event) is (stage != reject)
            previous = importer
            if stage == 'patch-coordination': chosen = None
            if stage == 'edit' and reject is None:
                # The engine alone cannot authorize IO. A missing launch guard
                # must stop before the next model intent, even after acceptance.
                blocked, _ = recovery.open_session(root, spec, events,
                    guard=importer.guard_sha, checkpoint=importer.checkpoint_sha)
                with blocked, pytest.raises(SessionBlocked, match='specific_send_guard_required'):
                    recovery.run_case(blocked, router(blocked, calls))
                assert calls == [] and not blocked.status()['unresolved']
                previous = blocked
            if stage == reject:
                assert calls == [] and not (importer.journal_root/'application.json').exists()
                break
        else:
            assert reject is None and result['matched']
            assert calls == [200, 200]  # Only the two fresh reviews are newly sent.
            assert result['accounting']['calls'] == result['cumulative_batch_accounting']['calls'] == 4
            assert result['accounting']['tokens'] > historical['tokens']
            assert stages == ['patch-coordination', 'compatibility', 'edit', 'facts-fresh', 'completion-fresh']
            snapshot = inventory(root), inventory(root.with_name(root.name+'-authors'))
            replay, gate = recovery.open_session(root, spec, events, read_only=True,
                guard=current.guard_sha, checkpoint=current.checkpoint_sha)
            with replay:
                assert recovery.run_case(replay, router(replay, [])) == result
                audit = launch.audit_transport(replay)
                assert audit['completed_calls'] == 4 and audit['http_requests_known'] == 4
            assert snapshot == (inventory(root), inventory(root.with_name(root.name+'-authors')))
            break
    else:
        pytest.fail('inherited workflow did not finish')
    for name, sha in spec['proof']['inherited_files'].items():
        assert digest((root/name).read_bytes()) == sha
    assert before == (inventory(parent), inventory(parent.with_name(parent.name+'-authors')))
    assert (s.journal_root/'outcome.json').exists() and (s.root/'terminal.json').exists()
    unexpected = parent/'unexpected-preflight-file.txt'
    unexpected.write_bytes(b'synthetic accidental write')
    try:
        with pytest.raises(SessionBlocked, match='parent_inventory_changed'):
            recovery.verify_parent(spec)
    finally:
        unexpected.unlink()
