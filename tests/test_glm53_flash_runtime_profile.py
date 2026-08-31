from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from app.agent.context import ContextBuilderV1
from app.agent.compiler import AgentRunCompiler
from app.agent.draft import SkillAgentDraftPreparer
from app.agent.loop import AgentLoop
from app.evaluation.glm53_domain_gate import (
    GLM53BudgetState,
    GLM53BudgetedProvider,
    GLM53FreshDomainResult,
    G53_7_OUTPUT_PATH,
    G53_7_RUNS_ROOT,
    create_glm53_provider,
)
from app.evaluation.provider_domain_production import ProductionDomainCaseExecutor
from app.providers.config import ZhipuSettings
from app.model_runtime import (
    GLM53_FLASH_RUNTIME_PROFILE,
    ModelRuntimeProfile,
    resolve_model_runtime_profile,
)
from app.providers.capabilities import ProviderCapabilities
from app.providers.models import ChatResponse, TokenUsage
from app.skills.catalog import SkillCatalog
from app.skills.execution import (
    SkillExecutionBoundary,
    SkillExecutionRequest,
    SkillInputArtifactBinding,
)
from app.skills.router import DeterministicSkillRouter
from app.skills.routing_models import RouterRequest
from app.tools.adapters.llm import build_llm_tools
from app.tools.adapters.knowledge import build_knowledge_tools
from app.tools.models import ToolContext
from app.tools.registry import ToolRegistry
from app.tools.runtime import ToolRuntime
from app.rag.hybrid import LocalHybridKnowledgeProvider
from app.product.recent_review import (
    RecentReviewProductRequest,
    RecentReviewRuntimeRequestCompiler,
)
from app.runtime.composition import RuntimeCompositionRoot
from app.runtime.observed_provider import ObservedLLMProvider
from app.runtime.runtime import RuntimeCompositionError, RuntimeExecutionFactory


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples/fixtures"


