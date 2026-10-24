"""Unadmitted whole-text contrast candidate on the existing result contract.

Replace the old fictional teaching examples, not facts, standards or result
fields. No Host labels, historical opinions, scope ledger or paid entrypoint.
"""
from dataclasses import replace

from app.evaluation import document_review_identity as identity
from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.golden_review_experiment import digest
from app.evaluation.golden_role_boundary_examples import EXAMPLES
from app.runtime.coach_contract import DOCUMENT_REVIEW_COACH_CONTRACT
from app.runtime.document_review_roles import DocumentRoleRoutedProvider
from scripts import report_block_keyed_editor as editor
from scripts.report_document_workflow import DocumentReviewWorkflow, request_sha

VERSION = 'offline-whole-text-contrast-review-v1'
METADATA = 'review_teaching_candidate'

CONTRASTS = """[审查边界教学示例：虚构印刷厂，不是本次报告或证据]
仅演示既有验收标准的应用；不得引用这些虚构数据为报告来源。以下各例均为完整短报告。
资料甲：小册子甲班每小时印120份、乙班80份；全部印品返工率甲乙都为4%，仅小册子分别为1%和7%；全部印品含小册子和海报。
甲1全文：“小册子甲班印得较快。返工率两班一致。这里的返工率指全部印品，两班均4%。”两项均符合资料，后句消解范围；可建议前移限定，无须修事实。
甲2全文：“小册子甲班印得较快。仅小册子的返工率两班一致。全部印品返工率均4%。”明确的小册子比较与1%/7%冲突；正确的全部印品比较不能撤销这处错误。修正小册子比较，保留其他事实。
甲3全文：“返工率一致，因此两班以同一返工率安排小册子和海报订单。”未解的对象影响安排，应进入issues；不能代选4%而放过。甲4全文：“本次全部印品返工率均4%，今后每批必然一致。”只修无依据未来外推，保留本次观察。
资料乙：三场白班产量100、120、110份，夜班40份；白班废品数都为3，夜班11。只白班均产量110、废品3；混合四班均产量92.5、废品5。
乙1全文：“混合班次的均值受夜班拉低，应分班次解读。表列混合产量92.5/废品5，白班产量110/废品3；不据这些数字判工艺能力。”这里的概括没有断言每个指标都降低，具体产量方向正确、废品表也正确；明确指标可以作为advisory，不能凭废品5>3补造全称fact_error。
乙2全文：“夜班把每一个指标都拉低，包括废品数量。表列混合产量92.5/废品5，白班产量110/废品3。”明确的每一个及废品方向与5>3冲突；表格正确不能撤销这句真错。修正指标方向，不删正确数值。
资料丙：四班产量200、180、160、150，前两班达标、后两班未达标；停机次数依次3、2、0、1。资料没有干预、反事实或未来数据。
丙1全文：“仅本样本中，停机较少的两班仍未达标。不能据此确定停机对达标的因果效应。”这是有数据支持的样本结果与证据不足，非‘降低停机无促进作用’的断言。
丙2全文：“四班证明减少停机没有任何达标促进作用，未来减少停机也不会达标。”这是明确因果零效应和未来外推，资料不支持，进入issues。其错误不能靠补一句‘只看样本’消除。
丙3全文：“达标班与未达标班停机次数几乎相同。”实际均值2.5和0.5，须修数字比较。修法应直接写出达标2.5、未达标0.5及小样本限制；不能为解释这个差距另断言减少停机会造成未达标或对达标无效。
丙4全文：“本样本更少停机并未带来达标，不能据此确定因果。”先按全文核实际含义：最窄样本观察有来源；若认为仍有影响结论的未解歧义，须说明具体不同命题及影响，而非仅凭‘带来’二字判因果真错。建议修法也同样核含义，不用一词代替证据。
[教学示例结束；仅按随后提交的完整报告及真实来源审查]
"""


def candidate_policy(baseline):
    if baseline.count(EXAMPLES) != 1:
        raise ValueError('contrast_example_identity')
    return baseline.replace(EXAMPLES, CONTRASTS)


def baseline_request(request):
    if request.metadata.get(METADATA) != VERSION:
        raise ValueError('contrast_candidate_identity')
    if request.messages[0].content.count(CONTRASTS) != 1:
        raise ValueError('contrast_policy_identity')
    metadata = dict(request.metadata)
    del metadata[METADATA]
    restored = replace(request, metadata=metadata, messages=(replace(request.messages[0],
        content=request.messages[0].content.replace(CONTRASTS, EXAMPLES)), *request.messages[1:]))
    # Full baseline role/protocol validation; transport sends actual candidate.
    identity.baseline(restored)
    return restored


def request_identity(request):
    if request.metadata.get(METADATA) is not None:
        return identity.request_identity(baseline_request(request))
    if request.metadata.get('harness_step') == 'revise' and (
            len(request.tools) != 1 or request.tools[0].name != editor.TOOL):
        raise ValueError('contrast_editor_identity')
    return identity.request_identity(request)


class ContrastDocumentWorkflow(editor.BlockKeyedDocumentWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        base = editor.BlockKeyedDocumentWorkflow.make_request(inputs, **kwargs)
        if kwargs.get('accepted') is not None:
            return base
        return budget_check(replace(base, metadata={**base.metadata, METADATA: VERSION},
            messages=(replace(base.messages[0], content=candidate_policy(base.messages[0].content)),
                *base.messages[1:])))

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = DocumentReviewWorkflow.validate_review(raw, inputs, previous_raw=previous_raw)
        request = ContrastDocumentWorkflow.make_request(inputs, **({} if previous_raw is None else
            {'previous_raw': previous_raw}))
        return payload, wire, dict(journal, teaching_candidate=VERSION,
            baseline_document_policy_sha256=journal['policy_sha256'],
            policy_sha256=digest(request.messages[0].content))

    def _call(self, prepared, phase):
        report = super()._call(prepared, phase)
        if phase == 'native_business_revision':
            from app.evaluation.source_patch_editor import report_inputs
            final = self.make_request(report_inputs(self._accepted[0], report))
            self.last_edit_journal = dict(self.last_edit_journal, teaching_candidate=VERSION,
                baseline_final_review_request_sha256=self.last_edit_journal['final_review_request_sha256'],
                final_review_request_sha256=self.request_sha(final))
        return report


class ContrastDiagnosticRouter(DocumentRoleRoutedProvider):
    teaching_candidate = VERSION

    def role_for_request(self, request):
        request_identity(request)
        return super().role_for_request(baseline_request(request)
            if request.metadata.get(METADATA) is not None else request)


class ContrastDiagnosticLimits:
    """Instance-only identity overlay; never registered as a product contract."""
    def __getattr__(self, name):
        return getattr(DOCUMENT_REVIEW_COACH_CONTRACT, name)

    request_identity = staticmethod(request_identity)

    def descriptor(self):
        return dict(DOCUMENT_REVIEW_COACH_CONTRACT.descriptor(), teaching_candidate=VERSION,
            editor_candidate=editor.VERSION, production_admitted=False)

    def require_provider(self, provider):
        DOCUMENT_REVIEW_COACH_CONTRACT.require_provider(provider)
        if getattr(provider, 'teaching_candidate', None) != VERSION:
            raise ValueError('contrast_router_identity')
