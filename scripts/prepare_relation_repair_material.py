"""Author development controls only; no execution package, API or Host task."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

from scripts.document_full_report_diagnostic import source_inputs, source_payload, base

ROOT = Path(__file__).resolve().parents[1]
SEED = 'data/evaluation/fixtures/host_relation_material_calibration_20261012/materials.json'
SEED_SHA = '53bea63165bc5eebfdbd8793c56e801b741f852b5f6738fea9b34a7fb6025f85'
CORRECT = '仅这四局中单的早期死亡胜负组均值并不接近。'
INCORRECT = '仅这四局中单的早期死亡胜负组均值接近。'
PARAGRAPH = ('全部五局15分钟前死亡的胜组均值为2.50次，负组约2.67次。'
    '仅中单时，胜场逐局为3、2次，负场为0、1次，均值分别2.50与0.50。'
    + CORRECT + '这些历史记录不能据以确定早死对胜负的因果作用。[K1][K5]')


def prepare():
    raw = (ROOT / SEED).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SEED_SHA:
        raise ValueError('repair_material_seed_changed')
    seed = json.loads(raw)
    original = next(c for c in seed['cases'] if c['case_id'] == 'R4')
    blocks = [b['text'] for b in original['report']]
    assert len(blocks) == 26 and '不等于数值未区分' in blocks[13]
    # Both new documents use the same explicit population; the historical R4
    # statement remains untouched and is not reclassified as a factual error.
    assert blocks[5].count('这 5 局内') == 1
    blocks[5] = blocks[5].replace('这 5 局内', '这 4 局中单内')
    blocks[13] = PARAGRAPH
    cases = []
    for key, target in (('U1', CORRECT), ('U2', INCORRECT)):
        texts = deepcopy(blocks)
        texts[13] = PARAGRAPH.replace(CORRECT, target)
        report = '\n\n'.join(texts)
        assert '不等于数值未区分' not in report and '每个中单胜场的值都高于每个中单负场' not in report
        inputs = source_inputs(report)
        parsed = list(inputs.source.blocks)
        assert len(parsed) == 26 and [t for _, t in parsed] == texts
        current, prior = json.loads(inputs.data_json), json.loads(original['current_input_json'])
        assert current['source_index']['evidence_keys'] == prior['source_index']['evidence_keys']
        assert {k:v for k,v in current.items() if k != 'source_index'} == {
            k:v for k,v in prior.items() if k != 'source_index'}
        request = base.TimedDocumentWorkflow.make_request(inputs)
        assert request.messages[0].content == seed['full_policy_text']
        actual_source = source_payload(request.messages[2].content)
        previous_source = source_payload(original['source_message'])
        # These are full-report binding digests, not facts. Regenerate all of
        # them; never mix an old message digest with new document block IDs.
        for name, field in (('source_index', 'source_digest'),
                            ('source_roots', 'catalog_sha256'), ('computed_evidence', 'source_digest')):
            actual_source[name].pop(field)
            previous_source[name].pop(field)
        assert actual_source == previous_source
        assert request.messages[3].content == original['deterministic_source_message']
        cases.append(dict(case_id=key, report=report,
            current_input_json=inputs.data_json,
            source_message=request.messages[2].content,
            deterministic_source_message=request.messages[3].content,
            report_blocks=[dict(block=k, text=t) for k, t in parsed]))
    assert cases[0]['report'].replace(CORRECT, INCORRECT, 1) == cases[1]['report']
    assert sum([3, 2]) / 2 == 2.5 and sum([0, 1]) / 2 == .5 and min([3, 2]) > max([0, 1])
    return dict(kind='author-development-material-only-v1', execution_authorized=False,
        execution_package=False, provider_calls=0, independent_calibration=False,
        source_fixture=SEED, source_sha256=SEED_SHA,
        full_policy_text=seed['full_policy_text'], cases=cases,
        operator_only_expectations=dict(U1='preserve all factual content',
            U2='correct only block 14 proximity claim; do not introduce non-separation or causal claims'),
        limits=['familiar sources; not holdout', 'removes explicit report-body repair hint, not complete source evidence',
            'not proof of why H5 failed or T9 succeeded', 'no policy change, model response or quality qualification'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = prepare()
    with args.output.open('x', encoding='utf-8', newline='\n') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(json.dumps(dict(cases=2, actual_blocks_each=26, difference='one sentence', provider_calls=0)))