def _execution(run_id: str = "flash_profile_test"):
    summary = json.loads(
        (FIXTURES / "player_summary_demo.json").read_text(encoding="utf-8")
    )
    report = (FIXTURES / "deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )
    catalog = SkillCatalog.from_directory(ROOT / "skills")
    utterance = "分析我最近十局的状态"
    decision = DeterministicSkillRouter().route(
        RouterRequest(
            utterance=utterance,
            available_skills=catalog.route_candidates,
        )
    )
    skill = catalog.get(decision.selected_skill)
    assert skill is not None
    payload = {
        "player_summary": summary,
        "deterministic_report": report,
        "focus": "overall",
    }
    typed = skill.input_model.model_validate(payload)
    binding = SkillInputArtifactBinding.from_content(
        run_id=run_id,
        player_summary=typed.player_summary,
        deterministic_report=typed.deterministic_report,
    )
    return SkillExecutionBoundary(catalog).validate(
        SkillExecutionRequest(
            run_id=run_id,
            user_utterance=utterance,
            router_decision=decision,
            input_payload=payload,
            input_artifacts=binding,
        )
    )


class _RecordingProvider:
    provider_name = "zhipu"
    model_name = "glm-5.3-flash"
    capabilities = ProviderCapabilities(
        text_chat=True,
        tool_calling=True,
        structured_output=True,
    )

    def __init__(
        self,
        *,
        runtime_profile: ModelRuntimeProfile | None = None,
    ) -> None:
        self.runtime_profile = runtime_profile
        self.requests = []

    def chat(self, request):
        self.requests.append(request)
        return ChatResponse(
            content="完成",
            model=self.model_name,
            provider=self.provider_name,
            usage=TokenUsage(input_tokens=1, output_tokens=1),
            finish_reason="stop",
        )


class _NoopObserver:
    def observe(self, _signal) -> None:
        return None


def test_flash_profile_is_exact_and_other_models_do_not_inherit_it():
    profile = resolve_model_runtime_profile("zhipu", "glm-5.3-flash")
    assert profile == GLM53_FLASH_RUNTIME_PROFILE
    assert profile.profile_id == "glm-5.3-flash-runtime-v1"
    assert profile.agent_timeout_s == 90.0
    assert profile.llm_tool_timeout_s == 90.0
    assert profile.transport_timeout_s == 120.0
    assert profile.max_output_tokens == 2048
    assert profile.temperature == 1.0
    assert profile.top_p == 0.95
    assert resolve_model_runtime_profile("zhipu", "glm-5.2") is None
    assert resolve_model_runtime_profile("deepseek", "glm-5.3-flash") is None


def test_g53_7_defaults_are_separate_from_immutable_legacy_artifacts():
    from app.evaluation.glm53_domain_gate import GLM53DomainGateOptions

    options = GLM53DomainGateOptions(confirm_real_call=True)
    assert options.output == G53_7_OUTPUT_PATH
    assert options.runs_root == G53_7_RUNS_ROOT
    assert options.output.name == (
        "zhipu_glm53_flash_domain_adoption_g53_7_runtime_profile_v1.json"
    )
    assert options.output.name != "zhipu_glm53_flash_domain_adoption_v1.json"


def test_profile_rejects_invalid_or_unsafe_budget_values():
    with pytest.raises(ValueError):
        ModelRuntimeProfile(
            profile_id="bad profile",
            provider_id="zhipu",
            model="glm-5.3-flash",
            agent_timeout_s=90,
            llm_tool_timeout_s=90,
            transport_timeout_s=120,
            max_output_tokens=2048,
            temperature=1,
            top_p=0.95,
        )
    with pytest.raises(ValueError):
        ModelRuntimeProfile(
            profile_id="unsafe",
            provider_id="zhipu",
            model="glm-5.3-flash",
            agent_timeout_s=math.nan,
            llm_tool_timeout_s=90,
            transport_timeout_s=120,
            max_output_tokens=2048,
            temperature=1,
            top_p=0.95,
        )
    with pytest.raises(ValueError):
        ModelRuntimeProfile(
            profile_id="unsafe",
            provider_id="zhipu",
            model="glm-5.3-flash",
            agent_timeout_s=90,
            llm_tool_timeout_s=90,
            transport_timeout_s=120,
            max_output_tokens=9000,
            temperature=1,
            top_p=0.95,
        )


def _forged_flash_profile() -> ModelRuntimeProfile:
    return ModelRuntimeProfile(
        profile_id="glm-5.3-flash-runtime-v1",
        provider_id="zhipu",
        model="glm-5.3-flash",
        agent_timeout_s=90,
        llm_tool_timeout_s=90,
        transport_timeout_s=120,
        max_output_tokens=2047,
        temperature=1,
        top_p=0.95,
    )


def test_generic_composition_rejects_same_model_forged_profile():
    forged = _forged_flash_profile()
    provider = _RecordingProvider()
    registry = ToolRegistry()
    loop = AgentLoop(
        provider=provider,
        tool_registry=registry,
        tool_runtime=ToolRuntime(registry),
    )

    with pytest.raises(ValueError, match="registered model profile"):
        AgentRunCompiler(registry, runtime_profile=forged)
    with pytest.raises(ValueError, match="registered model profile"):
        build_llm_tools(provider, runtime_profile=forged)
    with pytest.raises(ValueError, match="registered model profile"):
        SkillAgentDraftPreparer(loop, runtime_profile=forged)


def test_agent_compiler_and_loop_apply_only_injected_flash_profile():
    provider = _RecordingProvider()
    registry = ToolRegistry()
    knowledge = LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs")
    for definition in build_knowledge_tools(knowledge):
        registry.register(definition)
    loop = AgentLoop(
        provider=provider,
        tool_registry=registry,
        tool_runtime=ToolRuntime(registry),
    )
    execution = _execution()
    context = ContextBuilderV1().build(execution)

    result = SkillAgentDraftPreparer(
        loop,
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    ).prepare(execution, context)

    assert result.agent_run.final_response is not None
    request = provider.requests[0]
    assert request.timeout_s == pytest.approx(90.0)
    assert request.max_tokens == 2048
    assert request.temperature == 1.0
    assert request.top_p == 0.95
    assert request.metadata["runtime_profile_id"] == "glm-5.3-flash-runtime-v1"


def test_product_composition_binds_flash_profile_to_factory_and_trace_identity(
    tmp_path: Path,
):
    class _NoopObserver:
        def observe(self, signal) -> None:
            return None

    provider = _RecordingProvider(
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )
    root = RuntimeCompositionRoot.from_directories(
        skills_root=ROOT / "skills",
        prompt_programs_root=ROOT / "prompt_programs",
    )
    runtime = root.build_runtime(
        runs_root=tmp_path,
        provider=provider,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            ROOT / "data/rag_docs"
        ),
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )

    assert runtime._runtime_profile == GLM53_FLASH_RUNTIME_PROFILE
    assert runtime._execution_factory.runtime_profile == (
        GLM53_FLASH_RUNTIME_PROFILE
    )
    identity = runtime._identity(
        skill_name="recent-form-review",
        skill_version="0.2.0",
    )
    assert identity.runtime_profile_id == "glm-5.3-flash-runtime-v1"
    assert identity.runtime_profile_version == "1.0.0"

    observer = _NoopObserver()
    bundle = runtime._execution_factory.build(
        provider=ObservedLLMProvider(delegate=provider, observer=observer),
        observer=observer,
    )
    assert bundle.draft_preparer._compiler._runtime_profile == (
        GLM53_FLASH_RUNTIME_PROFILE
    )


