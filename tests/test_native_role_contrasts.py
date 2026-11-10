"""Arithmetic counterexamples and source delivery, not model-quality claims."""
from decimal import Decimal, localcontext

import pytest

from app.evaluation import golden_computed_evidence as computed
from app.evaluation import golden_native_issues_review as native
from app.evaluation import golden_semantic_sources as sources
from app.evaluation.golden_review_experiment import compact
from tests.test_golden_comparison_reassessment import inputs_for
from tests.test_golden_computed_evidence import changed_pack


def contrast(evidence, metric, role='MIDDLE'):
    table = evidence['role_contrasts']
    return dict(zip(table['columns'], table['cohorts'][role][evidence['metrics'].index(metric)]))


def test_damage_and_cs_have_different_composition_effects_from_raw_values():
    evidence = computed.build(inputs_for(), include_role_contrasts=True)
    damage = contrast(evidence, 'damage_per_min')
    cs = contrast(evidence, 'cs_per_min')
    assert damage['role_win_minus_loss'] == '669.235'
    assert damage['selected_gap_minus_role_gap'] == '26.1833333333333333333333333'
    assert Decimal(damage['role_win_minus_loss']) / Decimal(damage['selected_win_minus_loss']) > Decimal('.96')
    assert cs['role_win_minus_loss'] == '-0.205'
    assert Decimal(cs['selected_win_minus_loss']) > 0
    assert Decimal(cs['selected_gap_minus_role_gap']) > Decimal(cs['selected_win_minus_loss'])


@pytest.mark.parametrize('values,expected', [
    ((100, 0, 100, 100), ('50', '0', '50')),
    ((10, 100, 20, 10), ('-50', '-10', '-40')),
    ((10, 10, 10, 10), ('0', '0', '0')),
    ((100, 0, 200, 100), ('0', '-100', '100')),
])
def test_other_role_and_changed_values_can_reverse_or_remove_the_effect(values, expected):
    roles = [('TOP', True), ('UTILITY', False), ('TOP', False), ('UTILITY', True)]
    rows = [dict(match_id=f'T_{n}', included_in_aggregate=True, role=role, win=win,
                 damage_per_min=value) for n, ((role, win), value) in enumerate(zip(roles, values))]
    evidence = computed.build(inputs_for(rows), include_role_contrasts=True)
    row = contrast(evidence, 'damage_per_min', 'TOP')
    assert tuple(row[k] for k in ('selected_win_minus_loss', 'role_win_minus_loss',
                                  'selected_gap_minus_role_gap')) == expected
    assert set(evidence['role_contrasts']['cohorts']) == {'TOP', 'UTILITY'}


@pytest.mark.parametrize('kind', ['missing_metric', 'unknown_outcome', 'capped'])
def test_incomplete_selected_data_cannot_become_a_numeric_composition_effect(kind):
    inputs = inputs_for()
    key = next(k for k in inputs.source.evidence_keys if k.startswith('facts:recent_match:'))
    def mutate(p):
        if kind == 'missing_metric': p['facts'][key]['damage_per_min'] = None
        if kind == 'unknown_outcome': p['facts'][key]['win'] = None
        if kind == 'capped': p['facts']['facts:sample_boundaries']['match_rows_omitted_by_cap'] = 1
    changed = changed_pack(inputs, mutate)
    evidence = computed.build(changed, include_role_contrasts=True)
    row = contrast(evidence, 'damage_per_min')
    assert row['selected_win_minus_loss'] is row['selected_gap_minus_role_gap'] is None


def test_one_outcome_role_has_no_gap_and_legacy_shape_is_unchanged():
    inputs = inputs_for()
    before = computed.build(inputs)
    after = computed.build(inputs, include_role_contrasts=True)
    row = contrast(after, 'damage_per_min', 'UTILITY')
    assert row['selected_win_minus_loss'] is not None
    assert row['role_win_minus_loss'] is row['selected_gap_minus_role_gap'] is None
    after.pop('role_contrasts')
    assert before == after


def test_contrasts_ignore_report_wording_and_ambient_precision():
    first = computed.build(inputs_for(), include_role_contrasts=True)['role_contrasts']
    other_input = inputs_for(report='故意声称所有差距都由辅助造成。')
    with localcontext() as ctx:
        ctx.prec = 3
        other = computed.build(other_input, include_role_contrasts=True)
    assert other['role_contrasts'] == first


def test_native_request_and_issue_resolver_bind_same_full_contrast_source():
    inputs = inputs_for()
    built = native.request(inputs)
    data = native.strict_json(built.messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])
    catalog = sources.source_catalog(inputs, include_role_contrasts=True)
    ref = next(n for n, entry in catalog.items() if entry.key == sources.COMPUTED_KEY)
    resolved = native.resolve_refs(inputs, [ref])[0]
    assert resolved['value'] == data['computed_evidence']
    assert resolved['catalog_sha256'] == data['source_roots']['catalog_sha256']
    assert sources.resolve_refs(inputs, [ref])[0]['catalog_sha256'] != resolved['catalog_sha256']
    assert 'role_contrasts' not in sources.resolve_refs(inputs, [ref])[0]['value']
    raw = compact(dict(score=70, verdict='needs_revision', issues=[dict(block=1,
        source_ids=[ref], severity='medium', category='unsupported_comparison',
        explanation='离线接口见证，不是模型的语义判断。', suggested_correction='核对各指标。')], issue_resolutions=[]))
    _, accepted, journal = native.validate(raw, inputs)
    assert journal['selected_sources'][0]['selected_sources'][0]['value'] == data['computed_evidence']
    for request in (native.request(inputs, previous_raw=raw, diagnostics=[]), native.request(inputs, accepted=accepted)):
        followup = native.strict_json(request.messages[1].content.split('[UNTRUSTED DATA]\n')[1].split('\n[END UNTRUSTED DATA]')[0])
        assert followup['computed_evidence'] == data['computed_evidence']
