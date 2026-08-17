# Prompt Program V1 与 Runtime Composition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 建立可严格加载、可重算指纹、漂移即拒绝的 Prompt Program V1，并让 `AgentRuntimeV1` 的产品装配从已验证 Program 取得 prompt identity，同时保留非产品旧测试的显式 legacy 路径。

**Architecture:** Prompt Program Manifest 是 Skill、Context、Evaluation、Revision 和 knowledge tool 合同的组合身份，不保存 Prompt 正文。`PromptProgramCatalog` 负责严格读取 manifest；`PromptProgramResolver` 结合当前 `SkillCatalog` 重新计算现有 `PromptContextSnapshot` 的 component fingerprints，并在 skill/version/context/evaluation 或摘要不一致时 fail closed。Runtime 通过注入的 identity resolver 取得已验证 Program；未注入 resolver 的直接旧 Runtime 测试只使用显式标记的 legacy identity，不被当作产品装配。

**Tech Stack:** Python 3.11, Pydantic v2, JSON manifest, SHA-256 canonical JSON, pytest。

---

## 教学边界

本计划实现：

- Prompt Program 的严格数据合同；
- 当前组件指纹的生产复用；
- manifest digest 与组件 drift gate；
- secure Evaluation 1.1 组合限制；
- Runtime identity 的 resolver 接缝与产品 composition root。

本计划不实现：

- Prompt 文案调优；
- FastAPI/Application Service（5P-3 以后）；
- Riot/Provider/API Key/网络调用；
- LangGraph、Pi/Claude Agent SDK、MCP、Multi-Agent；
- 自动模型切换或真实模型质量评测。

### Task 1: 写失败测试固定 Program 合同与加载边界

**Files:**
- Create: `tests/test_prompt_program.py`

**Step 1: Write the failing tests**

覆盖以下不变量：严格字段、manifest 自身 digest、重复/缺失组件拒绝、缺失 manifest 拒绝、目录顺序稳定、secure Evaluation 1.1 限制、组件摘要变化拒绝、Skill/version/context 不匹配拒绝。

**Step 2: Run focused tests**

Run: `python -m pytest tests/test_prompt_program.py -q`

Expected: FAIL，因为 `app.prompt_program` 尚不存在。

### Task 2: 暴露可复用的当前组件指纹计算

**Files:**
- Modify: `app/evaluation/prompt_context_identity.py`
- Modify: `tests/test_prompt_context_identity.py`

**Step 1: Add a public wrapper**

在不改变现有 snapshot 行为的前提下，暴露 `build_component_fingerprints(skill, evaluation_contract_version=...)`，内部仍复用当前唯一的 `_component_fingerprints` 实现。

**Step 2: Run identity regression**

Run: `python -m pytest tests/test_prompt_context_identity.py -q`

Expected: 原有测试全部通过，新 wrapper 与旧私有实现生成相同顺序和摘要。

### Task 3: 实现严格 Prompt Program Manifest/Catalog/Resolver

**Files:**
- Create: `app/prompt_program/__init__.py`
- Create: `app/prompt_program/models.py`
- Create: `app/prompt_program/catalog.py`
- Create: `app/prompt_program/resolver.py`
- Modify: `tests/test_prompt_program.py`

**Step 1: Implement models**

实现 frozen/extra-forbid Pydantic models，采用规范 JSON 计算 `program_sha256`，并验证安全 ID、semver、组件唯一性与 secure Evaluation 1.1。

**Step 2: Implement catalog**

实现 `PromptProgramCatalog.from_directory()`：只加载可见子目录，要求每个包有 `manifest.json`，失败立即抛出稳定的 catalog error，输出按 program id 排序的不可变快照。

**Step 3: Implement resolver**

实现 `PromptProgramResolver.resolve(skill_name, skill_version)`：从当前 `SkillCatalog` 找到 Skill，重算组件 fingerprint，校验 manifest digest、skill/version、Context contract、Evaluation contract 和完整组件集合；任何漂移都拒绝。

**Step 4: Run focused tests**

Run: `python -m pytest tests/test_prompt_program.py -q`

Expected: PASS。

### Task 4: 添加产品 Prompt Program manifest 并通过真实当前资产校验

**Files:**
- Create: `prompt_programs/recent-form-review/manifest.json`
- Modify: `tests/test_prompt_program.py`

**Step 1: Generate only from checked-in current assets**

用本地 `skills/`、当前 Context descriptor、knowledge contract、Evaluation 1.1 和 Revision builder 计算 manifest 组件摘要；不读取 Key、不调用 Provider。

**Step 2: Verify product manifest**

测试默认目录能解析 `recent-form-review-coach@1.0.0`，并返回 verified program；改动任一资产或 manifest 字段时 fail closed。

### Task 5: 接入 Runtime identity 与显式 composition root

**Files:**
- Create: `app/runtime/composition.py`
- Modify: `app/runtime/runtime.py`
- Modify: `app/runtime/models.py` only if the resolver identity contract requires a typed model extension
- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_prompt_program.py`

**Step 1: Add resolver protocol and explicit legacy adapter**

Runtime 接受可注入的 verified identity resolver；产品 composition root 必须提供 `PromptProgramResolver`。直接旧测试若不注入 resolver，只能走命名为 `LegacyRuntimeIdentityResolver` 的兼容 adapter，不能伪装成 Program-verified 运行。

**Step 2: Replace hardcoded product identity**

`AgentRuntimeV1._identity()` 从 resolver 读取 program id/version、skill/version 和 context version；漂移在 Provider/Tool I/O 前失败。保留 `RuntimeIdentitySnapshot` 既有 schema，避免提前扩大 Trace 合同。

**Step 3: Add composition root**

实现一个只负责长生命周期装配 SkillCatalog、PromptProgramCatalog、Resolver 和 Runtime identity 依赖的薄 composition object；不在 import 时读取 Key，不创建 FastAPI，不发网络。

**Step 4: Run focused runtime tests**

Run: `python -m pytest tests/test_prompt_program.py tests/test_agent_runtime.py tests/test_runtime_models.py -q`

Expected: PASS；产品 resolver 场景使用 verified manifest，旧非产品测试仍明确标记 legacy。

### Task 6: 持久状态、门禁与公开验证

**Files:**
- Modify: `docs/project_execution_state.md`
- Modify: `.planning/2026-08-06-riftcoach-development/task_plan.md`
- Modify: `.planning/2026-08-06-riftcoach-development/findings.md`
- Modify: `.planning/2026-08-06-riftcoach-development/progress.md`
- Modify: `docs/requirements_change_log.md` when the accepted implementation decision is recorded
- Modify: `docs/roadmap_change_history.md`
- Modify: `docs/project_decisions.md`
- Modify: `docs/architecture_capability_matrix.md`

**Step 1: Run proportional verification**

Run focused Prompt Program tests, Runtime adjacent tests, full pytest, compileall, both RAG gates, governance, secret/tracked-data boundary, Harness dry-run and `git diff --check`.

**Step 2: Record limits honestly**

明确记录：Program drift gate 通过不等于真实 Provider 质量通过；旧 direct Runtime tests 的 legacy adapter 不等于产品路径；FastAPI/Application Service 仍是 5P-3；真实 Prompt/model 质量仍 unknown。

**Step 3: Commit, push, exact-SHA CI**

提交并验证公共 CI；成功后 canonical 唯一下一步切换为 `5P-3-domain-application-service`，不得自动进入 5P-4/5P-5/5F。