def test_flash_product_composition_auto_infers_concrete_profile(tmp_path: Path):
    root = RuntimeCompositionRoot.from_directories(
        skills_root=ROOT / "skills",
        prompt_programs_root=ROOT / "prompt_programs",
    )
    provider = _RecordingProvider(
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )
    knowledge = LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs")

    runtime = root.build_runtime(
        runs_root=tmp_path,
        provider=provider,
        knowledge_provider=knowledge,
    )

    assert runtime._runtime_profile == GLM53_FLASH_RUNTIME_PROFILE
    assert runtime._execution_factory.runtime_profile == (
        GLM53_FLASH_RUNTIME_PROFILE
    )


def test_flash_product_composition_rejects_unbound_provider(tmp_path: Path):
    root = RuntimeCompositionRoot.from_directories(
        skills_root=ROOT / "skills",
        prompt_programs_root=ROOT / "prompt_programs",
    )
    knowledge = LocalHybridKnowledgeProvider.from_directory(ROOT / "data/rag_docs")

    with pytest.raises(
        RuntimeCompositionError,
        match="requires the registered runtime profile",
    ):
        root.build_runtime(
            runs_root=tmp_path,
            provider=_RecordingProvider(),
            knowledge_provider=knowledge,
        )


def test_flash_explicit_unprofiled_factory_is_rejected(tmp_path: Path):
    root = RuntimeCompositionRoot.from_directories(
        skills_root=ROOT / "skills",
        prompt_programs_root=ROOT / "prompt_programs",
    )
    factory = RuntimeExecutionFactory(
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            ROOT / "data/rag_docs"
        ),
        evaluator_factory=lambda _runtime: object(),
        reviser_factory=lambda _runtime: object(),
    )

    with pytest.raises(
        RuntimeCompositionError,
        match="requires the registered runtime profile",
    ):
        root.build_runtime(
            runs_root=tmp_path,
            provider=_RecordingProvider(),
            execution_factory=factory,
        )


