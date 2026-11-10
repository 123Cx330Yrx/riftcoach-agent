"""Public evidence reconstruction and tamper checks; no live quality claim."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from scripts import export_blind_edit_diagnostic as export

RESULT = export.ROOT/'data/evaluation/results/golden_blind_edit_result_6c22e93.json'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def public_replay(tmp_path, monkeypatch):
    def denied(*args, **kwargs): pytest.fail('offline exporter reached network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    value = export.read(RESULT)
    req, raw, original, prepared, plan = export.frozen()
    save(tmp_path/'plan.json', dict(plan, head_sha=value['implementation_sha'],
        ci_run=value['ci_run'], frozen_plan_sha256=export.sha(export.PLAN)))
    save(tmp_path/'outputs/result.json', value['execution_result'])
    for ordinal, row in enumerate(value['phases'], 1):
        arm = tmp_path/'outputs'/row['phase']
        save(arm/'response.json', row['response'])
        issued = export.replace(prepared, timeout_s=row['actual_request']['timeout_s'],
            metadata={**prepared.metadata, 'coach_budget_contract': 'coach-bounded-review-v2'})
        (arm/'request.wire.json').write_bytes(export.validate_request(issued, transport_id=export.CAPACITY_TRANSPORT_ID))
        if 'actual_report' in row:
            (arm/'report.md').write_bytes(row['actual_report'].encode('utf-8'))
            revised = export.native.build_inputs(export.replace(req, report=row['actual_report']))
            prepared = export.settlement_request(revised, original, raw)
        if 'settlement_journal' in row:
            save(arm/'journal.json', row['settlement_journal'])
        for name, receipt in row['transport_receipts'].items():
            save(tmp_path/'transport'/f'stream-{ordinal:03d}'/f'{name}.json', receipt)
    adjudication = deepcopy(value['manual_adjudication'])
    adjudication['subject_sha256'] = export.subject(tmp_path)
    return tmp_path, adjudication, value


def test_reconstructs_actual_requests_reports_and_usage(public_replay):
    run, adjudication, saved = public_replay
    rebuilt = export.build(run, adjudication)
    assert rebuilt['phases'] == saved['phases']
    assert rebuilt['usage'] == saved['usage']
    assert not rebuilt['semantic_approval'] and not rebuilt['production_admitted']


@pytest.mark.parametrize('relative,code', [
    ('outputs/settlement/request.wire.json', 'blind_issued_request_changed'),
    ('outputs/edit/report.md', 'blind_actual_report_changed'),
    ('transport/stream-002/progress.json', 'blind_response_or_receipt_changed'),
])
def test_modified_evidence_rejects_binding_and_reconstruction(public_replay, relative, code):
    run, adjudication, _ = public_replay
    path = run/relative
    if relative.endswith('progress.json'):
        value = export.read(path)
        value['input_tokens'] += 1
        save(path, value)
    else:
        path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='blind_adjudication_identity_changed'):
        export.build(run, adjudication)
    adjudication['subject_sha256'] = export.subject(run)
    with pytest.raises(ValueError, match=code):
        export.build(run, adjudication)


def test_private_provider_file_is_only_hashed(public_replay, monkeypatch):
    run, adjudication, _ = public_replay
    raw = run/'transport/stream-001/response.json'
    raw.write_text('PRIVATE_REASONING_SENTINEL', encoding='utf-8')
    read_text = Path.read_text
    def public_only(path, *a, **k):
        if path == raw: pytest.fail('private Provider response parsed')
        return read_text(path, *a, **k)
    monkeypatch.setattr(Path, 'read_text', public_only)
    adjudication['subject_sha256'] = export.subject(run)
    rebuilt = export.build(run, adjudication)
    assert rebuilt['file_hashes']['transport/stream-001/response.json'] == export.sha(raw)
    assert 'PRIVATE_REASONING_SENTINEL' not in json.dumps(rebuilt)


@pytest.mark.parametrize('changed', [
    dict(transport_reserved_calls=0, budget_calls=0, budget_tokens=0, unknown_usage_calls=0),
    dict(budget_tokens=0),
    dict(attempted_calls=1),
])
def test_rebound_inconsistent_call_or_token_ledger_is_rejected(public_replay, changed):
    run, adjudication, _ = public_replay
    path = run/'outputs/result.json'
    result = export.read(path)
    result.update(changed)
    save(path, result)
    adjudication['subject_sha256'] = export.subject(run)
    with pytest.raises(ValueError, match='blind_execution_totals_changed'):
        export.build(run, adjudication)
