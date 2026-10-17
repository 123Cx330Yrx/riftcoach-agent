"""Actual historical tool output, deterministic consumption only, no regrading."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket

import pytest

from app.evaluation.golden_review_experiment import compact
from app.evaluation.source_patch_editor import report_inputs
from scripts import prepare_reviewer_profile_screen as screen
from scripts import review_duty_direct_patch as direct

WITNESS = Path(__file__).resolve().parents[1] / 'data/evaluation/fixtures/reviewer_route_recovery_20261018'
SYNTHETIC_PASS = dict(score=95, verdict='pass', issues=[], repairs=[], advisories=[], issue_resolutions=[])


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('offline witness cannot connect')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


@pytest.fixture(scope='module')
def sample():
    raw = (WITNESS / 'r02-review.json').read_bytes()
    manifest = json.loads((WITNESS / 'manifest.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == manifest['review_sha256']
    inputs = report_inputs(screen.source_inputs(), (screen.PACKAGE / 'r02.md').read_text(encoding='utf-8'))
    return inputs, json.loads(raw)


def preview(inputs, review):
    # A synthetic second-duty pass permits exercising the existing assembler.
    # It is not a second review, native event, live edit, or publication proof.
    return direct.preview(inputs, [direct.bind(inputs, 'facts', compact(review)),
        direct.bind(inputs, 'completion', compact(SYNTHETIC_PASS))])


def test_category_variants_do_not_change_repair_consumption(sample):
    inputs, original = sample
    results = []
    for category in ('other', 'fact_error', 'unsupported_comparison'):
        review = deepcopy(original)
        review['issues'][1]['category'] = category
        result = preview(inputs, review)
        assert result.journal['preview_only'] and not result.journal['semantic_approval']
        assert {op['block'] for op in result.journal['operations']} == {7, 19}
        expected = inputs.source.report
        for repair in review['repairs']:
            for key, edits in repair['edits'].items():
                block = int(key.removeprefix('block_'))
                for edit in edits:
                    assert inputs.source.blocks[block - 1][1].count(edit['before']) == 1
                    expected = expected.replace(edit['before'], edit['after'], 1)
        assert result.report == expected
        results.append(result.report)
    assert results[0] == results[1] == results[2]


@pytest.mark.parametrize('fault', ['missing_repair', 'wrong_block', 'bad_anchor', 'overlap'])
def test_block7_cannot_mask_invalid_block19_repair(sample, fault):
    inputs, original = sample
    review = deepcopy(original)
    if fault == 'missing_repair': review['repairs'].pop()
    elif fault == 'wrong_block':
        review['repairs'][1]['edits'] = {'block_7': review['repairs'][1]['edits']['block_19']}
    elif fault == 'bad_anchor': review['repairs'][1]['edits']['block_19'][0]['before'] = 'NO_SUCH_ANCHOR'
    elif fault == 'overlap':
        review['repairs'][1]['edits']['block_19'] *= 2
    with pytest.raises(ValueError): preview(inputs, review)