def test_flash_execution_factory_rejects_unprofiled_observed_provider():
    factory = RuntimeExecutionFactory(
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            ROOT / "data/rag_docs"
        ),
        evaluator_factory=lambda _runtime: object(),
        reviser_factory=lambda _runtime: object(),
    )
    observer = _NoopObserver()

    with pytest.raises(
        RuntimeCompositionError,
        match="requires the registered runtime profile",
    ):
        factory.build(
            provider=ObservedLLMProvider(
                delegate=_RecordingProvider(),
                observer=observer,
            ),
            observer=observer,
        )


def test_flash_execution_factory_auto_infers_bound_observed_provider():
    class _Evaluator:
        def evaluate(self, _request):
            return None

    class _Reviser:
        def revise(self, _request):
            return None

    factory = RuntimeExecutionFactory(
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            ROOT / "data/rag_docs"
        ),
        evaluator_factory=lambda _runtime: _Evaluator(),
        reviser_factory=lambda _runtime: _Reviser(),
    )
    observer = _NoopObserver()
    bundle = factory.build(
        provider=ObservedLLMProvider(
            delegate=_RecordingProvider(
                runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
            ),
            observer=observer,
        ),
        observer=observer,
    )

    assert bundle.draft_preparer._compiler._runtime_profile == (
        GLM53_FLASH_RUNTIME_PROFILE
    )


