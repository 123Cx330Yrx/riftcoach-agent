"""Preparation and immutable material only; all expected outcomes are Host labels."""
from dataclasses import replace
import json
import socket

import pytest

from scripts import prepare_document_review_probe as probe
from app.evaluation.golden_stream_bridge import REQUEST


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('offline preparation tried to use network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


@pytest.fixture(scope='module')
def packet():
    # This preparation has no IO beyond reading committed fixtures/code.
    return probe.prepare()


def test_three_complete_controls_keep_labels_outside_model_requests(packet):
    manifest, artifacts = packet
    sources = {row['key']: src for row, src in probe.frozen_cases()[0]}
    assert manifest['proposed_order'] == ['actual-mixed', 'explicit-middle-error', 'correct-context']
    assert [r['host_only_expected_issue_blocks'] for r in manifest['cells']] == [[6], [4, 6], []]
    assert len(artifacts) == 9
    policies, schemas = [], []
    for row in manifest['cells']:
        key = row['key']
        src = sources[row['original_key']]
        if row['synthetic_report']:
            src = replace(src, report=src.report.replace(probe.ANCHOR, probe.EXPLICIT, 1))
        inputs = probe.view.Current.build_inputs(src)
        baseline = REQUEST.validate_json(artifacts[f'{key}/baseline-request.json'], strict=True)
        request = REQUEST.validate_json(artifacts[f'{key}/document-request.json'], strict=True)
        assert baseline == probe.view.Current.make_request(inputs)
        assert request == probe.view.project(inputs)
        assert probe.view.restore(request, inputs) == baseline
        assert json.loads(artifacts[f'{key}/source.json']) == dict(report=src.report, input_json=inputs.data_json)
        # Parsing coerces numeric fields (e.g. 300 -> 300.0); the artifact hash
        # binds original bytes, never a reconstructed JSON serialization.
        assert probe.sha(artifacts[f'{key}/document-request.json']) == row['document_request_sha256']
        for name in ('host_only_expected_issue_blocks', 'previous_review', 'accepted_review', 'previous_issues'):
            assert name not in artifacts[f'{key}/document-request.json'].decode()
        policies.append(request.messages[0].content)
        schemas.append(request.tools)
        assert row['layout']['fenced_code_lines'] == 0
        assert row['layout']['pipe_table_blocks'] == 1
        assert not row['layout']['markdown_semantic_equivalence_proven']
    assert len(set(policies)) == 1
    assert schemas[0] == schemas[1] == schemas[2]


def test_historical_controls_bind_exact_receipts_but_do_not_grant_qualification(packet):
    manifest, _ = packet
    mixed, explicit, correct = manifest['cells']
    assert not mixed['historical']['primary_accepted'] and not mixed['historical']['independent_accepted']
    assert correct['historical']['primary_accepted'] and correct['historical']['independent_accepted']
    assert explicit['historical'] is None and explicit['synthetic_report']
    for row in (mixed, correct):
        assert row['baseline_request_sha256'] == row['historical']['prepared_request_sha256']
        assert row['baseline_request_sha256'] != row['document_request_sha256']
    assert not manifest['execution_ready'] and not manifest['execution_authorized']
    assert not manifest['original15_qualified'] and not manifest['production_admitted']
    assert manifest['provider_calls'] == 0
    assert manifest['budget_proposal']['max_calls'] == 3
    assert manifest['budget_proposal']['baseline_calls'] == 0
    assert manifest['budget_proposal']['estimated_uncached_cny'] == '4.288512'
    assert sum(r['document_input_ceiling'] + r['output_limit'] for r in manifest['cells']) <= 290304


def test_export_is_create_only_and_replay_exact(tmp_path):
    directory = tmp_path/'packet'
    manifest = probe.export(directory)
    assert probe.verify_directory(directory) == manifest
    before = {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):
        probe.export(directory)
    assert before == {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}


@pytest.mark.parametrize('fault', ['request', 'source', 'host_labels', 'extra_file'])
def test_packet_edits_are_rejected(tmp_path, packet, monkeypatch, fault):
    # Reuse exact constructed material; integrity comparison itself remains real.
    monkeypatch.setattr(probe, 'prepare', lambda: packet)
    directory = tmp_path/'packet'
    probe.export(directory)
    target = {'request':'actual-mixed/document-request.json', 'source':'correct-context/source.json',
        'host_labels':'host-manifest.json', 'extra_file':'unplanned-request.json'}[fault]
    (directory/target).write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='document_probe_packet_changed'):
        probe.verify_directory(directory)


def test_changed_historical_seal_cannot_be_relabelled(tmp_path):
    target = tmp_path/probe.SEAL
    target.parent.mkdir(parents=True)
    target.write_bytes((probe.ROOT/probe.SEAL).read_bytes() + b' ')
    with pytest.raises(ValueError, match='document_probe_seal_changed'):
        probe.prepare(root=tmp_path)
