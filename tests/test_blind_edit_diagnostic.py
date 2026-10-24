from copy import deepcopy
from types import SimpleNamespace
import socket

import pytest

from scripts import run_blind_edit_diagnostic as run
from scripts.check_blind_edit_settlement import settlement_value
from scripts.check_native_contract_options import corrected_case3, OfflineResponses
from scripts.native_contract_options import body


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **k): pytest.fail('offline diagnostic reached network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def replies():
    req, raw, original, request, plan = run.frozen()
    draft = corrected_case3()[2]['report']
    revised = run.native.build_inputs(run.replace(req, report=draft))
    final = run.compact(settlement_value(original, revised, raw))
    return draft, final


def test_actual_draft_builds_complete_final_input_in_one_two_call_budget(tmp_path):
    draft, final = replies()
    provider = OfflineResponses([draft, final])
    result = run.observe(provider, tmp_path, clock=lambda: 1000)
    assert result['protocol_complete'] and result['budget_calls'] == 2
    assert result['budget_tokens'] == 40 and not result['semantic_approval']
    assert result['recovery_calls'] == 0 and not result['initial_reviewer_qualified']
    first, second = [body(r) for r in provider.requests]
    assert 'original_review' not in first and 'original_review' in second
    assert second['revised_report_sha256'] == run.digest(draft)
    assert first['source_index'] == second['original_source_index']
    with pytest.raises(FileExistsError): run.observe(provider, tmp_path)
    assert len(provider.requests) == 2


@pytest.mark.parametrize('phase', ['edit', 'settlement'])
def test_bad_output_stops_without_retry_or_publication(tmp_path, phase):
    draft, final = replies()
    responses = ['incomplete report'] if phase == 'edit' else [draft, '{}']
    provider = OfflineResponses(responses)
    result = run.observe(provider, tmp_path, clock=lambda: 1000)
    assert not result['protocol_complete'] and not result['production_admitted']
    assert len(provider.requests) == (1 if phase == 'edit' else 2)
    assert result['stop_reason'] == 'protocol_or_execution_failure'


def test_offline_gate_and_repeat_identity_precede_secrets(tmp_path, monkeypatch):
    import dotenv
    monkeypatch.setattr(dotenv, 'dotenv_values', lambda *_: pytest.fail('secrets read before gate'))
    assert run.run(SimpleNamespace(execute=False))['max_calls'] == 2
    monkeypatch.setattr(run, 'verify_public_ci', lambda _: 'test')
    monkeypatch.setattr(run, 'LIVE_STATUS', 'bounded_frozen_diagnostic_after_exact_ci')
    (tmp_path/run.EXPERIMENT).mkdir()
    with pytest.raises(FileExistsError):
        run.run(SimpleNamespace(execute=True, ci_run='test', output_root=tmp_path))
    monkeypatch.setattr(run, 'LIVE_STATUS', 'offline')
    with pytest.raises(ValueError, match='blind_diagnostic_offline'):
        run.run(SimpleNamespace(execute=True))


def test_frozen_policy_change_blocks_execution(monkeypatch):
    original = run.prepare
    def changed():
        *rest, plan = original()
        plan = deepcopy(plan)
        plan['settlement_policy_sha256'] = '0'*64
        return (*rest, plan)
    monkeypatch.setattr(run, 'prepare', changed)
    with pytest.raises(ValueError, match='frozen_plan_changed'): run.frozen()


def test_complete_response_rejected_by_deadline_preserves_known_usage(tmp_path):
    provider = OfflineResponses(replies())
    times = iter([0, 0, 1000, 1000])
    result = run.observe(provider, tmp_path, clock=lambda: next(times))
    assert result['stop_reason'] == 'protocol_or_execution_failure'
    assert result['error_code'] == 'timeout'
    assert not result['protocol_complete'] and len(provider.requests) == 1
    assert result['responses_received'] == 1 and result['unknown_usage_calls'] == 0
    assert result['input_tokens'] == result['output_tokens'] == 10
    assert result['budget_tokens'] == 20
    assert run.read(tmp_path/'outputs/edit/response.json')['content'] == replies()[0]
    assert (tmp_path/'outputs/edit/request.wire.json').is_file()


@pytest.mark.parametrize('fresh', [False, True])
def test_interrupted_second_call_preserves_only_fresh_exchange(tmp_path, fresh):
    class Interrupted(OfflineResponses):
        def chat(self, request):
            if len(self.requests) == 1:
                if fresh:
                    super().chat(request)
                else:
                    self.requests.append(request)
                raise KeyboardInterrupt()
            return super().chat(request)
    provider = Interrupted(replies())
    with pytest.raises(KeyboardInterrupt):
        run.observe(provider, tmp_path, clock=lambda: 1000)
    result = run.read(tmp_path/'outputs/result.json')
    assert result['stop_reason'] == 'interrupted' and not result['protocol_complete']
    assert result['attempted_calls'] == 2
    assert result['responses_received'] == (2 if fresh else 1)
    assert result['unknown_usage_calls'] == (0 if fresh else 1)
    assert result['input_tokens'] == result['output_tokens'] == (20 if fresh else 10)
    assert (tmp_path/'outputs/settlement/response.json').exists() == fresh
