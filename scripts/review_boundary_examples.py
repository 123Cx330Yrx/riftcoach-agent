"""Fixed out-of-domain acceptance examples; diagnostic only, no runtime registration.

Examples are authored development guidance, not evidence about the submitted
report. They never enter its sources or replace the accepted business policy.
"""
from dataclasses import replace

from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_role_correction_scope import RoleCorrectionScopeReviewWorkflow as Baseline


EXAMPLES = """[审查边界教学示例：虚构印刷厂，不是本次报告或证据]
以下只示范如何应用已有验收标准，不规定报告写法，也不替代全文各项业务检查。不得把示例数字、结论或问题当作待审报告事实，不得引用示例作为来源。
共同资料：小册子甲班每小时印120份、乙班80份；全部印品甲乙两班返工率都为4%；仅小册子的返工率分别为1%和7%。全部印品包括小册子和海报。
例甲，报告全文：“小册子甲班印得较快。返工率则两班一致。这里的返工率指全部印品，两班均为4%。”
裁决：这两项比较均符合资料。最后一句明确解释前一句返工率的对象；印速和返工率比较不同范围本身不构成矛盾。可建议前移限定，不能要求改正事实或强制新增一项小册子返工率比较。
例乙，报告全文：“小册子甲班印得较快。仅小册子的返工率两班一致。全部印品返工率两班均为4%。”
裁决：第二句明确对象与1%/7%冲突，应修正该句。第三句是另一范围的正确事实，不能撤销第二句明确错误；无需改动正确的印速结论。
例丙，报告全文：“返工率一致，因此安排两班以相同返工率生产。”没有解释比较对象，任务也没说明印品种类。
裁决：资料允许多种范围且会影响安排，不能自行选4%解释后放过；应指出影响行动的未解范围，要求明确对象并核对相应资料。
例丁，报告全文：“全部印品本次返工率均为4%，所以今后每批都必然一致。”
裁决：本次4%正确，未来必然结论没有依据；修正未来外推，保留本次事实。不能因为有范围限定就忽略其后独立的全称断言。
[教学示例结束；仅按随后提交的完整报告及真实来源审查]
"""


def request_for(inputs, **kwargs):
    base = Baseline.make_request(inputs, **kwargs)
    if kwargs.get('accepted') is not None:
        return base
    return budget_check(replace(base, messages=(
        replace(base.messages[0], content=base.messages[0].content + '\n' + EXAMPLES),
        *base.messages[1:])))


class DiagnosticWorkflow(Baseline):
    """Injectable offline prototype, deliberately absent from product factories."""
    make_request = staticmethod(request_for)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = Baseline.validate_review(raw, inputs, previous_raw=previous_raw)
        return payload, wire, dict(journal, experiment='review-boundary-examples-v1',
            validator_policy_sha256=journal['policy_sha256'],
            policy_sha256=digest(request_for(inputs, previous_raw=previous_raw).messages[0].content))