def test_flash_runtime_rejects_unbound_compiler_policy_before_provider_io(
    tmp_path: Path,
):
    root = RuntimeCompositionRoot.from_directories(
        skills_root=ROOT / "skills",
        prompt_programs_root=ROOT / "prompt_programs",
    )
    provider = _RecordingProvider(
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )
    runtime = root.build_runtime(
        runs_root=tmp_path,
        provider=provider,
        knowledge_provider=LocalHybridKnowledgeProvider.from_directory(
            ROOT / "data/rag_docs"
        ),
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )
    summary = json.loads(
        (FIXTURES / "player_summary_demo.json").read_text(encoding="utf-8")
    )
    report = (FIXTURES / "deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )
    request = RecentReviewRuntimeRequestCompiler(
        SkillCatalog.from_directory(ROOT / "skills"),
        run_id_factory=lambda: "unbound_flash_policy",
    ).compile(
        RecentReviewProductRequest(
            riot_id="DemoPlayer#TEST",
            routing_region="asia",
        ),
        player_summary=summary,
        deterministic_report=report,
    )

    with pytest.raises(
        RuntimeCompositionError,
        match="policy is not bound to the Runtime profile",
    ):
        runtime.run(request)
    assert provider.requests == []


def test_recent_review_policy_carries_flash_overlay_without_erasing_skill_gate():
    summary = json.loads(
        (FIXTURES / "player_summary_demo.json").read_text(encoding="utf-8")
    )
    report = (FIXTURES / "deterministic_report_demo.md").read_text(
        encoding="utf-8"
    )
    compiler = RecentReviewRuntimeRequestCompiler(
        SkillCatalog.from_directory(ROOT / "skills"),
        run_id_factory=lambda: "flash_policy_overlay",
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )
    compiled = compiler.compile(
        RecentReviewProductRequest(
            riot_id="DemoPlayer#TEST",
            routing_region="asia",
        ),
        player_summary=summary,
        deterministic_report=report,
    )

    assert compiled.policy.policy_version == "1.1.0"
    assert compiled.policy.timeout_s == 30.0
    assert compiled.policy.execution_timeout_s == 90.0
    assert compiled.policy.runtime_profile_id == (
        "glm-5.3-flash-runtime-v1"
    )
    assert compiled.policy.runtime_profile_version == "1.0.0"


def test_llm_tool_uses_flash_defaults_and_caps_explicit_output():
    provider = _RecordingProvider()
    definition = build_llm_tools(
        provider,
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )[0]
    assert definition.policy.timeout_s == 90.0
    context = ToolContext(
        call_id="flash-profile-call",
        attempt=1,
        deadline_monotonic=100.0,
        clock=lambda: 0.0,
    )
    data = definition.handler(
        {
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 9999,
            "temperature": 0,
            "top_p": 0.1,
        },
        context,
    )
    assert data["content"] == "完成"
    request = provider.requests[0]
    assert request.max_tokens == 2048
    assert request.temperature == 1.0
    assert request.top_p == 0.95
    assert request.timeout_s == pytest.approx(90.0)
    assert request.metadata["runtime_profile_id"] == (
        "glm-5.3-flash-runtime-v1"
    )


def test_domain_budget_wrapper_reasserts_profile_for_custom_executor_requests():
    from app.providers.models import ChatMessage, ChatRequest, MessageRole

    state = GLM53BudgetState()
    state.register_case("flash_gate_baseline_01")
    provider = _RecordingProvider()
    controlled = GLM53BudgetedProvider(
        provider=provider,
        state=state,
        case_id="flash_gate_baseline_01",
        runtime_profile=GLM53_FLASH_RUNTIME_PROFILE,
    )
    controlled.chat(
        ChatRequest(
            messages=(ChatMessage(MessageRole.USER, "probe"),),
            temperature=0.0,
            max_tokens=8192,
            timeout_s=300.0,
            top_p=0.1,
        )
    )
    request = provider.requests[0]
    assert request.max_tokens == 2048
    assert request.temperature == 1.0
    assert request.top_p == 0.95
    assert request.timeout_s == pytest.approx(90.0)
    assert request.metadata["runtime_profile_version"] == "1.0.0"


def test_pre_profile_domain_results_remain_readable_and_immutable_contracts():
    result_root = ROOT / "data/evaluation/results/provider_capabilities"
    for filename in (
        "zhipu_glm53_flash_domain_adoption_v1.json",
        "zhipu_glm53_flash_domain_adoption_g53_6_max_replay_v1.json",
        "zhipu_glm53_flash_domain_adoption_g53_6_max_replay_1024_v1.json",
    ):
        payload = json.loads((result_root / filename).read_text(encoding="utf-8"))
        assert payload["admission"]["max_output_tokens_per_request"] == 1024
        assert "runtime_profile_id" not in payload["admission"]
        loaded = GLM53FreshDomainResult.model_validate(payload)
        assert loaded.admission.runtime_profile_id == "legacy-manifest-budget"
        assert loaded.admission.runtime_profile_version == "legacy"


def test_gate_provider_factory_uses_flash_transport_budget_without_changing_settings():
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return object()

    settings = ZhipuSettings(
        api_key="not-a-real-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        model="glm-5.3-flash",
        default_timeout_s=30,
    )
    provider = create_glm53_provider(settings, client_factory=factory)
    assert provider.model_name == "glm-5.3-flash"
    assert captured["timeout"] == 120.0
    assert captured["max_retries"] == 0


def test_domain_executor_rejects_forged_same_model_budget_profile(tmp_path):
    # The constructor only needs a loaded input plan to exercise its trust
    # boundary; reuse the frozen plan artifact and alter one budget field.
    from app.evaluation.provider_domain_plan import load_domain_case_input_plan
    from app.evaluation.domain_e2e import load_domain_dataset

    dataset = load_domain_dataset(
        ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_cases.json"
    )
    plan = load_domain_case_input_plan(
        ROOT / "data/evaluation/glm53_flash_domain_adoption_v1_input_plan.json",
        project_root=ROOT,
        dataset=dataset,
    )
    forged = ModelRuntimeProfile(
        profile_id="glm-5.3-flash-runtime-v1",
        provider_id="zhipu",
        model="glm-5.3-flash",
        agent_timeout_s=90,
        llm_tool_timeout_s=90,
        transport_timeout_s=120,
        max_output_tokens=2047,
        temperature=1,
        top_p=0.95,
    )
    with pytest.raises(ValueError, match="registered model profile"):
        ProductionDomainCaseExecutor(
            project_root=ROOT,
            input_plan=plan,
            runs_root=tmp_path,
            runtime_profile=forged,
        )
