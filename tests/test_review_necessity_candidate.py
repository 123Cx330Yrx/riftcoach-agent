"""Portable full-source preservation and isolation, not model quality tests."""
from dataclasses import replace
import hashlib
import json
import socket

import pytest

from app.evaluation import sol_natural_contract as baseline
from app.evaluation.source_patch_editor import report_inputs
from scripts import review_duty_direct_patch as direct
from scripts import review_necessity_candidate as candidate
from scripts.prepare_reviewer_profile_screen import visible, json_value
from scripts.report_document_view import restore_document


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def read(name):
    return json.loads((candidate.PACKAGE / name).read_text(encoding='utf-8'))


def test_full_material_and_one_change_per_contrast():
    inputs = candidate.materials()
    evaluation = read('evaluation.json')
    for name, expected in evaluation['files_sha256'].items():
        assert hashlib.sha256((candidate.PACKAGE / name).read_bytes()).hexdigest() == expected
    assert inputs['a'].source.report == read('context.json')['report']
    for case, edit in evaluation['contrasts'].items():
        parent = inputs[edit['parent']]
        assert parent.source.report.count(edit['before']) == 1
        assert inputs[case] == report_inputs(parent, parent.source.report.replace(edit['before'], edit['after'], 1))
    # Same complete evidence/knowledge/user task across all three reports.
    data = [json.loads(value.data_json) for value in inputs.values()]
    assert all(value.pack_json == inputs['a'].pack_json for value in inputs.values())
    assert all({k: v for k, v in value.items() if k != 'source_index'} ==
               {k: v for k, v in data[0].items() if k != 'source_index'} for value in data)
    assert len(inputs['a'].source.blocks) == len(inputs['b'].source.blocks) == len(inputs['c'].source.blocks) == 28


@pytest.mark.parametrize('name', ['facts', 'completion'])
@pytest.mark.parametrize('stage', ['initial', 'fresh'])
def test_candidate_preserves_complete_inputs_schema_and_envelope(name, stage):
    for inputs in candidate.materials().values():
        base = baseline.make_request(inputs, name, stage)
        actual = candidate.make_request(inputs, name, stage)
        assert actual.messages[1:] == base.messages[1:]
        assert actual.tools == base.tools
        metadata = {k: v for k, v in actual.metadata.items() if k != candidate.MARKER}
        assert replace(actual, messages=base.messages, metadata=metadata) == base
        assert ('repairs' in actual.tools[0].input_schema['properties']) == (stage == 'initial')
        document = actual.messages[1].content
        begin, end = '[UNTRUSTED REPORT DOCUMENT]\n', '\n[END UNTRUSTED REPORT DOCUMENT]'
        assert document.startswith(begin) and document.endswith(end)
        assert restore_document(document[len(begin):-len(end)], inputs) == inputs.source.report
        assert candidate.estimate_runtime_request_input_ceiling(actual) <= 64000
        # The historical receiver must not silently accept a policy variant.
        with pytest.raises(ValueError, match='sol_request_binding'):
            baseline.role_for_request(actual)
        if name == 'facts':
            with pytest.raises(ValueError, match='sol_dynamic_request_binding'):
                baseline.validate_business(visible(json_value(actual)), metadata[baseline.CONTEXT])
        else:
            assert actual.messages == base.messages


def test_preparation_does_not_read_evaluator_or_retained_opinion(tmp_path):
    files = candidate.prepare()
    for name in ('context.json', 'a.md', 'b.md', 'c.md'):
        (tmp_path / name).write_bytes((candidate.PACKAGE / name).read_bytes())
    # No evaluator sidecar or prior response exists in this material-only dir.
    assert candidate.prepare(tmp_path) == files
    manifest = json.loads(files['manifest.json'])
    assert len(manifest['cases']) == 3
    for case in candidate.CASES:
        business = json.loads(files[f'{case}-facts.json'])
        assert business == visible(json_value(candidate.make_request(candidate.materials()[case], 'facts')))
    assert manifest['provider_requests'] == 0
    assert not any(manifest[k] for k in ('authorized', 'semantic_improvement_proven',
                                       'production_admitted', 'publication_allowed'))


def test_old_false_positive_still_passes_structure_not_semantics():
    raw = (candidate.PACKAGE / 'retained-public-review.json').read_text(encoding='utf-8')
    evaluation = read('evaluation.json')
    assert hashlib.sha256(raw.encode()).hexdigest() == evaluation['original_public_arguments_sha256']
    wire = direct.validate(raw, candidate.materials()['a'], 'facts')
    # No keyword filter discards the model's mistaken issue or rewrites history.
    assert [issue.block for issue in wire.issues] == [10, 21]
    assert len(wire.repairs) == 2
    assert not evaluation['semantic_improvement_proven']
