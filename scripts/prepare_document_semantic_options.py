"""Build inert policy alternatives from public sealed requests; never sends IO.

This preparation does not define a runnable candidate identity or grant quality.
Only the fictional teaching suffix changes; all business rules, report/source
messages, tools and request limits remain identical to each fixed request.
"""
import copy
import hashlib
import json
from pathlib import Path

from app.evaluation.golden_role_boundary_examples import EXAMPLES
from scripts.report_contrast_review import CONTRASTS

ROOT = Path(__file__).resolve().parents[1]
OLD = 'data/evaluation/results/golden_document_full15_time600_result_20261010.json'
NEW = 'data/evaluation/results/golden_document_remaining4_time600_result_20261011.json'
SOURCES = (
    (OLD, 'claim-scope:4', 'initial'),
    (OLD, 'scope:3', 'final'),
    (OLD, 'scope:4', 'initial'),
    (NEW, 'observed:3', 'final'),
    (NEW, 'observed:5', 'initial'),
)
SEQUENCE = '''[审查决策顺序；不增加输出字段或调用]
先从完整报告确定原文实际断言，再核来源；不要先找到一个来源差异，再补造作者没有说的命题。
对拟列入issues的每项问题，依次核验：
1. 原文实际断言的对象、指标、组别、期间、量词是什么？同一对象的全文明确限定或后文解释是否已消解省略？不得补入每个、全部、长期或因果等未写断言。
2. 按这个实际命题核来源。指出具体冲突；若是未解歧义，说明各解释及其对结论或行动的不同影响。正确的另一对象事实不能撤销明确错误。
3. 修法仅覆盖已确认错误和有来源的直接影响；核摘要与正文是否仍留下同一错误，也核修法自己的例子和理由。不把正确内容或可选措辞一并改错。
4. 找不到实际冲突或影响结论的未解歧义时，不输出事实问题；可读性建议沿现有advisories合同。标题、否定、条件及复合句仍全部核验。
上述是现有标准的执行顺序；仍提交现有五字段、只调用一次既有工具，不输出思考过程、额外账本或新字段。
[决策顺序结束；仅按随后完整报告和真实来源审查]
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def prepare(root=ROOT):
    alternatives = {'expanded_examples': CONTRASTS, 'short_examples': EXAMPLES,
                    'decision_sequence': SEQUENCE}
    rows, policies = [], {}
    for seal_path, key, stage in SOURCES:
        seal_bytes = (root / seal_path).read_bytes()
        seal = json.loads(seal_bytes)
        relative = key.replace(':', '-') + '/' + stage + '/issued-request.json'
        request = seal['public_json_contents'][relative]
        policy = request['messages'][0]['content']
        assert request['messages'][0]['role'] == 'system'
        assert policy.count(CONTRASTS) == 1 and policy.endswith(CONTRASTS)
        common = policy[:-len(CONTRASTS)]
        outside = copy.deepcopy(request)
        outside['messages'][0]['content'] = '<POLICY>'
        variants = {}
        for name, suffix in alternatives.items():
            variant = copy.deepcopy(request)
            variant['messages'][0]['content'] = common + suffix
            changed = copy.deepcopy(variant)
            changed['messages'][0]['content'] = '<POLICY>'
            assert changed == outside
            assert variant['messages'][0]['content'].startswith(common)
            policy_sha = sha(variant['messages'][0]['content'].encode('utf-8'))
            policies[policy_sha] = variant['messages'][0]['content']
            variants[name] = dict(policy_sha256=policy_sha,
                constructed_request_sha256=sha(canonical(variant)),
                policy_characters=len(variant['messages'][0]['content']))
        assert alternatives['expanded_examples'] == CONTRASTS
        assert variants['expanded_examples']['constructed_request_sha256'] == sha(canonical(request))
        rows.append(dict(seal=seal_path, seal_sha256=sha(seal_bytes), key=key,
            stage=stage, request_path=relative,
            original_issued_request_sha256=seal['original_file_sha256'][relative],
            nonpolicy_canonical_sha256=sha(canonical(outside)),
            common_business_policy_sha256=sha(common.encode('utf-8')),
            variants=variants))
    return dict(kind='document-semantic-options-inert-preparation-v1',
        provider_calls=0, execution_ready=False, production_admitted=False,
        new_qualification=0, sample_count=len(rows),
        varies_only='fictional teaching suffix of system policy',
        unchanged=['complete report and sources', 'business acceptance rules',
            'tool schema and output fields', 'model and timing limits',
            'metadata and existing identity markers'],
        limitation='Constructed hashes are canonical JSON, not issued byte identities. '
            'Existing candidate metadata is preserved for comparison only; these are '
            'inert alternatives, not valid requests for a new runnable candidate. '
            'No semantic judgment, cost authorization or qualification is implied.',
        samples=rows, exact_policies=policies)


if __name__ == '__main__':
    output = ROOT / 'data/evaluation/results/document_semantic_options_preparation_20261011.json'
    value = prepare()
    with output.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    print(output)
