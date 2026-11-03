"""Offline material integrity and repair feasibility, never model quality."""
from copy import deepcopy
from decimal import Decimal
import json
import shutil
import socket

import pytest

from app.evaluation.golden_review_experiment import compact
from app.evaluation.source_patch_editor import report_inputs
from scripts import prepare_reviewer_semantic_screen as material
from scripts import review_duty_direct_patch as direct


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('material checks cannot connect')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture(scope='module')
def source():
    return material.source.source_inputs()


def test_submitted_requests_reproduce_and_retain_sources(source):
    result = material.verify()
    for row in result['rows']:
        case, duty = row['id'].split('-')
        report = (material.PACKAGE / (case + '.md')).read_bytes().decode('utf-8')
        inputs = report_inputs(source, report)
        before, after = json.loads(source.data_json), json.loads(inputs.data_json)
        before.pop('source_index'); after.pop('source_index')
        assert before == after
        business = json.loads((material.PACKAGE / 'requests' / (row['id'] + '.json')).read_bytes())
        wire = json.loads((material.PACKAGE / 'wire' / (row['id'] + '.json')).read_bytes())
        original = material.source.make_request(source, duty)
        assert business['messages'][0]['content'] == original.messages[0].content
        assert business['messages'][3]['content'] == original.messages[3].content
        assert wire['input'] == business['messages']
        assert wire['tools'][0]['parameters'] == business['tools'][0]['input_schema']
        assert wire['tool_choice'] == {'type': 'function', 'name': 'submit_report_review'}
        assert wire['stream'] is False
        assert row['existing_local_input_estimate'] <= 64000


def test_evaluation_and_primary_opinions_not_inputs(tmp_path):
    for case in material.CASES:
        shutil.copyfile(material.PACKAGE / (case + '.md'), tmp_path / (case + '.md'))
    # Assembly succeeds with no evaluation sidecar at all.
    before = material.assemble(tmp_path)
    for name in ('evaluation.json', 'primary-material-review.json'):
        (tmp_path / name).write_text('{"unexpected":"DO_NOT_LEAK_GOLD_OR_OPINION"}')
    assert material.assemble(tmp_path) == before
    assert all(b'DO_NOT_LEAK' not in raw for raw in before[1].values())


def test_mathematical_control_and_counterexample_from_rows(source):
    facts = json.loads(source.data_json)['facts_and_provenance']['facts']
    rows = [v for k, v in facts.items() if k.startswith('facts:recent_match:')]
    middle = [r for r in rows if r['role'] == 'MIDDLE']
    wins = [r for r in middle if r['win']]
    losses = [r for r in middle if not r['win']]
    def mean(group, field):
        return sum(Decimal(str(r[field])) for r in group) / len(group)
    assert [r['deaths_before_15'] for r in middle] == [3, 0, 1, 2]
    assert mean(middle, 'deaths_before_15') == Decimal('1.5')
    assert mean(rows, 'deaths_before_15') == Decimal('2.6')
    for field, w, l in [('cs_per_min', '8.805', '9.01'),
                        ('damage_per_min', '1286.755', '617.52'),
                        ('gold_per_min', '505.29', '432.815'),
                        ('vision_score', '33.5', '34')]:
        assert mean(wins, field) == Decimal(w)
        assert mean(losses, field) == Decimal(l)
    assert not all(l['cs_per_min'] > w['cs_per_min'] for l in losses for w in wins)
    assert facts['external:opgg:00:01']['rank'] == 12
    assert facts['external:opgg:00:01']['win_rate'] == .49


def test_reference_repairs_and_clean_no_edit():
    previews = material.reference_previews()
    assert [r['operations'] for r in previews] == [0, 1, 1]
    assert len({r['assembled_sha256'] for r in previews}) == 1


@pytest.mark.parametrize('case,duty', [('s02', 'facts'), ('s03', 'completion')])
@pytest.mark.parametrize('fault', ['missing_repair', 'bad_anchor', 'overlapping_other_duty'])
def test_bad_reference_cannot_become_valid_edit(source, case, duty, fault):
    evaluation = material.check_contrasts()
    opinions = deepcopy(evaluation['synthetic_reference_reviews'][case])
    if fault == 'missing_repair':
        opinions[duty]['repairs'] = []
    elif fault == 'bad_anchor':
        repairs = opinions[duty]['repairs'][0]['edits']
        next(iter(repairs.values()))[0]['before'] = 'NO_SUCH_SOURCE_ANCHOR'
    else:
        other = 'completion' if duty == 'facts' else 'facts'
        opinions[other] = deepcopy(opinions[duty])
    inputs = report_inputs(source, (material.PACKAGE / (case + '.md')).read_text(encoding='utf-8'))
    with pytest.raises(ValueError):
        direct.preview(inputs, [direct.bind(inputs, d, compact(opinions[d])) for d in material.source.DUTIES])


def test_extra_report_mutation_breaks_manifest(tmp_path):
    shutil.copytree(material.PACKAGE, tmp_path, dirs_exist_ok=True)
    path = tmp_path / 's02.md'
    path.write_bytes(path.read_bytes() + '\n新增无来源结论。\n'.encode('utf-8'))
    with pytest.raises(ValueError, match='material_contrast_changed'):
        material.check_contrasts(tmp_path)
