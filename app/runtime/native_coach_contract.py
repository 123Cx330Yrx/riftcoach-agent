"""Explicit native review identity; no production or default admission."""
import hashlib
import json
from pathlib import Path

from app.evaluation.coach_grounded_contract import grounded_context_policy
from app.evaluation.golden_compact_report_policy import COMPACT_REPORT_POLICY
from app.evaluation.golden_contextual_correction import FULL_CONTEXT_RULE
from app.evaluation.golden_position_policy import POSITION_POLICY
from app.evaluation.golden_source_use_policy import SOURCE_USE_POLICY


def generation_policy():
    # Generation receives business requirements, never review JSON instructions.
    source_policy = SOURCE_USE_POLICY.split('\nDuring evaluation', 1)[0]
    return '\n\n'.join((grounded_context_policy(), POSITION_POLICY, source_policy,
        COMPACT_REPORT_POLICY, FULL_CONTEXT_RULE,
        '按用户请求区分观摩对象与阅读者。观摩数据不构成阅读者本人的能力基线或训练证据；'
        '没有本人数据与目标时仅给条件观摩练习。标题中的能力断言同样需要证据。'
        '比较必须明确同一位置、样本和指标；均值、中位数、逐行方向不能互换，'
        '样本观察不能外推所有未来对局。官方发布日期与第三方检索时间分别归因。'
        '最终只输出完整Markdown报告，保持来源限制和知识引用。'))


def component_fingerprints(skill):
    from app.evaluation import golden_native_issues_review as native
    from app.evaluation.prompt_context_identity import build_component_fingerprints, ComponentFingerprint
    common = {'skill_manifest', 'skill_instructions', 'context_contract', 'knowledge_tool_contract'}
    rows = [r for r in build_component_fingerprints(skill, evaluation_contract_version='1.1.0', knowledge_retrieval_time=True)
            if r.component_id in common]
    root = Path(__file__).resolve().parents[2]
    sources = (
        'app/evaluation/golden_native_issues_review.py',
        'app/evaluation/golden_semantic_review.py',
        'app/evaluation/golden_semantic_sources.py',
        'app/evaluation/golden_contextual_sources.py',
        'app/evaluation/golden_computed_evidence.py',
        'app/evaluation/golden_integrated_runtime.py',
        'app/evaluation/golden_stream_bridge.py',
        'app/runtime/review_sender.py', 'app/runtime/receipted_provider_factory.py',
        'app/runtime/native_coach_contract.py',
        'app/product/native_coach_composition.py',
        'app/product/recent_review_service.py',
        'app/evaluation/golden_source_context.py',
        'app/product/coach_positions.py',
        'app/tools/adapters/knowledge.py',
        'app/harness/steps.py',
        'app/harness/knowledge.py',
        'app/harness/adapters.py',
        'app/harness/runtime.py',
        'app/agent/context.py',
        'app/runtime/runtime.py',
    )
    values = {'evaluation_schema': json.dumps(native.NativeIssuesReview.model_json_schema(), sort_keys=True),
              'generation_policy': generation_policy()}
    values.update({path: (root/path).read_text(encoding='utf-8') for path in sources})
    return tuple(rows + [ComponentFingerprint(component_id=key.replace('/', '.').replace('.py', ''),
        source=key, sha256=hashlib.sha256(value.encode()).hexdigest()) for key, value in values.items()])
