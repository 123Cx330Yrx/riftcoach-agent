"""Offline counterexamples at the edit boundary; never a business re-review.

Historical H5 response/Host rejection are read unchanged. All injected edits
are author-written test data. No provider, native import or run mutation.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from app.evaluation import coarse_revision_editor as cited
from app.evaluation.golden_coarse_source_projection import resolve_refs
from app.evaluation.golden_integrated_runtime import Exchange
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_stream_bridge import CAPACITY_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import frozen_cases
from app.evaluation.source_patch_editor import edit_request as independent_edit_request, report_inputs
from app.providers.models import ChatResponse, ToolCall, TokenUsage
from app.report_validation import ReportValidationError
from scripts import report_block_keyed_editor as keyed
from scripts.report_contrast_review import ContrastDocumentWorkflow as Workflow

ROOT = Path(__file__).resolve().parents[1]
MATERIAL = 'data/evaluation/fixtures/document_full_report_remaining_initial_20261012/report-H5-initial/material.json'
EVIDENCE = 'data/evaluation/results/document_full_report_remaining_host_evidence_20261012.json'
CALIBRATION = 'data/evaluation/fixtures/host_full_report_calibration_20261012/materials.json'
EXPECTED = {
    MATERIAL: '2d19fd9adf4e3df85256615ef590b79462a964342cd86e30e9ed6c34cc76c125',
    EVIDENCE: 'e9e12dc4e6431a666fa877dcb6932b25397f2cdeb584e78154b0d02530304f62',
    CALIBRATION: 'd3930389e748dfe4fb326f19b335242fe95587203890802b9e18b5a7650ab39b',
}
BEFORE = '仅这四局中单的早期死亡胜负组均值接近，暂不把这项作为主要分界。'
CORRECT = '仅这四局中单，胜局早期死亡均值为2.50次，负局为0.50次；负局更少，但这些观察不足以确定因果作用。'
BAD_SEPARATION = '仅这四局中单，胜局早期死亡均值为2.50次，负局为0.50次；因此在本样本中早死次数并未把胜局与负局分开。'


def load():
    paths = (MATERIAL, EVIDENCE, CALIBRATION)
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    for path, expected in EXPECTED.items():
        if hashes[path] != expected:
            raise ValueError('correction_audit_evidence_changed')
    material, evidence, calibration = [json.loads((ROOT / p).read_bytes()) for p in paths]
    source = next(req for row, req in frozen_cases()[0] if row['key'] == 'claim-scope:1')
    inputs = Workflow.build_inputs(replace(source, report=material['report']))
    if inputs.data_json != material['current_input_json']:
        raise ValueError('correction_audit_input_changed')
    if digest(inputs.source.report) != evidence['submission']['primary']['binding']['report_sha256']:
        raise ValueError('correction_audit_historical_report_binding')
    raw = compact(evidence['response']['tool_calls'][0]['arguments'])
    # "wire" means structural validity, NOT historical Host acceptance.
    _, wire, journal = Workflow.validate_review(raw, inputs)
    assert journal['semantic_approval'] is False
    for role in ('primary', 'independent'):
        decision = evidence['submission'][role]['stage_assessment']
        assert decision['accepted'] is False
        assert any(d['kind'] == 'wrong_correction' for d in decision['defects'])
    return inputs, wire, evidence, calibration, hashes


def simulated_exchange(request, tool, edits):
    """In-memory fault injection, not a persisted transport receipt."""
    response = ChatResponse(provider='zhipu', model='glm-5.3-flash', content=None,
        usage=TokenUsage(input_tokens=0, output_tokens=0),
        finish_reason='tool_calls', tool_calls=(ToolCall(id='OFFLINE-injected-edit',
            name=tool, arguments={'edits': edits}),))
    return Exchange(request, response, hashlib.sha256(validate_request(
        request, transport_id=CAPACITY_TRANSPORT_ID)).hexdigest())


def assemble(protocol, inputs, wire, after, *, before=BEFORE, refs=(31, 32)):
    reason = 'OFFLINE author-written counterexample; no semantic approval.'
    if protocol == 'block_keyed':
        request = keyed.edit_request(inputs, wire)
        edits = {} if after is None else {'block_4': [dict(before=before, after=after, reason=reason)]}
        return keyed.inspect_exchange(request, simulated_exchange(request, keyed.TOOL, edits),
            inputs, wire, make_final=Workflow.make_request)
    if protocol != 'source_cited':
        raise ValueError('unknown_audit_protocol')
    request = cited.edit_request(inputs, wire)
    edits = [] if after is None else [dict(block=4, before=before, after=after,
        source_ids=list(refs), reason=reason)]
    return cited.inspect_edit_exchange(request,
        simulated_exchange(request, cited.SUBMIT_TOOL, edits), inputs, wire)


def synthetic_coach_case():
    """New host-authored fixture in an existing Coach template, not repaired H5."""
    source = next(req for row, req in frozen_cases()[0] if row['key'] == 'claim-scope:1')
    base = Workflow.build_inputs(source)
    block = base.source.blocks[3][1]
    report = base.source.report.replace(block, BEFORE + '[K1]', 1)
    inputs = report_inputs(base, report)
    assert inputs.source.blocks[3][1] == BEFORE + '[K1]'
    _, wire, _ = Workflow.validate_review(compact(dict(score=80, verdict='needs_revision',
        issues=[dict(block=4, severity='medium', category='fact_error', source_ids=[31, 32],
            explanation='OFFLINE author-written fixture: 中单早死均值2.50与0.50，原句称接近。',
            suggested_correction='OFFLINE fixture: 按来源核对并修正该比较，保留其他内容。')],
        issue_resolutions=[], advisories=[])), inputs)
    return inputs, wire


def audit():
    historical_inputs, historical_wire, evidence, calibration, hashes = load()
    computed = resolve_refs(historical_inputs, [31])[0]['value']
    idx = computed['metrics'].index('deaths_before_15')
    cohort = computed['cohorts']['MIDDLE']
    numerical = {k: cohort[k][idx] for k in ('win_mean', 'loss_mean', 'all_pairs')}
    assert numerical == dict(win_mean='2.50', loss_mean='0.50', all_pairs='greater')
    format_failures = []
    for protocol in ('block_keyed', 'source_cited'):
        try:
            assemble(protocol, historical_inputs, historical_wire, CORRECT)
        except ReportValidationError as exc:
            assert 'missing headings' in str(exc)
            format_failures.append(dict(protocol=protocol, case='actual_H5',
                failure='report_missing_headings', stage='before_semantic_review'))
        else:
            raise AssertionError('historical free-form report unexpectedly editable')
    inputs, wire = synthetic_coach_case()
    # These semantic expectations are author labels, NEVER executable NLP gates.
    scenarios = (
        ('source_supported_repair', CORRECT, 'supported_repair'),
        ('h5_false_nonseparation', BAD_SEPARATION, 'wrong_replacement'),
        ('false_number', CORRECT.replace('2.50', '9.50'), 'wrong_replacement'),
        ('unsupported_cause', CORRECT + '因此减少早死必然导致失败。', 'wrong_replacement'),
        ('unwritten_universal', CORRECT + '辅助局拉低了每一个指标。', 'wrong_replacement'),
        ('empty_on_wrong_report', None, 'original_error_remains'),
    )
    rows = []
    for protocol in ('block_keyed', 'source_cited'):
        for name, after, expectation in scenarios:
            assembly = assemble(protocol, inputs, wire, after)
            expected = inputs.source.report if after is None else inputs.source.report.replace(BEFORE, after)
            assert assembly.report == expected
            assert assembly.journal['semantic_approval'] is False
            assert assembly.journal['production_admitted'] is False
            assert assembly.journal['full_final_review_required'] is True
            final = (Workflow if protocol == 'block_keyed' else cited.Current).make_request(
                report_inputs(inputs, expected))
            assert assembly.journal['final_review_request_sha256'] == keyed.request_sha(final)
            rows.append(dict(protocol=protocol, case=name, author_semantic_label=expectation,
                structural_result='assembled_requires_full_review', report_sha256=digest(expected),
                exact_untouched_bytes=True, final_request_bound=True, semantic_approval=False))
    # Actual whole-text positive control is initial-only, too. Do not silently
    # adapt its headings or claim an edit round-trip on a different report.
    correct = next(c for c in calibration['cases'] if c['case_id'] == 'V2')
    report = '\n\n'.join(b['text'] for b in correct['report'])
    clean = report_inputs(historical_inputs, report)
    _, clean_wire, _ = Workflow.validate_review(compact(dict(score=97, verdict='pass',
        issues=[], issue_resolutions=[], advisories=[])), clean)
    for protocol in ('block_keyed', 'source_cited'):
        try:
            assemble(protocol, clean, clean_wire, None)
        except ReportValidationError as exc:
            assert 'missing headings' in str(exc)
            format_failures.append(dict(protocol=protocol, case='actual_V2_empty_edit',
                failure='report_missing_headings', stage='before_semantic_review'))
        else:
            raise AssertionError('historical free-form control unexpectedly editable')
        supported = report_inputs(inputs, inputs.source.report.replace(BEFORE, CORRECT))
        _, keep_wire, _ = Workflow.validate_review(compact(dict(score=97, verdict='pass',
            issues=[], issue_resolutions=[], advisories=[])), supported)
        result = assemble(protocol, supported, keep_wire, None)
        assert result.report == supported.source.report
        rows.append(dict(protocol=protocol, case='synthetic_supported_keep',
            author_semantic_label='author_written_control_not_new_business_verdict',
            structural_result='unchanged_requires_full_review',
            report_sha256=digest(result.report), semantic_approval=False))
    edit = keyed.edit_request(historical_inputs, historical_wire)
    original_correction = historical_wire.issues[0].suggested_correction
    assert original_correction in edit.messages[1].content
    # The dormant alternative can receive complete sources without a prior review;
    # this is a request capability only, not admission or end-to-end evidence.
    alternate = independent_edit_request(historical_inputs)
    assert 'review_findings' not in alternate.messages[1].content
    assert original_correction not in alternate.messages[1].content
    assert '每个问题必须按照 evidence 和 suggested_correction 修正' not in edit.messages[0].content
    for path, sha in hashes.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha
    return dict(kind='OFFLINE-correction-consumption-counterexamples-v1',
        project_provider_calls=0, project_http_calls=0, native_tasks=0, business_submissions=0,
        qualification=0, historical_host_rejection_unchanged=True,
        actual_free_form_edit_failures=format_failures,
        matrix_input_kind='NEW author-written Coach-format fixture; not historical H5',
        lower_level_fault_injection_bypasses_host_gate=True, source_sha256=hashes,
        computed_middle_early_deaths=numerical, original_correction=original_correction,
        edit_policy_sha256=digest(edit.messages[0].content),
        current_edit_preserves_complete_review=True,
        source_first_request_without_review_constructible=True, rows=rows,
        decision='Do not replace the editor schema or add citation IDs as a semantic fix.',
        unresolved='No model tested: source-first task allocation is only a prospective alternative; '
            'its full runtime/budget path and semantic quality remain unproven.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    # Create only; an existing audit is evidence, not a file to silently refresh.
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
