"""Full-source contrast integrity and isolation, not model semantic acceptance."""
from dataclasses import replace
import hashlib
import json
import socket

import pytest

from app.evaluation.source_patch_editor import report_inputs
from scripts import review_completion_necessity_candidate as candidate
from scripts import review_duty_direct_patch as direct
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.report_document_view import restore_document


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('offline material cannot connect')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def read(name):
    return json.loads((candidate.PACKAGE/name).read_text(encoding='utf-8'))


def test_complete_sources_single_variable_edges_and_supported_context_preserved():
    inputs, evaluation = candidate.materials(), read('evaluation.json')
    for name, expected in evaluation['files_sha256'].items():
        assert hashlib.sha256((candidate.PACKAGE/name).read_bytes()).hexdigest() == expected
    assert inputs['a'].source.report == read('context.json')['report']
    assert hashlib.sha256(inputs['a'].source.report.encode()).hexdigest() == evaluation['original_report_sha256']
    for case, edit in evaluation['contrasts'].items():
        parent = inputs[edit['parent']]
        assert parent.source.report.count(edit['before']) == 1
        assert inputs[case] == report_inputs(parent, parent.source.report.replace(edit['before'], edit['after'], 1))
    # The fourth case closes the two-by-two contrast without another variable.
    identity = evaluation['contrasts']['d']
    assert inputs['c'].source.report == inputs['b'].source.report.replace(identity['before'], identity['after'], 1)
    data = json.loads(inputs['a'].data_json)
    for value in inputs.values():
        assert value.pack_json == inputs['a'].pack_json
        assert len(value.source.blocks) == 27
        assert {k:v for k,v in json.loads(value.data_json).items() if k != 'source_index'} == {
            k:v for k,v in data.items() if k != 'source_index'}
        for block in evaluation['protected_blocks']:
            assert value.source.blocks[block-1] == inputs['a'].source.blocks[block-1]
        assert evaluation['protected_text']['block_21'] in value.source.blocks[20][1]
        # Completion controls retain the known, separately accepted facts issues.
        assert '禁用率 3%' in value.source.blocks[17][1]
        assert '本样本赢局英雄中' in value.source.blocks[17][1]


@pytest.mark.parametrize('stage', ['initial', 'fresh'])
def test_candidate_changes_only_policy_and_offline_marker_with_full_document(stage):
    for inputs in candidate.materials().values():
        baseline = candidate.make_request(inputs, 'baseline', stage)
        actual = candidate.make_request(inputs, 'candidate', stage)
        assert baseline == candidate.baseline.make_request(inputs, 'completion', stage)
        assert actual.messages[1:] == baseline.messages[1:]
        assert actual.tools == baseline.tools
        assert actual.messages[0].content == baseline.messages[0].content + candidate.COMPLETION_NECESSITY_POLICY
        metadata = {k:v for k,v in actual.metadata.items() if k != candidate.MARKER}
        assert replace(actual, messages=baseline.messages, metadata=metadata) == baseline
        assert ('repairs' in actual.tools[0].input_schema['properties']) == (stage == 'initial')
        begin, end = '[UNTRUSTED REPORT DOCUMENT]\n', '\n[END UNTRUSTED REPORT DOCUMENT]'
        document = actual.messages[1].content
        assert document.startswith(begin) and document.endswith(end)
        assert restore_document(document[len(begin):-len(end)], inputs) == inputs.source.report
        assert candidate.estimate_runtime_request_input_ceiling(actual) <= 64000
        # A changed policy cannot silently run under the current live contract.
        with pytest.raises(ValueError, match='necessity_natural_request_binding'):
            candidate.baseline.role_for_request(actual)
        with pytest.raises(ValueError, match='necessity_natural_request_binding'):
            candidate.baseline.validate_business(visible(json_value(actual)), metadata[candidate.baseline.CONTEXT])


def test_preparation_does_not_read_labels_or_failed_opinion(tmp_path):
    expected = candidate.prepare()
    for name in ('context.json', *(f'{case}.md' for case in candidate.CASES)):
        (tmp_path/name).write_bytes((candidate.PACKAGE/name).read_bytes())
    assert candidate.prepare(tmp_path) == expected
    manifest = json.loads(expected['manifest.json'])
    assert len(manifest['requests']) == 8
    for case in candidate.CASES:
        rows = [r for r in manifest['requests'] if r['case'] == case]
        assert rows[0]['non_system_messages_sha256'] == rows[1]['non_system_messages_sha256']
        assert rows[0]['tools_sha256'] == rows[1]['tools_sha256']
        for arm in candidate.ARMS:
            assert json.loads(expected[f'{case}-{arm}.json']) == visible(json_value(
                candidate.make_request(candidate.materials()[case], arm)))
    assert manifest['provider_requests'] == manifest['key_reads'] == 0
    assert not any(manifest[k] for k in ('authorized', 'execution_ready', 'semantic_improvement_proven',
                                       'production_admitted', 'publication_allowed', 'actual_application', 'fresh_evidence'))


def test_retained_bad_opinion_still_passes_structure_without_becoming_accepted():
    raw = (candidate.PACKAGE/'retained-public-review.json').read_text(encoding='utf-8')
    evaluation = read('evaluation.json')
    assert hashlib.sha256(raw.encode()).hexdigest() == evaluation['original_public_arguments_sha256']
    wire = direct.validate(raw, candidate.materials()['a'], 'completion')
    assert [issue.block for issue in wire.issues] == [21, 18]
    edits = [e for group in wire.repairs for values in group.edits.values() for e in values]
    assert len(edits) == 5
    assert not evaluation['retained_response']['semantic_accepted']
    assert not evaluation['semantic_improvement_proven']


@pytest.mark.parametrize('arm,stage', [('unknown', 'initial'), ('candidate', 'unknown')])
def test_unknown_variant_cannot_be_prepared(arm, stage):
    with pytest.raises(ValueError, match='completion_contrast_arm_or_stage'):
        candidate.make_request(candidate.materials()['a'], arm, stage)
