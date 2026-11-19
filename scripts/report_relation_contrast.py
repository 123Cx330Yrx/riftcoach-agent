"""Unadmitted relation contrast, preserving the complete initial/edit/final flow.

An experimental teaching delta, not a semantic validator or a paid entrypoint.
No historical policy, response, decision, source, or product registry is changed.
"""
from dataclasses import replace

from app.evaluation.golden_native_issues_review import budget_check
from app.evaluation.golden_review_experiment import digest
from scripts import report_contrast_review as parent

VERSION = 'offline-relation-contrast-v1'
METADATA = 'relation_teaching_candidate'
OLD = '丙3全文：“达标班与未达标班停机次数几乎相同。”实际均值2.5和0.5，须修数字比较。修法应直接写出达标2.5、未达标0.5及小样本限制；不能为解释这个差距另断言减少停机会造成未达标或对达标无效。'
NEW = OLD + '''
丙3修法对照：“达标班停机均值2.5、未达标班0.5，所以停机次数没有把本次两组分开；不能据此确定因果。”数字和因果限制正确，但中间结论错误：本次达标班3、2，未达标班0、1，每个达标班的值都较高，两组无重叠。较少停机出现在未达标组，并不意味着数值没有样本区分。可只改为“本次达标班均值2.5、未达标班0.5，未达标组较少；不能据此确定因果”，不必增加新的解释。
反例校验：另一批达标班停机4、0，未达标班3、1，两组均值同为2，但取值区间重叠，不能说每个达标班都高于每个未达标班。若达标班改为5、0而未达标仍3、1，均值2.5和2有差异，取值仍重叠。均值方向、逐行区分和因果效应是不同断言，按各自来源核查，不由其中一个替另外两个作答。这同样适用于建议修法新写出的断言，不要求报告增加这些术语。'''


def restore(request):
    if request.metadata.get(METADATA) != VERSION:
        raise ValueError('relation_candidate_identity')
    policy = request.messages[0].content
    if policy.count(NEW) != 1:
        raise ValueError('relation_policy_identity')
    metadata = dict(request.metadata)
    del metadata[METADATA]
    result = replace(request, metadata=metadata, messages=(
        replace(request.messages[0], content=policy.replace(NEW, OLD)), *request.messages[1:]))
    parent.request_identity(result)
    return result


def request_identity(request):
    return parent.request_identity(restore(request)
        if METADATA in request.metadata else request)


class RelationContrastWorkflow(parent.ContrastDocumentWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        base = parent.ContrastDocumentWorkflow.make_request(inputs, **kwargs)
        if kwargs.get('accepted') is not None:
            return base
        policy = base.messages[0].content
        if policy.count(OLD) != 1:
            raise ValueError('relation_parent_example_changed')
        return budget_check(replace(base, metadata={**base.metadata, METADATA: VERSION},
            messages=(replace(base.messages[0], content=policy.replace(OLD, NEW)), *base.messages[1:])))

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        payload, wire, journal = parent.ContrastDocumentWorkflow.validate_review(
            raw, inputs, previous_raw=previous_raw)
        request = RelationContrastWorkflow.make_request(inputs,
            **({} if previous_raw is None else {'previous_raw': previous_raw}))
        return payload, wire, dict(journal, relation_teaching_candidate=VERSION,
            parent_policy_sha256=journal['policy_sha256'],
            policy_sha256=digest(request.messages[0].content))


class RelationDiagnosticRouter(parent.ContrastDiagnosticRouter):
    relation_teaching_candidate = VERSION

    def role_for_request(self, request):
        return super().role_for_request(restore(request)
            if METADATA in request.metadata else request)


class RelationDiagnosticLimits(parent.ContrastDiagnosticLimits):
    request_identity = staticmethod(request_identity)

    def descriptor(self):
        return dict(super().descriptor(), relation_teaching_candidate=VERSION)

    def require_provider(self, provider):
        super().require_provider(provider)
        if getattr(provider, 'relation_teaching_candidate', None) != VERSION:
            raise ValueError('relation_router_identity')
