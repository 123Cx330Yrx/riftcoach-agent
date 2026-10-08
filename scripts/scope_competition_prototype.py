"""Offline whole-review prototype; no live entry point or product registration.

Records competing interpretations as short public evidence justifications, not
private reasoning. Reference validation cannot decide whether anchors entail a
scope or whether the model found every disputed claim. No old receipt qualifies.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from typing import Literal

from pydantic import Field

from app.evaluation import review_bound_editor as editor
from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_native_issues_review import budget_check, strict_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReview
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.source_patch_editor import report_inputs
from app.providers.errors import ProviderResponseError

VERSION = 'scope-competition-offline-v1'
OLD_FIELDS = '五个字段为score、verdict、issues、issue_resolutions、advisories。'
NEW_FIELDS = '六个字段为scope_checks、score、verdict、issues、issue_resolutions、advisories。'
AUDIT_RULE = (
    'scope_checks是简短的公开证据记录，不是思维过程或另一份评估。'
    '对全文中存在竞争样本范围的断言记录一次，包括考虑列为issue或advisory的范围争议；'
    '完全明确且无竞争的普通断言不必生成记录，仍须接受完整业务审查。'
    'claim是block内唯一连续原文，不改写断言；candidates逐项列实际竞争的已有cohort，'
    'anchors指向全文中支持或排除这一解释的原段，包括与局部读法相反的具体前后文。'
    'relation的supports/refutes/does_not_resolve只描述这些文字对该范围解释的关系，'
    '不是数值正确性；basis用一句话说明该关系，不重抄数字、来源或思维链。'
    'resolution明确resolved的cohort，或unresolved且cohort=null；不能因某组数字让原句正确而选择该组。'
    '再按实际范围核对原有全部业务要求，真实问题仍只在issues裁决；'
    '范围确定不代表断言成立，均值不支持逐局一致，范围限定不抵消未来或因果外推。'
    '记录缺失、引用合法或解释看似完整都不是事实正确的证明。'
)


class Claim(Strict):
    block: int = Field(ge=1, le=64)
    exact_text: str = Field(min_length=1, max_length=500)


class Candidate(Strict):
    cohort: str = Field(min_length=1, max_length=16)
    anchors: list[int] = Field(min_length=1, max_length=8)
    relation: Literal['supports', 'refutes', 'does_not_resolve']
    basis: str = Field(min_length=1, max_length=220)


class Resolution(Strict):
    status: Literal['resolved', 'unresolved']
    cohort: str | None = Field(max_length=16)


class ScopeCheck(Strict):
    claim: Claim
    candidates: list[Candidate] = Field(min_length=2, max_length=7)
    resolution: Resolution


class CompetitionReview(RoleClarityReview):
    scope_checks: list[ScopeCheck] = Field(max_length=16)


def _data(request):
    return json.loads(request.messages[1].content.split('\n', 1)[1].rsplit('\n', 1)[0])


def review_request(inputs):
    base = editor.Current.make_request(inputs)
    policy = base.messages[0].content
    if policy.count(OLD_FIELDS) != 1:
        raise ValueError('competition_policy_drift')
    schema = CompetitionReview.model_json_schema()
    # Preserve the existing citation restrictions; never widen the old sources.
    for name in ('Problem', 'IssueResolution'):
        schema['$defs'][name] = deepcopy(base.tools[0].input_schema['$defs'][name])
    cohorts = list(_data(base)['computed_evidence']['cohorts'])
    schema['$defs']['Candidate']['properties']['cohort']['enum'] = cohorts
    return budget_check(replace(base,
        messages=(replace(base.messages[0], content=policy.replace(OLD_FIELDS, NEW_FIELDS)
                          + '\n' + AUDIT_RULE), *base.messages[1:]),
        tools=(replace(base.tools[0], input_schema=schema),),
        metadata={**base.metadata, 'offline_scope_audit': VERSION}))


def validate(raw, inputs):
    value = strict_json(raw)
    wire = CompetitionReview.model_validate(value, strict=True)
    # Base projection is internal validation only. Keep the actual complete raw
    # and all audit records in the journal. The editor's existing actionable
    # review contract is unchanged, as with nonblocking clarity markers.
    projected = compact(wire.model_dump(mode='json', exclude={'scope_checks'}))
    payload, _, journal = editor.Current.validate_review(projected, inputs)
    request = review_request(inputs)
    cohorts = set(_data(request)['computed_evidence']['cohorts'])
    seen = set()
    for check in wire.scope_checks:
        claim = check.claim
        if claim.block > len(inputs.source.blocks):
            raise ValueError('competition_claim_block')
        block = inputs.source.blocks[claim.block - 1][1]
        start = block.find(claim.exact_text)
        if start < 0 or block.find(claim.exact_text, start + 1) >= 0:
            raise ValueError('competition_claim_not_unique')
        identity = (claim.block, claim.exact_text)
        if identity in seen:
            raise ValueError('competition_duplicate_claim')
        seen.add(identity)
        refs = [c.cohort for c in check.candidates]
        if len(set(refs)) != len(refs) or not set(refs) <= cohorts:
            raise ValueError('competition_candidate_inventory')
        for candidate in check.candidates:
            if (len(set(candidate.anchors)) != len(candidate.anchors)
                    or any(type(n) is not int or not 1 <= n <= len(inputs.source.blocks)
                           for n in candidate.anchors)):
                raise ValueError('competition_anchor_inventory')
        resolved = check.resolution
        if resolved.status == 'unresolved':
            if resolved.cohort is not None:
                raise ValueError('competition_unresolved_has_cohort')
        elif not any(c.cohort == resolved.cohort and c.relation == 'supports'
                     for c in check.candidates):
            raise ValueError('competition_resolution_without_support')
    return payload, wire, dict(journal,
        experiment=VERSION, validator_experiment=VERSION,
        raw=raw, raw_sha256=digest(raw), parsed_review=wire.model_dump(mode='json'),
        policy_sha256=digest(request.messages[0].content),
        scope_audit_coverage_verified=False, semantic_approval=False,
        production_admitted=False)


class OfflineWorkflow(editor.ReviewBoundRevisionWorkflow):
    """Injectable full initial/edit/fresh prototype; never registers a candidate.

    A malformed response stops this experiment. There is no sixth recovery call.
    Fresh sees only its complete report/sources, never the initial scope choice.
    """

    @staticmethod
    def make_request(inputs, **kwargs):
        if kwargs:
            if set(kwargs) != {'accepted'}:
                raise ValueError('competition_no_reassessment')
            return editor.edit_request(inputs, kwargs['accepted'])
        return review_request(inputs)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        if previous_raw is not None:
            raise ProviderResponseError(provider='zhipu', code='competition_no_reassessment')
        try:
            payload, wire, journal = validate(raw, inputs)
            actionable = RoleClarityReview.model_validate(
                wire.model_dump(mode='json', exclude={'scope_checks'}), strict=True)
            return payload, actionable, journal
        except ValueError as error:
            raise ProviderResponseError(provider='zhipu', code='competition_invalid_review') from error

    def _call(self, prepared, phase):
        result = super()._call(prepared, phase)
        if phase == 'native_business_revision':
            # The reused editor records its legacy preview. Replace that preview
            # binding with this prototype's actual fresh request, without IO.
            final = review_request(report_inputs(self._accepted[0], result))
            self.last_edit_journal = dict(self.last_edit_journal,
                final_review_request_sha256=hashlib.sha256(validate_request(
                    final, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest(),
                final_review_contract=VERSION)
        return result


def audit_requests():
    """Reproducible zero-IO input audit using committed original-set fixtures."""
    from app.evaluation import review_bound_qualification as backend
    from app.evaluation.glm53_bounded_revision_budget_reachability import (
        estimate_runtime_request_input_ceiling as size,
    )
    rows = []
    for fixture, source in backend.frozen_cases()[0]:
        inputs = backend.Workflow.build_inputs(source)
        base, proposed = backend.Workflow.make_request(inputs), review_request(inputs)
        if proposed.messages[1:] != base.messages[1:]:
            raise ValueError('competition_complete_input_changed')
        rows.append(dict(key=fixture['key'], report_sha256=digest(source.report),
            input_sha256=digest(inputs.data_json), base_input_ceiling=size(base),
            proposed_input_ceiling=size(proposed), request_sha256=hashlib.sha256(
                validate_request(proposed, transport_id=REVIEW_MODEL_TRANSPORT_ID)).hexdigest()))
    return dict(version=VERSION, provider_calls=0, model_quality_proven=False,
        product_registered=False, natural_task_budget_verified=False,
        original15_new_qualified=0, old_identity_qualified=2,
        request_audit=rows,
        limitations=['Authored fixtures and legal addresses do not prove semantic coverage.',
                    'Existing production routing rejects this prototype schema.',
                    'No live runner, frozen paid plan, or authority to spend.'])


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    from app.evaluation.golden_journal import write_new_json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit_requests()
    if args.output:
        write_new_json(args.output, result)
    print(compact(result))
