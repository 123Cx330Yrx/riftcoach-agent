"""Rebuild authored full-source paired materials without model/Host execution.

The dataset's focus expectations are development hypotheses, not independent
labels or whole-report verdicts. Only report inputs enter request construction.
"""
import argparse
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

from app.evaluation.coach_report import validate_revised_report
from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_journal import write_new_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.source_patch_editor import report_inputs, _section_order
from scripts import probe_natural_duty_preservation as probe

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT/'data/evaluation/datasets/natural_duty_preservation_pairs_20261015.json'
VERSION = 'offline-natural-duty-preservation-pairs-v1'


@dataclass(frozen=True)
class MaterialPair:
    case_id: str
    original: ReviewInput
    final: ReviewInput


def read_dataset():
    return json.loads(DATASET.read_text(encoding='utf-8'))


def source_inputs(data):
    binding = data['source_binding']
    cell, request = next((c, r) for c, r in probe.frozen.frozen_cases()[0]
                         if c['key'] == binding['key'])
    inputs = probe.duty.TimedDocumentWorkflow.build_inputs(request)
    actual = dict(key=cell['key'], dataset_sha256=cell['manifest_sha256'],
                  source_input_sha256=digest(inputs.data_json),
                  source_report_sha256=digest(request.report),
                  pack_sha256=digest(inputs.pack_json))
    if actual != binding:
        raise ValueError('preservation_pairs_source_binding_changed')
    return inputs


