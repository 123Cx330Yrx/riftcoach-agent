"""Heading recognition is structural, never task or model-quality approval."""
import pytest

from app.evaluation.coach_report import validate_revised_report
from app.evaluation.source_patch_editor import _section_order
from app.report_validation import COACH_REPORT_HEADINGS, report_heading_identity, report_section_body
from app.harness.steps import CoachDraft
from app.runtime.coach_contract import guard_coach_draft


@pytest.mark.parametrize('newline', ['\n', '\r\n'])
@pytest.mark.parametrize('suffix', ['', '：仅用于观摩', ': observation', ' 说明',
    '（观摩性质）', '(observation)', '（观摩性质）：说明'])
@pytest.mark.parametrize('title', [COACH_REPORT_HEADINGS[6], '## 6. 观摩练习计划'])
def test_section_extraction_preserves_text_and_excludes_other_sections(newline, suffix, title):
    report = newline.join(COACH_REPORT_HEADINGS).replace(COACH_REPORT_HEADINGS[6],
        title + suffix + newline + '保留原文\t15分钟。' + newline)
    report += newline + '来源里提到30分钟。'
    draft = CoachDraft(report=report)
    assert guard_coach_draft(draft, None) is draft
    validate_revised_report(report, report)
    _section_order(report)
    assert report_section_body(report, COACH_REPORT_HEADINGS[6]) == '保留原文\t15分钟。' + newline * 2


@pytest.mark.parametrize('suffix', ['伪造', '（未闭合', '(unclosed', '（错误)',
    '()', '（）', '（说明）伪造', '（外层（内层））'])
def test_lookalike_or_incomplete_qualifier_does_not_satisfy_section(suffix):
    title = COACH_REPORT_HEADINGS[6] + suffix
    assert report_heading_identity(title) is None
    report = '\n'.join(COACH_REPORT_HEADINGS).replace(COACH_REPORT_HEADINGS[6], title)
    with pytest.raises(ValueError):
        guard_coach_draft(CoachDraft(report=report), None)


@pytest.mark.parametrize('fault', ['inline', 'fenced', 'duplicate', 'swapped', 'lookalike'])
def test_unusable_section_never_becomes_a_memory_acknowledgement(fault):
    old, alias = COACH_REPORT_HEADINGS[6], '## 6. 观摩练习计划'
    report = '\n'.join(COACH_REPORT_HEADINGS).replace(old, alias + '\n15分钟。')
    if fault == 'inline': report = report.replace(alias, '正文 ' + alias)
    if fault == 'fenced': report = report.replace(alias, '```\n' + alias + '\n```')
    if fault == 'duplicate': report = report.replace(alias, alias + '\n' + old)
    if fault == 'swapped': report = report.replace(alias, COACH_REPORT_HEADINGS[5]).replace(
        COACH_REPORT_HEADINGS[5], alias, 1)
    if fault == 'lookalike': report = report.replace(alias, alias + '假标题')
    with pytest.raises(ValueError):
        _section_order(report)
    assert report_section_body(report, old) == ''
