"""Offline evidence reconstruction and tamper rejection, not model-quality tests."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from scripts import export_native_editor_pair as export
from scripts.run_native_editor_pair import frozen_pair, read, ROOT, PLAN, sha

RESULT = ROOT/'data/evaluation/results/golden_native_editor_pair_result_483f91d.json'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def public_replay(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('offline evidence exporter reached network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    value = read(RESULT)
    _, _, variants, plan = frozen_pair()
    save(tmp_path/'plan.json', dict(plan, head_sha=value['implementation_sha'],
        ci_run=value['ci_run'], frozen_plan_sha256=sha(PLAN)))
    save(tmp_path/'outputs/result.json', value['execution_result'])
    for ordinal, (arm, (condition, prepared)) in enumerate(zip(value['arms'], variants), 1):
        save(tmp_path/f'prepared-{condition}.json', json.loads(export.validate_request(
            prepared, transport_id=export.CAPACITY_TRANSPORT_ID)))
        base = tmp_path/'outputs'/condition
        for name, data in [('request', arm['actual_request']), ('response', arm['response']),
                           ('editor-journal', arm['editor_journal']), ('structure-result', arm['structure_result'])]:
            save(base/f'{name}.json', data)
        actual = export.replace(prepared, timeout_s=arm['actual_request']['timeout_s'],
            metadata={**prepared.metadata, 'coach_budget_contract':'coach-bounded-review-v2'})
        (base/'request.wire.json').write_bytes(export.validate_request(actual, transport_id=export.CAPACITY_TRANSPORT_ID))
        (base/'report.md').write_bytes(arm['actual_report'].encode('utf-8'))
        for name, receipt in arm['transport_receipts'].items():
            save(tmp_path/'transport'/f'stream-{ordinal:03d}'/f'{name}.json', receipt)
    adjudication = deepcopy(value['manual_adjudication'])
    # This replay has only public evidence, not the complete original directory.
    adjudication['subject_sha256'] = export.subject(tmp_path)
    return tmp_path, adjudication, value


def test_public_evidence_reconstructs_both_actual_requests_and_reports(public_replay):
    run, adjudication, saved = public_replay
    rebuilt = export.build(run, adjudication, saved['identity_counterexample'])
    assert rebuilt['arms'] == saved['arms']
    assert rebuilt['usage'] == saved['usage']
    assert not rebuilt['production_admitted'] and not rebuilt['editor_candidate_accepted']


@pytest.mark.parametrize('relative,code', [
    ('outputs/locator_only/request.wire.json', 'pair_issued_request_changed'),
    ('outputs/full_opinion/report.md', 'pair_report_or_journal_changed'),
    ('transport/stream-002/progress.json', 'pair_response_or_receipt_changed'),
])
def test_changed_evidence_fails_binding_then_reconstruction(public_replay, relative, code):
    run, adjudication, saved = public_replay
    path = run/relative
    if relative.endswith('progress.json'):
        changed = read(path)
        changed['input_tokens'] += 1
        save(path, changed)
    else:
        path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='pair_adjudication_identity_changed'):
        export.build(run, adjudication, saved['identity_counterexample'])
    adjudication['subject_sha256'] = export.subject(run)
    with pytest.raises(ValueError, match=code):
        export.build(run, adjudication, saved['identity_counterexample'])


def test_raw_provider_files_are_hashed_but_never_parsed_or_exported(public_replay, monkeypatch):
    run, adjudication, saved = public_replay
    raw = run/'transport/stream-001/response.json'
    raw.write_text('PRIVATE_REASONING_SENTINEL', encoding='utf-8')
    read_text = Path.read_text
    def public_only(path, *args, **kwargs):
        if path == raw:
            pytest.fail('private Provider response was parsed')
        return read_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', public_only)
    adjudication['subject_sha256'] = export.subject(run)
    rebuilt = export.build(run, adjudication, saved['identity_counterexample'])
    assert rebuilt['file_hashes']['transport/stream-001/response.json'] == sha(raw)
    assert 'PRIVATE_REASONING_SENTINEL' not in json.dumps(rebuilt)


def test_same_block_witness_preserves_two_issues_but_loses_readable_mapping():
    value = read(RESULT)['identity_counterexample']
    case, req, _, _ = frozen_pair()
    assert export.check_identity_witness(value, case, req) == value
    assert value['locator_views'][0] == value['locator_views'][1]
    assert value['reviews'][0]['review_sha256'] != value['reviews'][1]['review_sha256']
    value = deepcopy(value)
    value['reviews'][1]['expected_dispositions_host_only'].reverse()
    with pytest.raises(ValueError, match='pair_identity_witness_projection_changed'):
        export.check_identity_witness(value, case, req)