def arithmetic_evidence(inputs, expected):
    """Recompute numeric fixture premises; do not classify natural language."""
    data = json.loads(inputs.data_json)
    facts = data['facts_and_provenance']['facts']
    rows = [(key, value) for key, value in facts.items() if key.startswith('facts:recent_match:')]
    groups = dict(win=[(k, v) for k, v in rows if v['win']],
                  loss=[(k, v) for k, v in rows if not v['win']],
                  middle_loss=[(k, v) for k, v in rows if v['role'] == 'MIDDLE' and not v['win']])
    result = {}
    for name, group in groups.items():
        values = [v[expected['metric']] for _, v in group]
        mean = sum(Decimal(str(v)) for v in values) / len(values)
        rounded = str(mean.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        if ([k for k, _ in group] != expected[name+'_rows']
                or values != expected['expected_'+name+'_values']
                or rounded != expected[name+'_mean']):
            raise ValueError('preservation_pairs_arithmetic_changed')
        result[name] = dict(row_keys=[k for k, _ in group], values=values,
                            count=len(values), mean_2dp=rounded)
    if (expected['user_task'] != data['user_utterance']
            or expected['applicable_knowledge'] != [c['citation_id'] for c in data['knowledge']['citations']]):
        raise ValueError('preservation_pairs_task_or_knowledge_changed')
    return result


def material_pairs(data=None):
    data = read_dataset() if data is None else data
    inputs = source_inputs(data)
    template = data['template']
    if template.count('{comparison}') != 1 or template.count('{duplicate}') != 1:
        raise ValueError('preservation_pairs_template_changed')
    pairs = []
    for case in data['cases']:
        if type(case['duplicate_original']) is not bool:
            raise ValueError('preservation_pairs_duplicate_flag')
        def render(segment, duplicate=False):
            text = data['segments'][segment]
            return template.replace('{comparison}', text).replace('{duplicate}', text+'\n' if duplicate else '')
        original = report_inputs(inputs, render(case['original'], case['duplicate_original']))
        final = report_inputs(inputs, render(case['final']))
        validate_revised_report(final.source.report, original.source.report)
        _section_order(original.source.report)
        _section_order(final.source.report)
        pairs.append(MaterialPair(case['id'], original, final))
    if len(pairs) != 6 or len({p.case_id for p in pairs}) != 6:
        raise ValueError('preservation_pairs_inventory')
    return pairs


def requests(pair):
    # Evaluation annotations, expected outcomes and case IDs are not arguments
    # to either builder and never become model-visible content or metadata.
    return {name: dict(
        baseline=probe.make_request(pair.final, name, 'fresh'),
        comparison=probe.comparison_request(pair.original, pair.final, name))
        for name in probe.duty.DUTIES}


def audit():
    data = read_dataset()
    inputs = source_inputs(data)
    numeric = arithmetic_evidence(inputs, data['evaluation_sources'])
    pairs = material_pairs(data)
    records = []
    for pair in pairs:
        rows = {name: {arm: dict(sha256=probe.duty.request_sha(request),
                                input_ceiling=probe.frozen.size(request))
                       for arm, request in arms.items()}
                for name, arms in requests(pair).items()}
        evaluation = next(c['evaluation'] for c in data['cases'] if c['id'] == pair.case_id)
        if (evaluation['whole_report_expected_verdict'] is not None
                or evaluation['independent_review'] != 'not_performed'
                or not evaluation['evaluation_only'] or evaluation['semantic_quality_proven']):
            raise ValueError('preservation_pairs_unsupported_quality_claim')
        records.append(dict(case_id=pair.case_id,
                            original_report_sha256=digest(pair.original.source.report),
                            final_report_sha256=digest(pair.final.source.report),
                            original_input_sha256=digest(pair.original.data_json),
                            final_input_sha256=digest(pair.final.data_json),
                            evaluation_annotation_sha256=digest(compact(evaluation)),
                            requests=rows, model_result=None, independent_result=None))
    shared = [r for r in records if r['case_id'] in ('p01', 'p02', 'p03')]
    if (len(shared) != 3 or len({r['final_input_sha256'] for r in shared}) != 1
            or len({r['original_input_sha256'] for r in shared}) != 3):
        raise ValueError('preservation_pairs_same_final_control_changed')
    for name in probe.duty.DUTIES:
        if (len({r['requests'][name]['baseline']['sha256'] for r in shared}) != 1
                or len({r['requests'][name]['comparison']['sha256'] for r in shared}) != 3):
            raise ValueError('preservation_pairs_request_control_changed')
    return dict(kind=VERSION, dataset_sha256=digest(DATASET.read_text(encoding='utf-8')),
                source_binding=data['source_binding'], arithmetic_evidence=numeric,
                cases=records, request_shape_count=len(pairs)*4,
                same_final_control_ids=[r['case_id'] for r in shared],
                maximum_input_ceiling=max(r['input_ceiling'] for c in records
                    for arms in c['requests'].values() for r in arms.values()),
                provider_calls=0, new_host_tasks=0, qualified=False,
                execution_ready=False, execution_authorized=False, publication_allowed=False,
                actual_application_or_fresh_evidence=False, semantic_detection_proven=False,
                independent_review_completed=False,
                report_origin=data['report_origin'],
                limitations=[
                    'Arithmetic checks verify fixture premises, not full-report semantic labels.',
                    'Focus expectations are primary-authored; no whole-report pass labels are assigned.',
                    'Both arms retain full sources; only the comparison arm has original-relative information.',
                    'The comparison arm also adds policy, so it does not isolate an input-only causal effect.',
                    'No sender, actual application, model response or independent judgment exists.',
                    'Familiar source material is development evidence, not holdout or qualification.'],
                audit_source_sha256=digest(Path(__file__).read_text(encoding='utf-8')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.resolve().is_relative_to(ROOT/'data/runs'):
        raise ValueError('offline_pairs_outside_runs_required')
    result = audit()
    if args.output is not None:
        write_new_json(args.output.resolve(), result)
    print(json.dumps(dict(cases=len(result['cases']), request_shapes=result['request_shape_count'],
                         max_input=result['maximum_input_ceiling'], provider_calls=0,
                         independent_review_completed=False), ensure_ascii=True))


if __name__ == '__main__':
    main()
